"""Frozen five-source transfer test: older ensemble, new experts, original Bfxr."""
import argparse
import json
from pathlib import Path
import time
import numpy as np
import soundfile as sf
import torch

from match.audio import prepare_target
from match.objective import MatchObjective
from match.renderer import BfxrRenderer
from multisynth.cli import AUDIO_SUFFIXES, source_info
from multisynth.coverage import verify_archived_audio
from multisynth.coverage_feedback import export_coverage
from multisynth.features import describe
from multisynth.preference import PreferenceMetric
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash, exact_replay
from neural_invert.coverage_mixture import load as load_mixture
from neural_invert.coverage_mixture_eval import write_wave, read_wave
from neural_invert.data import file_hash, _json_write
from neural_invert.evaluate import OriginalBfxr, rendered_candidates, refine_candidate, serializable
from neural_invert.experiment import audition_pcm
from neural_invert.predict import load_model, predict
from neural_invert.temporal import predict_temporal

BASE = Path('tools/multisynth')
OUT = BASE/'runs/specialists-tagged-v1'
GALLERY = BASE/'runs/specialists-tagged-v1-listening'
CORPUS = Path('/Users/stephenlavelle/Documents/bfxr2/tools/targets_non_bfxr_big/tags')
PLAN = Path('docs/superpowers/plans/2026-10-05-specialists-tagged-transfer.md')
SHARED = BASE/'runs/neural-v2/acoustic-model'
MIXTURE = BASE/'runs/native-mixture-v1/models/mixture'
SPECIALISTS = BASE/'runs/specialists-v1/models'
BFXR = Path('/Users/stephenlavelle/Documents/bfxr2/.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt')
METRIC = BASE/'models/preference-neural-v2.json'
SEED = 20261116
TAGS = ('footstep', 'explode', 'hit', 'clothes', 'laser')


class AuditionObjective(MatchObjective):
    """Search floats, but measure the exact single-transform listening PCM."""
    def score_batch(self, waves):
        return super().score_batch([audition_pcm(w) if w is not None and len(w) else w for w in waves])


def freeze():
    if OUT.exists():
        raise FileExistsError('Fresh target freeze required')
    paths = {'shared':SHARED/'best.pt', 'Transfxr':MIXTURE/'best.pt',
        'Boomr':SPECIALISTS/'Boomr/best.pt', 'Footsteppr':SPECIALISTS/'Footsteppr/best.pt', 'originalBfxr':BFXR}
    hashes = {k:file_hash(p) for k,p in paths.items()}
    prior_hashes, prior_pcm, archives = set(), set(), {}
    for path in sorted((BASE/'listening_data').glob('*/manifest.json')):
        archives[str(path)] = file_hash(path)
        manifest = json.loads(path.read_text())
        for target in manifest['targets']:
            prior_hashes.add(target['source'].get('sha256'))
            verify_archived_audio(path.parent, target['referenceAudio'])
            pcm, rate = sf.read(path.parent/target['referenceAudio']['file'], dtype='float32')
            assert rate == 44100
            prior_pcm.add(audio_hash(pcm))
    rng = np.random.default_rng(SEED)
    rows, rejected = [], []
    for tag in TAGS:
        paths = sorted(p for p in (CORPUS/tag).rglob('*') if p.suffix.lower() in AUDIO_SUFFIXES and p.is_file())
        rng.shuffle(paths)
        for path in paths:
            reason = None
            info = sf.info(path)
            if not .025 <= info.duration <= 1.8:
                reason = 'duration'
            elif file_hash(path) in prior_hashes:
                reason = 'previously-judged-file'
            else:
                wave = audition_pcm(prepare_target(path))
                if not len(wave) or np.max(np.abs(wave)) < 1e-6:
                    reason = 'silence'
                elif audio_hash(wave) in prior_pcm:
                    reason = 'previously-judged-or-selected-pcm'
            if reason:
                rejected.append(dict(name=str(path.relative_to(CORPUS)),reason=reason))
                continue
            prior_pcm.add(audio_hash(wave))
            rows.append(dict(source=source_info(path,CORPUS), tag=tag, sourceSeconds=info.duration,
                auditionHash=audio_hash(wave), auditionSamples=len(wave), seed=SEED+len(rows)*1009))
            break
        else:
            raise ValueError('No eligible unjudged reference in '+tag)
    assert len(rows)==5
    OUT.mkdir()
    _json_write(OUT/'targets.json',dict(complete=True, rows=rows, rejected=rejected, priorArchives=archives,
        scriptSha256=file_hash(__file__), designSha256=file_hash(PLAN), checkpoints=hashes,
        preferenceMetricSha256=file_hash(METRIC), seed=SEED,
        policy='Freeze five short tagged sources before inference; exclude previously judged exact files and PCM. Categories are sampling strata, never model inputs. Not a family-disjoint test.',
        oldPool='shared22 two/head + Transfxr mixture four + original Bfxr 2000; refine two distinct best non-original engines 128/start',
        newPool='Boomr and Footsteppr four/head; refine best of each 128/start',
        listeningPolicy='Baseline pool winner, new-specialist pool winner, original Bfxr; if Bfxr duplicates baseline, distinct raw specialist instead. Deduplicate PCM; at most three options. All five references, no score-based dropping.'))
    print(json.dumps(dict(frozen=[r['source']['name'] for r in rows],sha256=file_hash(OUT/'targets.json'))),flush=True)


