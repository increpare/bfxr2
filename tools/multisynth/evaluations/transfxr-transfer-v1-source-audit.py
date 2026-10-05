"""Replay source DSP and every perturbation independently of inference."""
import importlib.util
import json
from pathlib import Path
import tempfile
import numpy as np
import soundfile as sf
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash,_json_write

root=Path('tools/multisynth/runs/transfxr-transfer-v1')
m=json.loads((root/'targets.json').read_text());assert m['complete']
p=Path('tools/multisynth/evaluations/transfxr-transfer-v1.py')
assert file_hash(p)==m['scriptSha256']
spec=importlib.util.spec_from_file_location('transfer_source',p);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
source=Path('tools/multisynth/runs/coverage-selection-v1/results.json');assert file_hash(source)==m['sourceReportSha256']
prior=json.loads(source.read_text());expected=[r['target']['id'] for r in prior['fresh'] if r['target']['id'] in module.ANCHORS]
expected += [r['target']['id'] for r in prior['fresh'] if r['target']['id'] not in module.ANCHORS][:5]
assert [t['baseId'] for t in m['targets'] if t.get('variant')=='clean']==expected
meta=json.loads(Path('tools/multisynth/runs/native-coverage-v1/data/Transfxr.json').read_text())
trained={meta['rows'][i]['parameterHash'] for i in meta['splits']['oldTrain']+meta['splits']['newTrain']}
real=Path('tools/multisynth/runs/pitch-calibration-listening-v1')
real_report=json.loads((real/'results.json').read_text())
replayed={};variants=0;realverified=0
with Renderer() as renderer, tempfile.TemporaryDirectory(prefix='transfxr-transfer-audit-') as tmp:
    assert renderer.inventory['sourceHash']==m['sourceHash']
    for i,t in enumerate(m['targets']):
        heard=module.read(t)
        if t['group']=='real-repeated':
            record=real_report['results'][int(t['id'].split('-')[1])]
            original=real/record['folder']/'target.wav'
            assert file_hash(original)==t['sourceWavSha256']
            original_pcm,rate=sf.read(original,dtype='float32')
            assert rate==44100 and np.array_equal(original_pcm,heard)
            realverified+=1;continue
        source=t['sourceTarget'];key=t.get('baseId',t['id'])
        if key not in replayed:
            p,w=renderer.render(t['sourceSynth'],source['sourceParams'],source['sourceSeed'])
            assert p==source['sourceParams'] and audio_hash(w)==source['audioHash']
            assert t['sourceGain']==.5/float(np.max(np.abs(w)))
            replayed[key]=(w*t['sourceGain']).astype(np.float32)
        normalized=replayed[key]
        if t['group']=='other-synth':assert np.array_equal(normalized,heard)
        else:
            assert source['parameterHash'] not in trained
            assert np.array_equal(normalized,module.read(t['sourceAudio']))
            scratch=Path(tmp)/str(i);scratch.mkdir()
            candidate,_=module.transform(Path(t['sourceAudio']['waveFile']),t['variant'],scratch/'out.wav')
            assert np.array_equal(candidate,heard);variants+=1
            if 'codecFileSha256' in t['transform']:
                assert file_hash(Path(t['waveFile']).with_suffix('.mp3'))==t['transform']['codecFileSha256']
assert variants==64 and realverified==5
observed=[t['sourceSynth'] for t in m['targets'] if t['group']=='other-synth']
assert set(observed)|{x['sourceSynth'] for x in m['failures']}==set(m['externalEngines'])
out=dict(complete=True,scriptSha256=file_hash(__file__),manifestSha256=file_hash(root/'targets.json'),
         sourceDspReplays=len(replayed),exactPerturbationReplays=variants,exactRepeatedRealSources=realverified,
         externalSynths=observed,failedExternalDraws=m['failures'],selfControlGroupsAbsentFromTraining=True,
         scope='DSP source and transformation parity. Shared families and pre-used development targets are not independent generalization.')
dest=Path('tools/multisynth/evaluations/transfxr-transfer-v1-source-audit.json');assert not dest.exists()
_json_write(dest,out);print(json.dumps(out),flush=True)
