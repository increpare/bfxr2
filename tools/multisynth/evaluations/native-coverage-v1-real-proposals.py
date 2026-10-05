"""Private raw candidates on exactly the five rejected reference auditions."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.coverage_train import load
from neural_invert.data import file_hash,_json_write
from neural_invert.evaluate import rendered_candidates,serializable
from neural_invert.temporal import load_temporal,predict_temporal
from neural_invert.pitch_v5_eval import descriptor_pitch,compare_descriptor_pitch

torch.set_num_threads(1)
root=Path('tools/multisynth/runs/native-coverage-v1')
previous=Path('tools/multisynth/runs/pitch-calibration-listening-v1')
output=root/'real-proposals'
if output.exists():raise FileExistsError('Fresh proposal output required')
prior=json.loads((previous/'results.json').read_text());assert len(prior['results'])==5
models={arm:load(root/'models'/arm) for arm in ('control','expanded')}
models['frozen-v3']=load_temporal('tools/multisynth/runs/temporal-v3/hybrid-experts/Transfxr')
output.mkdir()
report=dict(complete=False,scriptSha256=file_hash(__file__),referenceReportSha256=file_hash(previous/'results.json'),
    checkpointHashes={arm:meta['checkpointHash'] for arm,(model,meta) in models.items()},
    scope='Five repeated development references with explicit zero convincing recreations; private raw pools, no listening promotion.',rows=[])
with Renderer() as renderer:
    for record in prior['results']:
        source=previous/record['folder']/'target.wav';wave,rate=sf.read(source,dtype='float32')
        assert rate==44100 and wave.ndim==1
        objective=MatchObjective(wave);pitch=descriptor_pitch(wave)
        directory=output/record['folder'];directory.mkdir()
        row=dict(source=record['source'],referenceWavSha256=file_hash(source),referenceFloatPcmSha256=audio_hash(wave),targetPitch=pitch,arms={})
        for arm,(model,meta) in models.items():
            proposals=predict_temporal(model,meta,wave,renderer,count=4)
            accepted,failures=rendered_candidates(proposals,renderer,objective)
            failures += [dict(error='missing proposal slot') for _ in range(4-len(proposals))]
            saved=[]
            for i,c in enumerate(accepted):
                path=directory/f'{arm}-{i}.wav';sf.write(path,c['wave'],44100,subtype='FLOAT')
                decoded,sr=sf.read(path,dtype='float32');assert sr==44100 and np.array_equal(decoded,c['wave'])
                p=descriptor_pitch(c['wave'])
                saved.append(dict(**serializable(c),waveFile=str(path.resolve()),waveFileSha256=file_hash(path),audioHash=audio_hash(c['wave']),
                                  pitch=p,pitchComparison=compare_descriptor_pitch(pitch,p)))
            row['arms'][arm]=dict(candidates=saved,failures=failures,selected=min(saved,key=lambda c:c['score']) if saved else None)
        report['rows'].append(row);_json_write(output/'results.json',report)
        print(json.dumps(dict(name=record['source']['name'],scores={a:r['selected']['score'] if r['selected'] else None for a,r in row['arms'].items()})),flush=True)
report['complete']=True;_json_write(output/'results.json',report)
