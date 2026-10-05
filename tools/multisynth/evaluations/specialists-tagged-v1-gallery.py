"""Independently verify the frozen transfer run and export visible comparisons.

Use this exporter, not the unused publish action in the frozen run script.
It corrects two export metadata defects without altering evaluated audio:
the raw fallback needs a visible questionnaire role, and original Bfxr needs
its own actual renderer backend identity.
"""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.audio import prepare_target
from match.objective import MatchObjective
from match.renderer import BfxrRenderer
from multisynth.coverage import verify_archived_audio
from multisynth.coverage_feedback import export_coverage
from multisynth.features import describe
from multisynth.preference import PreferenceMetric
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash, exact_replay
from neural_invert.coverage_mixture_eval import read_wave
from neural_invert.data import file_hash, _json_write
from neural_invert.experiment import audition_pcm
from neural_invert.temporal_gallery import backend_provenance

BASE = Path('tools/multisynth')
OUT = BASE/'runs/specialists-tagged-v1'
GALLERY = BASE/'runs/specialists-tagged-v1-listening'
AUDIT = BASE/'evaluations/specialists-tagged-v1-listening-audit.json'


def main():
    if GALLERY.exists() or AUDIT.exists():
        raise FileExistsError('Preserve the published experiment')
    torch.set_num_threads(1)
    frozen = json.loads((OUT/'targets.json').read_text())
    report = json.loads((OUT/'results.json').read_text())
    assert report['complete'] and len(report['rows'])==5
    assert frozen['scriptSha256']==report['scriptSha256']==file_hash(BASE/'evaluations/specialists-tagged-v1.py')
    assert report['targetsSha256']==file_hash(OUT/'targets.json')
    assert report['checkpoints']==frozen['checkpoints']
    metric_path = BASE/'models/preference-neural-v2.json'
    assert file_hash(metric_path)==frozen['preferenceMetricSha256']
    metric = PreferenceMetric.load(metric_path)
    original_path = Path('/Users/stephenlavelle/Documents/bfxr2/.worktrees/inverse-model-next/tools/invert/runs/v7_real_ft/best.pt')
    paths = {'shared':BASE/'runs/neural-v2/acoustic-model/best.pt',
        'Transfxr':BASE/'runs/native-mixture-v1/models/mixture/best.pt',
        'Boomr':BASE/'runs/specialists-v1/models/Boomr/best.pt',
        'Footsteppr':BASE/'runs/specialists-v1/models/Footsteppr/best.pt', 'originalBfxr':original_path}
    assert {name:file_hash(path) for name,path in paths.items()}==report['checkpoints']
    old_files, old_pcm = set(), set()
    for file,sha in frozen['priorArchives'].items():
        assert file_hash(file)==sha
        archive = Path(file).parent
        for target in json.loads(Path(file).read_text())['targets']:
            old_files.add(target['source'].get('sha256'))
            verify_archived_audio(archive,target['referenceAudio'])
            samples,rate = sf.read(archive/target['referenceAudio']['file'],dtype='float32')
            assert rate==44100
            old_pcm.add(audio_hash(samples))
    records, checks = [], []
    replays = 0
    max_error = 0.
    with Renderer() as renderer, BfxrRenderer(jobs=1) as bfxr:
        backend = backend_provenance(bfxr)
        for target,row in zip(frozen['rows'],report['rows']):
            assert row['complete'] and row['target']==target
            assert row==json.loads((OUT/row['folder']/'result.json').read_text())
            assert row['targetsSha256']==report['targetsSha256']
            source = target['source']
            assert file_hash(source['path'])==source['sha256'] and source['sha256'] not in old_files
            reference = audition_pcm(prepare_target(source['path']))
            assert audio_hash(reference)==target['auditionHash'] and target['auditionHash'] not in old_pcm
            old_pcm.add(target['auditionHash'])
            assert np.array_equal(reference,read_wave(row['reference']))
            source_folder = OUT/row['folder']
            saved_reference,rate = sf.read(source_folder/'target.wav',dtype='float32')
            assert rate==44100 and np.array_equal(reference,saved_reference)
            objective = MatchObjective(reference)
            descriptor = describe(reference)
            pool_records = []
            for label,pool in row['pools'].items():
                for candidate in pool:
                    raw = read_wave(candidate)
                    exact_replay({**candidate,'wave':raw},renderer,bfxr)
                    replays += 1
                    heard = audition_pcm(raw)
                    assert audio_hash(heard)==candidate['auditionHash']
                    score = float(objective.score_batch([heard])[0])
                    error = abs(score-candidate['score'])
                    assert error<1e-6
                    max_error = max(error,max_error)
                    assert abs(float(metric.distances(descriptor,describe(heard))[0])-candidate['preferenceDistance'])<1e-7
                    if candidate.get('expert')!='original-bfxr':
                        assert candidate['sourceHash']==renderer.inventory['sourceHash']
                    if label in ('oldRefined','newRefined'):
                        refinement = candidate['provenance']['refinement']
                        assert refinement['budget']==128 and len(refinement['trace'])==129
                        assert refinement['finalScore']==candidate['score']
                        assert all(b<=a+1e-7 for a,b in zip(refinement['trace'],refinement['trace'][1:]))
                    pool_records.append(candidate)
            assert len(row['pools']['oldRefined'])==len(row['pools']['newRefined'])==2
            pools = row['pools']
            old = min(pools['oldRaw']+pools['oldRefined']+pools['original'],key=lambda c:c['score'])
            new = min(pools['newRaw']+pools['newRefined'],key=lambda c:c['score'])
            assert old['score']==row['summary']['oldBest'] and new['score']==row['summary']['newBest']
            expected = [('previous',old),('selected',new)]
            seen = {c['auditionHash'] for _,c in expected}
            original = pools['original'][0]
            if original['auditionHash'] not in seen:
                expected.append(('original',original))
            else:
                extra = next((c for c in sorted(pools['newRaw'],key=lambda c:c['score']) if c['auditionHash'] not in seen),None)
                if extra is not None:
                    expected.append(('raw',extra))
            unique,seen = [],set()
            for role,c in expected:
                if c['auditionHash'] not in seen:
                    unique.append((role,c));seen.add(c['auditionHash'])
            assert len(unique)==len(row['finalists'])
            cards = []
            for (role,expected_candidate),c in zip(unique,row['finalists']):
                assert c['role']==role and c['params']==expected_candidate['params'] and c['seed']==expected_candidate['seed']
                assert c['synth']==expected_candidate['synth'] and c['origin']==expected_candidate['origin']
                raw = read_wave(expected_candidate)
                pcm,rate = sf.read(source_folder/c['file'],dtype='float32')
                assert rate==44100 and np.array_equal(pcm,audition_pcm(raw))
                assert audio_hash(pcm)==c['provenance']['auditionPcmHash']
                assert file_hash(source_folder/c['file'])==c['provenance']['auditionWavSha256']
                assert abs(float(objective.score_batch([pcm])[0])-c['provenance']['auditionMatchObjective'])<1e-6
                original_backend = c.get('expert')=='original-bfxr'
                provenance = {**c['provenance'],'evaluationRole':role,'verifiedReportSha256':file_hash(OUT/'results.json')}
                if original_backend:
                    provenance['verifiedOriginalBackend'] = backend
                    provenance['backendBindingScope'] = 'Original run omitted separate backend hash; all saved original PCM exactly replayed against this bound backend after evaluation.'
                cards.append({**c,'role':'alternative' if role=='raw' else role,
                    'sourceHash':backend['sourceHash'] if original_backend else renderer.inventory['sourceHash'],
                    'provenance':provenance})
            records.append(dict(folder=row['folder'],source=source,candidates=cards,
                note='Choose the closest, then say how close it is. None are close is a useful answer.'))
            checks.append(dict(source=source['name'],referenceHash=audio_hash(reference),
                poolCandidates=len(pool_records),roles=[c['role'] for c in cards],
                candidates=[dict(role=c['role'],synth=c['synth'],pcmHash=c['provenance']['auditionPcmHash'],score=c['score']) for c in cards]))
            print(json.dumps(dict(verified=source['name'],replays=replays)),flush=True)
        assert backend==backend_provenance(bfxr)
    # Only create the gallery once the entire run passes independent checks.
    GALLERY.mkdir()
    for record in records:
        dest = GALLERY/record['folder'];dest.mkdir()
        for file in ['target.wav']+[c['file'] for c in record['candidates']]:
            (dest/file).write_bytes((OUT/record['folder']/file).read_bytes())
    model = export_coverage(GALLERY,records,dict(experiment='specialists-tagged-v1-listening',complete=True,
        targetCount=5,galleryTitle='Five new tagged sounds',humanReviewRequired=True,
        galleryIntro=['Five short tagged references. Choose the closest, then say how close it is.',
            'Compare recreations by gesture, pitch and character. None are close is useful feedback.',
            'Options are shuffled. Every replay starts from the beginning.'],
        reportSha256=file_hash(OUT/'results.json'),scriptSha256=file_hash(__file__),
        targetsSha256=report['targetsSha256'],checkpoints=report['checkpoints'],
        originalBackend=backend,selectionPolicy=frozen['listeningPolicy'],
        uiCodeHashes={p.name:file_hash(p) for p in BASE.glob('quick_*') if p.is_file()}))
    receipt = dict(complete=True,experimentId=model['experimentId'],scriptSha256=file_hash(__file__),
        evaluatedScriptSha256=report['scriptSha256'],reportSha256=file_hash(OUT/'results.json'),
        resultsSha256=file_hash(GALLERY/'results.json'),htmlSha256=file_hash(GALLERY/'index.html'),
        replayedCandidates=replays,maxScoreError=max_error,checks=checks,originalBackend=backend,
        corrections=['Use visible alternative role for raw fallback; quick questionnaire hides diagnostic raw roles.',
            'Original Bfxr sourceHash is the separately verified backend, not multisynth inventory. Original run backend was not pre-frozen; all saved original outputs exactly replayed against the bound current backend.'],
        audioFiles={str(p.relative_to(GALLERY)):file_hash(p) for p in GALLERY.glob('*/*.wav')},
        scope='Full source, reference, pool audio and finalist replay verification; all five preselected sources included, no score-based selection. No assistant judgments.')
    _json_write(AUDIT,receipt)
    _json_write(GALLERY/'export-audit.json',receipt)
    print(json.dumps(dict(url='http://127.0.0.1:8765/'+str(GALLERY/'index.html'),experimentId=model['experimentId'])),flush=True)


if __name__=='__main__':
    main()
