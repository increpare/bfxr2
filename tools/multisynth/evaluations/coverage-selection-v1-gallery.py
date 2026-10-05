"""Three deliberately selected self-inversion checks for human calibration."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from multisynth.coverage_feedback import export_coverage
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash, _json_write
from neural_invert.experiment import audition_pcm

CHOICES=[('Transfxr-selection-17860','Warbling sweep'),
         ('Transfxr-selection-17445','Short texture'),
         ('Transfxr-selection-21373','Bouncing rise')]


def save_audition(path,wave):
    heard=audition_pcm(wave)
    sf.write(path,heard,44100,subtype='PCM_16')
    actual,rate=sf.read(path,dtype='float32')
    assert rate==44100 and np.array_equal(actual,heard)
    return dict(actualRenderAudioHash=audio_hash(wave),auditionWavSha256=file_hash(path),
        auditionPcmSha256=audio_hash(heard),auditionTransform='single peak normalization to 0.5 and PCM16 quantization')


def run():
    source=Path('tools/multisynth/runs/coverage-selection-v1/results.json')
    report=json.loads(source.read_text())
    audit_path=Path('tools/multisynth/evaluations/coverage-selection-v1-audit.json')
    audit=json.loads(audit_path.read_text())
    assert report['complete'] and report['numericalGatePassed']
    assert audit['complete'] and audit['reportSha256']==file_hash(source)
    output=Path('tools/multisynth/runs/coverage-selection-v1-listening')
    if output.exists():raise FileExistsError('Fresh listening export required')
    output.mkdir(parents=True)
    records=[]
    metadata=dict(experiment='coverage-selection-v1-listening',complete=True,targetCount=3,
        galleryTitle='Three quick self-inversion checks',humanReviewRequired=True,
        galleryIntro=['Three new synth-generated references whose exact control groups were held out of training. Both systems get eight proposals.',
            'Choose the closer recreation, a tie, or none. A relative winner is not automatically convincing.',
            'Please also tell me whether any is a convincing recreation. These are deliberately selected diagnostics, not a representative quality estimate.',
            'This checks pitch gestures and texture before wider training. The real-recording search remains separate.'],
        selectionReason='Two pitch gestures and one tracker-uncertain texture where expanded proposals improve distance; includes agreement and safeguard disagreement cases. Selected after evaluation, not a random sample.',
        sourceReportSha256=file_hash(source),auditSha256=file_hash(audit_path),scriptSha256=file_hash(__file__),
        checkpoints=report['checkpoints'],policy=report['policy'],
        uiCodeHashes={p.name:file_hash(p) for p in Path('tools/multisynth').glob('quick_*') if p.is_file()})
    with Renderer() as renderer:
        for index,(identity,label) in enumerate(CHOICES):
            row=next(r for r in report['fresh'] if r['target']['id']==identity)
            target=row['target'];assert target['sourceHash']==renderer.inventory['sourceHash']
            p,wave=renderer.render('Transfxr',target['sourceParams'],target['sourceSeed'])
            assert p==target['sourceParams'] and audio_hash(wave)==target['audioHash']
            folder=f'{index+1:03d}';dest=output/folder;dest.mkdir()
            reference=save_audition(dest/'target.wav',wave)
            record=dict(folder=folder,source=dict(name=label+' · held-out Transfxr',
                sha256=reference['auditionWavSha256'],synthetic=True,sourceTarget=target),
                referenceProvenance=reference,candidates=[],
                note='Known-synth diagnostic. Relative preference does not imply a convincing recreation.')
            for arm,role,title in [('old-eight','previous','Previous expert · eight proposals'),
                ('guarded-ensemble','expanded','Combined experts · four plus four')]:
                c=row['selections'][arm]
                assert file_hash(c['waveFile'])==c['waveFileSha256']
                audio,rate=sf.read(c['waveFile'],dtype='float32')
                assert rate==44100 and audio_hash(audio)==c['audioHash']
                p,replay=renderer.render(c['synth'],c['params'],c['seed'])
                assert p==c['params'] and np.array_equal(replay,audio)
                filename=role+'.wav';audition=save_audition(dest/filename,audio)
                card=dict(c,role=role,label=title,file=filename,sourceHash=renderer.inventory['sourceHash'],
                    provenance={**c['provenance'],**audition,'selectionArm':arm,'sourceReportSha256':file_hash(source),
                        'sourceTargetId':identity,'selectionPolicy':report['policy'] if arm=='guarded-ensemble' else 'lowest rendered distance from eight old-expert proposals'})
                record['candidates'].append(card)
            assert len({c['provenance']['auditionPcmSha256'] for c in record['candidates']})==2
            records.append(record)
    model=export_coverage(output,records,metadata)
    _json_write(output/'export-audit.json',dict(complete=True,experimentId=model['experimentId'],
        resultsSha256=file_hash(output/'results.json'),htmlSha256=file_hash(output/'index.html'),
        audioFiles={str(p.relative_to(output)):file_hash(p) for p in output.glob('*/*.wav')},
        scope='All references and candidates replayed exactly; single audition transform verified after PCM16 write. No human quality verdict.'))
    print(json.dumps(dict(path=str(output/'index.html'),experimentId=model['experimentId'])),flush=True)


if __name__=='__main__':run()
