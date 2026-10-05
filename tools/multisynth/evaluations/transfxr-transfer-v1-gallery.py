"""Six fixed listening probes of input robustness and external sound transfer."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import soundfile as sf
from multisynth.renderer import Renderer
from multisynth.coverage_feedback import export_coverage
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash,_json_write
from neural_invert.experiment import audition_pcm

CHOICES=[('Transfxr-selection-17860/mp3-32k','Warbling sweep · MP3 32 kbps'),
 ('Transfxr-selection-17860/transpose+5','Warbling sweep · up five semitones'),
 ('Transfxr-selection-17445/lowpass-1800','Short texture · low-pass filtered'),
 ('external-Bfxr','New sound from Bfxr'),('external-Boomr','New sound from Boomr'),('external-Pluckr','New sound from Pluckr')]

def run():
    root=Path('tools/multisynth/runs/transfxr-transfer-v1');report=json.loads((root/'results.json').read_text())
    audit=Path('tools/multisynth/evaluations/transfxr-transfer-v1-audit.json')
    checked=json.loads(audit.read_text());assert report['complete'] and checked['complete'] and checked['reportSha256']==file_hash(root/'results.json')
    source_audit=Path('tools/multisynth/evaluations/transfxr-transfer-v1-source-audit.json')
    assert json.loads(source_audit.read_text())['manifestSha256']==report['manifestSha256']
    out=Path('tools/multisynth/runs/transfxr-transfer-v1-listening');out.mkdir(exist_ok=False)
    byid={r['target']['id']:r for r in report['rows']};records=[]
    def read(c):
        assert file_hash(c['waveFile'])==c['waveFileSha256']
        wave,rate=sf.read(c['waveFile'],dtype='float32');assert rate==44100 and audio_hash(wave)==c['audioHash'];return wave
    def save(path,wave):
        heard=audition_pcm(wave);sf.write(path,heard,44100,subtype='PCM_16')
        decoded,rate=sf.read(path,dtype='float32');assert rate==44100 and np.array_equal(decoded,heard)
        return dict(actualRenderAudioHash=audio_hash(wave),auditionPcmSha256=audio_hash(heard),auditionWavSha256=file_hash(path),auditionTransform='single peak normalization to 0.5 and PCM16 quantization')
    with Renderer() as renderer:
        for i,(identity,label) in enumerate(CHOICES):
            row=byid[identity];t=row['target'];folder=f'{i+1:03d}';dest=out/folder;dest.mkdir()
            reference=save(dest/'target.wav',read(t))
            if 'baseId' in t:
                clean=dict(byid[t['baseId']+'/clean']['selected']['ensemble'],
                           score=row['frozenClean']['ensemble']['score'])
                alternatives=[('frozen-clean','Prediction from clean input',clean),('adapted','Prediction from altered input',row['selected']['ensemble'])]
                note='Reference is the altered sound. Compare a prediction made from the clean source with a prediction made from this altered input.'
            else:
                alternatives=[('old','Earlier Transfxr model',row['selected']['old-eight']),('ensemble','Combined Transfxr models',row['selected']['ensemble'])]
                note='Reference comes from another synthesizer. Every recreation uses Transfxr.'
            record=dict(folder=folder,source=dict(name=label,sha256=reference['auditionWavSha256'],sourceTarget=t),referenceProvenance=reference,note=note,candidates=[])
            seen=set()
            for role,title,c in alternatives:
                audio=read(c)
                if audio_hash(audio) in seen:continue
                seen.add(audio_hash(audio));p,replay=renderer.render('Transfxr',c['params'],c['seed'])
                assert p==c['params'] and np.array_equal(audio,replay)
                info=save(dest/(role+'.wav'),audio)
                record['candidates'].append(dict(c,synth='Transfxr',role=role,label=title,file=role+'.wav',sourceHash=renderer.inventory['sourceHash'],
                    provenance={**c['provenance'],**info,'transferReportSha256':file_hash(root/'results.json'),'sourceCase':identity,'comparisonRole':role}))
            records.append(record)
    metadata=dict(experiment='transfxr-transfer-v1-listening',complete=True,targetCount=6,galleryTitle='Does the match survive changes?',humanReviewRequired=True,
        galleryIntro=['Six short checks: three altered inputs, then three sounds made by other synths. All recreations use Transfxr.',
            'Choose the closer match, tie, or None are close. For altered inputs, the reference is the altered sound; match what you hear.',
            'The first three compare predictions from clean and altered input. The others compare the earlier model with the combined models. Identical outputs appear once.',
            'These are fixed diagnostic examples, not a representative success rate. A quick overall comment on whether any are convincing would help.'],
        selectionReason='Fixed cases: warble MP3-32k and +5 semitones, texture lowpass-1800, new native Bfxr/Boomr/Pluckr. No selection by match-score improvement.',
        reportSha256=file_hash(root/'results.json'),auditSha256=file_hash(audit),sourceAuditSha256=file_hash(source_audit),scriptSha256=file_hash(__file__),
        checkpoints=report['checkpoints'],uiCodeHashes={p.name:file_hash(p) for p in Path('tools/multisynth').glob('quick_*') if p.is_file()})
    model=export_coverage(out,records,metadata)
    receipt=dict(complete=True,experimentId=model['experimentId'],htmlSha256=file_hash(out/'index.html'),resultsSha256=file_hash(out/'results.json'),
                 audioFiles={str(p.relative_to(out)):file_hash(p) for p in out.glob('*/*.wav')},scope='All selected DSP replay and single audition transform verified.')
    _json_write(out/'export-audit.json',receipt)
    _json_write(Path('tools/multisynth/evaluations/transfxr-transfer-v1-listening-audit.json'),receipt)
    print(json.dumps(dict(url='http://127.0.0.1:8765/'+str(out/'index.html'),experimentId=model['experimentId'],audios=len(receipt['audioFiles']))),flush=True)
if __name__=='__main__':run()
