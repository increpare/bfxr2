"""Publish selected new specialist comparisons, preserving historical audition PCM."""
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from match.objective import MatchObjective
from multisynth.coverage import copy_archived_audio, verify_archived_audio
from multisynth.coverage_feedback import export_coverage
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.coverage_mixture_eval import read_wave
from neural_invert.data import file_hash, _json_write
from neural_invert.experiment import audition_pcm

BASE = Path('tools/multisynth')
REPORT = BASE/'runs/specialists-v1/evaluation/results.json'
SELECTION = BASE/'evaluations/specialists-v1-listening-targets.json'
OUT = BASE/'runs/specialists-v1-listening'


def main():
    if OUT.exists():
        raise FileExistsError('Preserve existing listening page')
    report = json.loads(REPORT.read_text())
    selection = json.loads(SELECTION.read_text())
    assert report['complete'] and selection['reportSha256']==file_hash(REPORT)
    assert 1 <= len(selection['rows']) <= 6
    rows = {r['target']['id']:r for r in report['rows']}
    OUT.mkdir()
    records, checks = [], []
    with Renderer() as renderer:
        for index, item in enumerate(selection['rows']):
            row = rows[item['id']]
            folder = f'{index+1:03d}'
            dest = OUT/folder
            dest.mkdir()
            reference = read_wave(row['target'])
            # Evaluation reference already is audition PCM, so no transform here.
            assert np.array_equal(reference, audition_pcm(reference))
            sf.write(dest/'target.wav',reference,44100,subtype='PCM_16')
            objective = MatchObjective(reference)
            new = row['selected'][item['newEngine']]
            assert item['newEngine'] in ('Boomr','Footsteppr')
            archive = None
            if item['baseline']=='archive':
                archive = Path(item['archive'])
                manifest = json.loads((archive/'manifest.json').read_text())
                target = next(t for t in manifest['targets'] if t['id']==item['archiveTargetId'])
                old = next(c for c in manifest['candidates'] if c['id']==item['archiveCandidateId'])
                assert old['id'] in {c['id'] for c in target['candidates']}
                verify_archived_audio(archive,target['referenceAudio'])
                verify_archived_audio(archive,old['audio'])
                heard, rate = sf.read(archive/target['referenceAudio']['file'],dtype='float32')
                assert rate==44100 and np.array_equal(heard,reference)
            else:
                assert item['baseline'] in ('Transfxr','old-Boomr','old-Footsteppr')
                old = row['selected'][item['baseline']]
            record = dict(folder=folder,source=dict(name=item['label'],sha256=file_hash(dest/'target.wav'),
                sourceTarget=row['target']),note='Choose the closer recreation, then say how close it is. None are close is useful feedback.',candidates=[])
            hashes = []
            options = [('previous',old),('selected',new)]
            if item.get('extraBaselineEngine'):
                assert item['extraBaselineEngine'] in ('Transfxr','old-Boomr','old-Footsteppr')
                options.append(('original',row['selected'][item['extraBaselineEngine']]))
            for role, c in options:
                path = dest/(role+'.wav')
                if role=='previous' and archive is not None:
                    copy_archived_audio(archive/c['audio']['file'],path)
                    source_hash = c['sourceHash']
                    provenance = dict(archiveManifestSha256=file_hash(archive/'manifest.json'),
                        archiveCandidateId=c['id'],auditionTransform='exact archived PCM, no additional normalization')
                else:
                    wave = read_wave(c)
                    params, replay = renderer.render(c['synth'],c['params'],c['seed'])
                    assert params==c['params'] and np.array_equal(wave,replay)
                    sf.write(path,audition_pcm(wave),44100,subtype='PCM_16')
                    source_hash = renderer.inventory['sourceHash']
                    provenance = dict(actualRenderAudioHash=audio_hash(wave),
                        auditionTransform='single peak normalization to 0.5 and PCM16 quantization')
                heard, rate = sf.read(path,dtype='float32')
                assert rate==44100
                hashes.append(audio_hash(heard))
                score = float(objective.score_batch([heard])[0])
                if role!='previous' or archive is None:
                    assert abs(score-c['score'])<1e-7 and audio_hash(heard)==c['auditionHash']
                record['candidates'].append({**c,'role':role,'label':'Comparison option','file':role+'.wav',
                    'sourceHash':source_hash,'provenance':{**c['provenance'],**provenance,
                        'auditionMatchObjective':score,'auditionPcmHash':audio_hash(heard),
                        'auditionWavSha256':file_hash(path),'sourceCase':item['id'],
                        'experimentReportSha256':file_hash(REPORT),'selectionReason':item['reason']}})
            assert len(set(hashes))==len(hashes)
            records.append(record)
            checks.append(dict(id=item['id'],candidateAudioHashes=hashes,scores=[c['provenance']['auditionMatchObjective'] for c in record['candidates']]))
    metadata = dict(experiment='specialists-v1-listening',complete=True,targetCount=len(records),
        galleryTitle='New synth experts · six short comparisons',humanReviewRequired=True,
        galleryIntro=['Choose the closest sound, then say how close it is before moving on.',
            'None are close and Skip advance immediately. Replay always starts at the beginning; your answers save locally.',
            'A mix of synthetic references and a tagged recording. Every pair contains a new recreation.'],
        reportSha256=file_hash(REPORT),selectionSha256=file_hash(SELECTION),scriptSha256=file_hash(__file__),
        checkpoints=report['checkpoints'],selectionPolicy=selection['policy'],
        uiCodeHashes={p.name:file_hash(p) for p in BASE.glob('quick_*') if p.is_file()})
    model = export_coverage(OUT,records,metadata)
    receipt = dict(complete=True,experimentId=model['experimentId'],htmlSha256=file_hash(OUT/'index.html'),
        resultsSha256=file_hash(OUT/'results.json'),checks=checks,
        audioFiles={str(p.relative_to(OUT)):file_hash(p) for p in OUT.glob('*/*.wav')},
        scope='Every new candidate DSP replayed; archived audio/reference exact; one audition transform; distinct candidate PCM; questionnaire unanswered by assistant.')
    _json_write(OUT/'export-audit.json',receipt)
    _json_write(BASE/'evaluations/specialists-v1-listening-audit.json',receipt)
    print(json.dumps(dict(url='http://127.0.0.1:8765/'+str(OUT/'index.html'),experimentId=model['experimentId'])),flush=True)


if __name__ == '__main__':
    main()
