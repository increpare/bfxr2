"""Publish all fixed transfer sources and five preselected native controls."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.coverage import verify_archived_audio, copy_archived_audio
from multisynth.coverage_feedback import export_coverage
from multisynth.renderer import Renderer
from multisynth.soft_periodicity import SoftPeriodicityObjective
from neural_invert.benchmark import audio_hash, exact_replay
from neural_invert.coverage_mixture_eval import read_wave
from neural_invert.data import file_hash, _json_write
from neural_invert.experiment import audition_pcm

BASE = Path('tools/multisynth')
ROOT = BASE/'runs/squishr-v1'
OUT = BASE/'runs/squishr-v1-listening'


def main():
    if OUT.exists():
        raise FileExistsError('Preserve published listening experiment')
    torch.set_num_threads(1)
    frozen = json.loads((ROOT/'targets.json').read_text())
    report = json.loads((ROOT/'evaluation/results.json').read_text())
    assert report['complete'] and report['binding']['targetsSha256']==file_hash(ROOT/'targets.json')
    assert report['mutationAttempts']==9472
    ids = frozen['listeningIds']
    selected = [next(r for r in report['rows'] if r['target']['id']==target_id) for target_id in ids]
    assert len(selected)==10 and len(set(ids))==10
    OUT.mkdir()
    records, checks = [], []
    with Renderer() as renderer:
        assert renderer.inventory['sourceHash']==report['sourceHash']
        for index, row in enumerate(selected):
            folder = OUT/f'{index+1:03d}'
            folder.mkdir()
            target = row['target']
            reference = read_wave(row['reference'])
            soft, legacy = SoftPeriodicityObjective(reference), MatchObjective(reference)
            sf.write(folder/'target.wav',reference,44100,subtype='PCM_16')
            reread,sr = sf.read(folder/'target.wav',dtype='float32')
            assert sr==44100 and np.array_equal(reread,reference)
            if 'source' in target:
                source = target['source']
            else:
                texture_names = ('Slime','Bubbles','Suction','Splat','Gulp','Spring')
                texture = int(target['sourceParams']['texture'])
                source = dict(name=f'Reserved {texture_names[texture].lower()} sound ({target["id"]})',
                    sha256=target['sourceAudioHash'],sourceSynth='Squishr',sourceParams=target['sourceParams'],
                    sourceSeed=target['sourceSeed'],sourceHash=report['sourceHash'])
            candidates, seen = [], set()
            if 'retainedCandidate' in target:
                archive = Path(target['referenceArchive'])
                assert file_hash(archive/'manifest.json')==target['archiveManifestSha256']
                verify_archived_audio(archive,target['referenceAudio'])
                archived_reference,sr = sf.read(archive/target['referenceAudio']['file'],dtype='float32')
                assert sr==44100 and np.array_equal(reference,archived_reference)
                c = target['retainedCandidate']
                verify_archived_audio(archive,c['audio'])
                old,sr = sf.read(archive/c['audio']['file'],dtype='float32')
                assert sr==44100
                seen.add(audio_hash(old))
                copy_archived_audio(archive/c['audio']['file'],folder/'retained.wav')
                candidates.append({**c,'role':'previous','label':'Earlier approved recreation','file':'retained.wav',
                    'provenance':{**c['provenance'],'retainedArchive':str(archive),'retainedCandidateId':c['id'],
                        'retainedManifestSha256':file_hash(archive/'manifest.json'),'previousAdequacy':'very-close',
                        'auditionTransform':'Exact archived PCM, no normalization'}})
            for arm in ('shared','specialist'):
                c = row['arms'][arm]['refined']
                assert c['sourceHash']==report['sourceHash']
                wave = read_wave(c)
                exact_replay({**c,'wave':wave},renderer,None)
                heard = audition_pcm(wave)
                assert audio_hash(heard)==c['auditionHash']
                if audio_hash(heard) in seen:
                    continue
                seen.add(audio_hash(heard))
                filename = arm+'.wav'
                sf.write(folder/filename,heard,44100,subtype='PCM_16')
                reread,sr = sf.read(folder/filename,dtype='float32')
                assert sr==44100 and np.array_equal(reread,heard)
                assert abs(soft.score(reread)-c['score'])<1e-6
                assert abs(legacy.score(reread)-c['legacyScore'])<1e-6
                candidates.append({**c,'role':'selected' if arm=='shared' else 'alternative',
                    'label':'Shared Squishr head' if arm=='shared' else 'Dedicated Squishr expert','file':filename,
                    'provenance':{**c['provenance'],'evaluationReportSha256':file_hash(ROOT/'evaluation/results.json'),
                        'auditionWavSha256':file_hash(folder/filename),'auditionTransform':'Single peak normalization and PCM16'}})
                candidates[-1]['provenance'].update(auditionMatchObjective=c['legacyScore'],softPeriodicity=c['score'])
            # Stop before publication if a target cannot form a comparison.
            assert 2<=len(candidates)<=3
            records.append(dict(folder=folder.name,source=source,candidates=candidates,
                note='Choose the closest, then how close it sounds. '+('Tagged recording transfer test.' if target['group'].startswith('tagged') else 'Reserved native synth reference; preset families still overlap training.')))
            checks.append(dict(targetId=target['id'],group=target['group'],optionCount=len(candidates),
                options=[dict(role=c['role'],synth=c['synth'],origin=c.get('origin'),file=c['file']) for c in candidates]))
    metadata = dict(experiment='squishr-v1-listening',complete=True,targetCount=10,
        galleryTitle='Can the new Squishr expert recreate these?',galleryIntro=[
            'Ten short comparisons: five tagged recordings, then five reserved synth sounds. Take the optional break after five.',
            'Compare the existing Squishr head with a newly trained dedicated expert. Both receive the same small search budget. The earlier approved footstep is included unchanged.',
            'Choose the closest, then tell us whether it is very close, roughly similar, or only least-bad. None close and ties are useful answers.'],
        humanReviewRequired=True,reportSha256=file_hash(ROOT/'evaluation/results.json'),
        targetsSha256=file_hash(ROOT/'targets.json'),scriptSha256=file_hash(__file__),
        selectionPolicy='Five fixed tagged references then first five seeded native test controls; no score-based target selection. Both arms refined with same objective and 128 attempts; exact approved anchor retained. Deduplicate exact candidate PCM.',
        scope='Squishr expert development comparison, not an all-synth system benchmark or a population quality estimate.',
        uiCodeHashes={p.name:file_hash(p) for p in BASE.glob('quick_*') if p.is_file()})
    model = export_coverage(OUT,records,metadata)
    page = (OUT/'index.html').read_text()
    needle = '<p class="quick-help">'
    assert page.count(needle)==1
    page = page.replace(needle,needle+'<b>10 comparisons · first 5 tagged, last 5 synth references.</b> ')
    (OUT/'index.html').write_text(page)
    _json_write(BASE/'evaluations/squishr-v1-listening-audit.json',dict(complete=True,
        experimentId=model['experimentId'],checks=checks,resultsSha256=file_hash(OUT/'results.json'),
        htmlSha256=file_hash(OUT/'index.html'),scriptSha256=file_hash(__file__),
        reportSha256=file_hash(ROOT/'evaluation/results.json'),
        audioFiles={str(p.relative_to(OUT)):file_hash(p) for p in sorted(OUT.glob('*/*.wav'))}))
    print(json.dumps(dict(experimentId=model['experimentId'],checks=checks)),flush=True)


if __name__=='__main__':
    main()
