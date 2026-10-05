"""Frozen Transfxr local-gradient test. Run from repository root with PYTHONPATH=tools."""
from copy import deepcopy
import json
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from match.objective import MatchObjective
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash, _json_write, parameter_hash
from neural_invert.features import describe
from neural_invert.forward import load_forward, feature_loss
from neural_invert.forward_probe import _normalization, _loss, _fixed_controls
from neural_invert.local_gradient import local_step, primary_gate, POLICY
from neural_invert.pitch_v5_eval import descriptor_pitch, compare_descriptor_pitch
from neural_invert.schema import ControlSchema
from neural_invert.onset_train import load, predict
from neural_invert.evaluate import rendered_candidates


def summarize(rows, key):
    before = [r['before'] for r in rows]
    after = [r['steps'][key] for r in rows]
    return dict(cases=len(rows),
        improvements=sum(b['featureLoss']['total'] < a['featureLoss']['total'] for a,b in zip(before,after)),
        meanBefore=float(np.mean([a['featureLoss']['total'] for a in before])),
        meanAfter=float(np.mean([a['featureLoss']['total'] for a in after])),
        meanObjectiveBefore=float(np.mean([a['objective'] for a in before])),
        meanObjectiveAfter=float(np.mean([a['objective'] for a in after])),
        surrogateImprovements=sum(b['surrogateLoss'] < a['surrogateLoss'] for a,b in zip(before,after)),
        additionalSilence=sum(b['silent'] and not a['silent'] for a,b in zip(before,after)),
        reliablePitchLosses=sum(r['targetPitch']['reliable'] and a['pitch']['reliable'] and not b['pitch']['reliable'] for r,a,b in zip(rows,before,after)),
        staticPitchLosses=sum(r['static'] and a['pitchComparison']['medianErrorSemitones'] is not None
            and a['pitchComparison']['medianErrorSemitones'] <= 1
            and (b['pitchComparison']['medianErrorSemitones'] is None or b['pitchComparison']['medianErrorSemitones'] > 1)
            for r,a,b in zip(rows,before,after)),
        movingDirectionLosses=sum(r['moving'] and a['pitchComparison']['directionMatches'] is True
            and b['pitchComparison']['directionMatches'] is not True for r,a,b in zip(rows,before,after)))