def run():
    frozen = json.loads((OUT/'targets.json').read_text())
    assert frozen['scriptSha256']==file_hash(__file__)
    assert not (OUT/'results.json').exists()
    torch.set_num_threads(1)
    shared = load_model(SHARED)
    mixture = load_mixture(MIXTURE)
    new = {name:load_model(SPECIALISTS/name) for name in ('Boomr','Footsteppr')}
    for name, meta in [('shared',shared[1]),('Transfxr',mixture[1])]+[(name,m[1]) for name,m in new.items()]:
        assert meta['checkpointHash']==frozen['checkpoints'][name]
    assert file_hash(BFXR)==frozen['checkpoints']['originalBfxr']
    assert file_hash(METRIC)==frozen['preferenceMetricSha256']
    metric = PreferenceMetric.load(METRIC)
    rows = []
    with Renderer() as renderer, BfxrRenderer(jobs=1) as bfxr:
        original = OriginalBfxr(BFXR,bfxr)
        for index, target in enumerate(frozen['rows']):
            dest = OUT/f'{index+1:03d}'
            # Only complete per-source files are resumable; interrupted folders
            # intentionally require inspection rather than silent replacement.
            if (dest/'result.json').exists():
                saved = json.loads((dest/'result.json').read_text())
                assert saved['complete'] and saved['target']==target
                assert saved['targetsSha256']==file_hash(OUT/'targets.json')
                rows.append(saved)
                continue
            dest.mkdir()
            started = time.monotonic()
            assert file_hash(target['source']['path'])==target['source']['sha256']
            reference = audition_pcm(prepare_target(target['source']['path']))
            assert audio_hash(reference)==target['auditionHash']
            reference_info = write_wave(dest/'target-float.wav',reference)
            sf.write(dest/'target.wav',reference,44100,subtype='PCM_16')
            objective = AuditionObjective(reference)
            descriptor = describe(reference)
            failures = []
            print(json.dumps(dict(target=index+1, name=target['source']['name'], phase='proposals')),flush=True)
            proposed = [{**c,'origin':'shared22'} for c in predict(*shared,reference,renderer,per_synth=2)]
            proposed += [{**c,'origin':'Transfxr-mixture'} for c in predict_temporal(*mixture,reference,renderer,count=4)]
            old_raw, bad = rendered_candidates(proposed,renderer,objective)
            failures.extend(bad)
            new_raw = []
            for name, model in new.items():
                accepted, bad = rendered_candidates([{**c,'origin':'specialist-'+name}
                    for c in predict(*model,reference,renderer,per_synth=4)],renderer,objective)
                new_raw.extend(accepted)
                failures.extend(bad)
            assert old_raw and new_raw
            print(json.dumps(dict(target=index+1,phase='original-bfxr')),flush=True)
            bfxr_candidate = original.approximate(reference,objective,budget=2000,seed=target['seed'])
            bfxr_candidate['origin'] = 'original-bfxr'
            starts, seen = [], set()
            for candidate in sorted(old_raw,key=lambda c:c['score']):
                if candidate['synth'] not in seen:
                    starts.append(candidate)
                    seen.add(candidate['synth'])
                if len(starts)==2:
                    break
            assert len(starts)==2
            print(json.dumps(dict(target=index+1,phase='refinement',oldEngines=[c['synth'] for c in starts])),flush=True)
            old_refined = [refine_candidate(c,renderer,objective,128,target['seed']+i*71) for i,c in enumerate(starts)]
            new_refined = [refine_candidate(min((c for c in new_raw if c['synth']==name),key=lambda c:c['score']),
                renderer,objective,128,target['seed']+i*71) for i,name in enumerate(('Boomr','Footsteppr'))]
            saved_pools = {}
            for label, pool in [('oldRaw',old_raw),('oldRefined',old_refined),('newRaw',new_raw),
                                ('newRefined',new_refined),('original',[bfxr_candidate])]:
                saved_pools[label] = []
                for slot,c in enumerate(pool):
                    wave_info = write_wave(dest/f'{label}-{slot}.wav',c['wave'])
                    pcm = audition_pcm(c['wave'])
                    score = float(MatchObjective.score_batch(objective,[pcm])[0])
                    assert abs(score-c['score'])<1e-6
                    saved_pools[label].append({**serializable(c), **wave_info,
                        'auditionHash':audio_hash(pcm), 'sourceHash':renderer.inventory['sourceHash'],
                        'preferenceDistance':float(metric.distances(descriptor,describe(pcm))[0])})
            old_choices = old_raw+old_refined+[bfxr_candidate]
            new_choices = new_raw+new_refined
            old_best, new_best = min(old_choices,key=lambda c:c['score']), min(new_choices,key=lambda c:c['score'])
            options = [('previous',old_best),('selected',new_best)]
            seen_pcm = {audio_hash(audition_pcm(c['wave'])) for _,c in options}
            if audio_hash(audition_pcm(bfxr_candidate['wave'])) not in seen_pcm:
                options.append(('original',bfxr_candidate))
            else:
                extra = next((c for c in sorted(new_raw,key=lambda c:c['score']) if audio_hash(audition_pcm(c['wave'])) not in seen_pcm),None)
                if extra is not None:
                    options.append(('raw',extra))
            finalists, seen_pcm = [], set()
            for role,c in options:
                replay = exact_replay(c,renderer,bfxr)
                pcm = audition_pcm(c['wave'])
                if audio_hash(pcm) in seen_pcm:
                    continue
                seen_pcm.add(audio_hash(pcm))
                file = role+'.wav'
                sf.write(dest/file,pcm,44100,subtype='PCM_16')
                decoded,rate = sf.read(dest/file,dtype='float32')
                assert rate==44100 and np.array_equal(decoded,pcm)
                score = float(MatchObjective.score_batch(objective,[decoded])[0])
                assert abs(score-c['score'])<1e-6
                finalists.append({**serializable(c),'role':role,'label':'Comparison option','file':file,
                    'sourceHash':renderer.inventory['sourceHash'],
                    'provenance':{**c['provenance'],'origin':c['origin'],'actualReplay':replay,
                        'auditionMatchObjective':score,'auditionPcmHash':audio_hash(pcm),
                        'auditionWavSha256':file_hash(dest/file),'auditionTransform':'single peak normalization and PCM16',
                        'targetsSha256':file_hash(OUT/'targets.json'),
                        'preferenceNeuralV2':float(metric.distances(descriptor,describe(pcm))[0]),
                        'selectionPolicy':frozen['listeningPolicy']}})
            assert 2<=len(finalists)<=3
            saved = dict(complete=True,target=target,targetsSha256=file_hash(OUT/'targets.json'),
                reference=reference_info,folder=dest.name,pools=saved_pools,finalists=finalists,
                failures=failures,seconds=time.monotonic()-started,
                summary=dict(oldBest=old_best['score'],newBest=new_best['score'],originalBfxr=bfxr_candidate['score'],
                    rawSpecialist=min(c['score'] for c in new_raw),oldEngine=old_best['synth'],newEngine=new_best['synth'],
                    oldRawCandidates=len(old_raw),newRawCandidates=len(new_raw),oldSearch=256,newSearch=256,
                    originalEvaluations=bfxr_candidate['provenance']['evaluations']))
            _json_write(dest/'result.json',saved)
            rows.append(saved)
            print(json.dumps(dict(done=index+1,summary=saved['summary'],seconds=saved['seconds'])),flush=True)
    result = dict(complete=True,targetsSha256=file_hash(OUT/'targets.json'),scriptSha256=file_hash(__file__),
        checkpoints=frozen['checkpoints'],rows=rows)
    _json_write(OUT/'results.json',result)
    _json_write(BASE/'evaluations/specialists-tagged-v1-evaluation.json',dict(complete=True,
        reportSha256=file_hash(OUT/'results.json'),targetsSha256=file_hash(OUT/'targets.json'),
        scriptSha256=file_hash(__file__),checkpoints=frozen['checkpoints'],
        rows=[dict(source=r['target']['source'],summary=r['summary'],seconds=r['seconds']) for r in rows],
        scope='Five preselected tagged files, no previously judged exact file/PCM. Not source-family holdout or population success estimate. More engines use more total compute. No new human adequacy yet.'))


