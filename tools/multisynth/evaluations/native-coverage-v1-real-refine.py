"""Private equal-budget seed test on the five rejected reference auditions."""
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.coverage_selection import select_candidate, POLICY
from neural_invert.data import _json_write, file_hash
from neural_invert.evaluate import serializable
from neural_invert.pitch_v5_eval import descriptor_pitch, compare_descriptor_pitch
from neural_invert.temporal_eval import refine_guarded, target_diagnostics


def run():
    torch.set_num_threads(1)
    root=Path('tools/multisynth/runs/native-coverage-v1')
    gate=Path('tools/multisynth/runs/coverage-selection-v1/results.json')
    eligibility=json.loads(gate.read_text())
    if not eligibility['complete'] or not eligibility['numericalGatePassed']:
        raise ValueError('Coverage selection did not pass numerical gate')
    prior=Path('tools/multisynth/runs/pitch-calibration-listening-v1')
    originals=json.loads((prior/'results.json').read_text())['results']
    raw_path=root/'real-proposals/results.json';raw=json.loads(raw_path.read_text());assert raw['complete']
    output=root/'real-refined'
    if output.exists():raise FileExistsError('Fresh real refinement required')
    output.mkdir()
    report=dict(complete=False,scriptSha256=file_hash(__file__),rawReportSha256=file_hash(raw_path),
        selectionGateSha256=file_hash(gate),policy=POLICY,
        codeHashes={str(p):file_hash(p) for p in [Path('tools/neural_invert/temporal_eval.py'),Path('tools/neural_invert/coverage_selection.py'),*Path('tools/match').glob('*.py')]},
        scope='Repeated development references. Same 384 local trials per arm with same seed, four raw starts scored then best refined. No human likeness claim.',rows=[])
    with Renderer() as renderer:
        for index,(r,original) in enumerate(zip(raw['rows'],originals)):
            assert r['source']==original['source']
            path=prior/original['folder']/'target.wav'
            assert file_hash(path)==r['referenceWavSha256']
            wave,rate=sf.read(path,dtype='float32');assert rate==44100
            objective=MatchObjective(wave);target=target_diagnostics(wave);pitch=descriptor_pitch(wave)
            directory=output/original['folder'];directory.mkdir()
            row=dict(source=r['source'],folder=original['folder'],referenceWavSha256=file_hash(path),targetPitch=pitch,arms={})
            for arm in ('control','expanded'):
                start=dict(r['arms'][arm]['selected'])
                assert file_hash(start['waveFile'])==start['waveFileSha256']
                start['wave'],rate=sf.read(start['waveFile'],dtype='float32')
                assert rate==44100 and audio_hash(start['wave'])==start['audioHash']
                p,replay=renderer.render(start['synth'],start['params'],start['seed'])
                assert p==start['params'] and np.array_equal(replay,start['wave'])
                # Remove file bindings to the initial candidate before refining its controls.
                for key in ('waveFile','waveFileSha256','audioHash','pitch','pitchComparison'):start.pop(key,None)
                refined=refine_guarded(start,renderer,objective,target,budget=384,seed=20261028+index*1009)
                p,replay=renderer.render(refined['synth'],refined['params'],refined['seed'])
                assert p==refined['params'] and np.array_equal(replay,refined['wave'])
                assert abs(float(objective.score_batch([replay])[0])-refined['score'])<1e-8
                path=directory/f'{arm}.wav';sf.write(path,replay,44100,subtype='FLOAT')
                cp=descriptor_pitch(replay)
                row['arms'][arm]=dict(**serializable(refined),waveFile=str(path.resolve()),waveFileSha256=file_hash(path),
                    audioHash=audio_hash(replay),pitch=cp,pitchComparison=compare_descriptor_pitch(pitch,cp))
                print(json.dumps(dict(name=r['source']['name'],arm=arm,score=refined['score'])),flush=True)
                _json_write(directory/f'{arm}.json',row['arms'][arm])
            row['selected']=select_candidate(pitch,row['arms']['control'],[row['arms']['expanded']])
            report['rows'].append(row);_json_write(output/'results.json',report)
    report['complete']=True;_json_write(output/'results.json',report)


if __name__=='__main__':run()