def run():
    torch.set_num_threads(1)
    source = Path('tools/multisynth/evaluations/local-gradient-v1-targets.json')
    output = Path('tools/multisynth/runs/local-gradient-v1')
    if output.exists(): raise FileExistsError('Fresh output required')
    frozen = json.loads(source.read_text())
    rows = [r for r in frozen['rows'] if r['sourceSynth'] == 'Transfxr']
    assert len(rows) == POLICY['cases'] and len({r['id'] for r in rows}) == len(rows)
    model, metadata = load_forward('tools/multisynth/runs/forward-audio-pilot-v1/model/Transfxr')
    schema = ControlSchema(metadata['spec'])
    inverse, inverse_meta = load('tools/multisynth/runs/onset-v1/models/Transfxr/control')
    training_file = Path('tools/multisynth/runs/neural-v2/data/Transfxr.json')
    assert file_hash(training_file) == metadata['datasetFiles']['metadataSha256']
    training = json.loads(training_file.read_text())
    trained = {training['rows'][i]['parameterHash'] for i in training['train']}
    assert all(r['parameterHash'] not in trained for r in rows)
    inverse_source = Path(inverse_meta['sourcePath'])
    assert file_hash(inverse_source/'manifest.json') == frozen['sourceManifestSha256']
    assert file_hash(inverse_source/'Transfxr.json') == frozen['sourceMetadataSha256']
    inverse_rows = json.loads((inverse_source/'Transfxr.json').read_text())
    inverse_trained = {inverse_rows['rows'][i]['parameterHash'] for i in inverse_rows['train']}
    for row in rows:
        original = inverse_rows['rows'][row['sourceRow']]
        assert row['sourceRow'] in inverse_rows['val']
        assert row['sourceParams'] == original['params'] and row['sourceSeed'] == original['seed']
        assert row['audioHash'] == original['audioHash']
        assert row['parameterHash'] == parameter_hash(original) == original['parameterHash']
        assert row['parameterHash'] not in inverse_trained | trained
    for weight in model.parameters(): weight.requires_grad_(False)
    mean,std = _normalization(metadata, 'cpu')
    output.mkdir()
    report = dict(complete=False, sourceReportSha256=file_hash(source),
        codeSha256=file_hash(__file__), helperSha256=file_hash('tools/neural_invert/local_gradient.py'),
        diagnosticCodeHashes={str(p):file_hash(p) for p in [
            *Path('tools/match').glob('*.py'), *Path('tools/neural_invert').glob('pitch_v5*.py'),
            Path('tools/neural_invert/forward_probe.py')]},
        checkpointSha256=metadata['checkpointHash'], normalizationHash=metadata['normalizationHash'],
        inverseCheckpointSha256=file_hash('tools/multisynth/runs/onset-v1/models/Transfxr/control/best.pt'),
        forwardTrainingMetadataSha256=file_hash(training_file), targetControlsAbsentFromForwardTraining=True,
        policy=POLICY, rows=[])
    with Renderer() as renderer:
        for row in rows:
            assert row['sourceHash'] == renderer.inventory['sourceHash'] == metadata['sourceHash']
            p,target = renderer.render('Transfxr', row['sourceParams'], row['sourceSeed'])
            assert p == row['sourceParams'] and audio_hash(target) == row['audioHash']
            objective = MatchObjective(target)
            proposals = predict(inverse,inverse_meta,target,renderer,count=4)
            accepted,failures = rendered_candidates(proposals,renderer,objective)
            assert accepted
            previous = min(accepted,key=lambda c:c['score'])
            p,before = renderer.render('Transfxr', previous['params'], previous['seed'])
            assert p == previous['params'] and np.array_equal(before,previous['wave'])
            folder = output/row['id']; folder.mkdir()
            sf.write(folder/'target.wav', target, 44100, subtype='FLOAT')
            features,target_pitch = describe(target),descriptor_pitch(target)
            unit,cats = schema.encode(previous['params'])
            u = torch.tensor(unit[None], requires_grad=True)
            c = torch.tensor(cats[None], dtype=torch.long)
            normalized = ((torch.tensor(features)-mean)/std)[None]
            loss,_ = feature_loss(model(u,c),normalized)
            loss.backward()
            gradient = u.grad[0].numpy().copy()
            assert np.isfinite(gradient).all()

            def save(label, params, wave):
                _fixed_controls(schema, previous['params'], params)
                x,category = schema.encode(params)
                with torch.no_grad():
                    surrogate,_ = feature_loss(model(torch.tensor(x[None]),torch.tensor(category[None],dtype=torch.long)), normalized)
                path=folder/(label+'.wav');sf.write(path,wave,44100,subtype='FLOAT')
                decoded,rate=sf.read(path,dtype='float32')
                assert rate==44100 and np.array_equal(decoded,wave)
                pitch=descriptor_pitch(wave)
                return dict(params=params,seed=previous['seed'],audioHash=audio_hash(wave),
                    waveFile=str(path.resolve()),waveFileSha256=file_hash(path),
                    featureLoss=_loss(describe(wave),features,metadata),surrogateLoss=float(surrogate),
                    objective=float(objective.score_batch([wave])[0]),
                    silent=bool(not wave.size or np.max(np.abs(wave)) <= 1e-8),
                    pitch=pitch,pitchComparison=compare_descriptor_pitch(target_pitch,pitch))

            result=dict(id=row['id'],stratum=row['stratum'],targetPitch=target_pitch,
                initialProposalScores=[c['score'] for c in accepted],initialProposalFailures=failures,
                targetParams=row['sourceParams'],targetSeed=row['sourceSeed'],targetAudioHash=row['audioHash'],
                targetWaveFileSha256=file_hash(folder/'target.wav'),
                static=bool(target_pitch['reliable'] and target_pitch['spanSemitones']<=1),
                moving=bool(target_pitch['reliable'] and target_pitch['direction'] in (-1,1)),
                gradient=gradient.tolist(),before=save('before',previous['params'],before),steps={})
            for radius in (.001,.005,.02):
                for direction in (1,-1):
                    updated=local_step(unit,gradient,radius,direction)
                    params=deepcopy(previous['params'])
                    for control,value in zip(schema.continuous,updated):
                        schema._write(params,control['path'],float(control['min']+value*(control['max']-control['min'])))
                    canonical,wave=renderer.render('Transfxr',params,previous['seed'])
                    key=f'{radius:g}-{direction:+d}'
                    result['steps'][key]=save(key,canonical,wave)
            report['rows'].append(result)
            _json_write(output/'results.json',report)
            print(json.dumps(dict(id=row['id'],before=result['before']['featureLoss']['total'],
                after=result['steps']['0.005-+1']['featureLoss']['total'])),flush=True)
    report['summaries']={key:summarize(report['rows'],key) for key in report['rows'][0]['steps']}
    report['primaryGate']=primary_gate(report['summaries']['0.005-+1'])
    report['complete']=True
    _json_write(output/'results.json',report)
    print(json.dumps(dict(summaries=report['summaries'],primaryGate=report['primaryGate'])),flush=True)


if __name__=='__main__': run()