def publish():
    if GALLERY.exists():
        raise FileExistsError('Preserve published experiment')
    report = json.loads((OUT/'results.json').read_text())
    assert report['complete'] and report['scriptSha256']==file_hash(__file__)
    GALLERY.mkdir()
    records = []
    for row in report['rows']:
        folder = row['folder']
        dest = GALLERY/folder
        dest.mkdir()
        for file in ['target.wav']+[c['file'] for c in row['finalists']]:
            (dest/file).write_bytes((OUT/folder/file).read_bytes())
        records.append(dict(folder=folder, source=row['target']['source'], candidates=row['finalists'],
            note='Choose the closest, then say how close it is. None are close is a useful answer.'))
    model = export_coverage(GALLERY,records,dict(experiment='specialists-tagged-v1-listening',complete=True,
        targetCount=5,galleryTitle='Five new tagged sounds',humanReviewRequired=True,
        galleryIntro=['Five short tagged references. Choose the closest, then say how close it is.',
            'Each trial compares the strongest older-system output and a new specialist recreation; a third option retains original Bfxr or a distinct unrefined specialist.',
            'Options are shuffled. Every replay starts from the beginning.'],
        reportSha256=file_hash(OUT/'results.json'),scriptSha256=file_hash(__file__),
        targetsSha256=report['targetsSha256'],checkpoints=report['checkpoints'],
        uiCodeHashes={p.name:file_hash(p) for p in BASE.glob('quick_*') if p.is_file()}))
    print(json.dumps(dict(url='http://127.0.0.1:8765/'+str(GALLERY/'index.html'),experimentId=model['experimentId'])),flush=True)


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=['freeze','run','publish'])
    args = parser.parse_args()
    torch.set_num_threads(1)
    {'freeze':freeze,'run':run,'publish':publish}[args.action]()
