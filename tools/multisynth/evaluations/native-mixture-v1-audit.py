"""Replay mixture validation and selected real-DSP audio without changing reports."""
import json
from pathlib import Path
import numpy as np
import torch
from match.objective import MatchObjective
from multisynth.renderer import Renderer
from neural_invert.coverage_mixture import load, validation, DATA
from neural_invert.coverage_train import read_data
from neural_invert.coverage_mixture_eval import read_wave, summarize, TRANSFER, EXCLUSIONS
from neural_invert.temporal import balanced_weights
from neural_invert.data import file_hash, _json_write, parameter_hash
from neural_invert.benchmark import audio_hash

ROOT=Path('tools/multisynth/runs/native-mixture-v1')

def run():
    torch.set_num_threads(1)
    manifest,meta,shard=read_data(DATA)
    split=meta['splits'];rows=meta['rows'];validation_report={}
    ids=torch.tensor(split['oldVal']);weights=torch.ones(len(rows));weights[ids]=balanced_weights(rows,split['oldVal'])
    for arm in ('single','mixture'):
        model,info=load(ROOT/'models'/arm)
        report=json.loads((ROOT/'models'/arm/'training.json').read_text())
        mean,std=(torch.tensor(info['normalization'][k]) for k in ('mean','std'))
        actual=validation(model,shard,ids,weights,mean,std,torch.device('cpu'))
        expected=next(r['validation']['original'] for r in report['history'] if r['step']==report['bestStep'])
        assert abs(actual['loss']-expected['loss'])<2e-6
        assert np.allclose(actual['responsibility'],expected['responsibility'],atol=2e-6)
        assert actual['winnerCounts']==expected['winnerCounts']
        validation_report[arm]=dict(bestStep=report['bestStep'],cpu=actual,recorded=expected,
                                   checkpointSha256=info['checkpointHash'])
    path=ROOT/'evaluation/results.json';report=json.loads(path.read_text());assert report['complete']
    targets=json.loads((ROOT/'evaluation/targets.json').read_text())
    assert file_hash(ROOT/'evaluation/targets.json')==report['manifestSha256']
    assert file_hash(TRANSFER)==targets['sourceReportSha256']
    assert file_hash(DATA/'manifest.json')==targets['dataManifestSha256']
    assert all(file_hash(p)==digest for p,digest in targets['exclusions'].items())
    assert file_hash('tools/neural_invert/coverage_mixture_eval.py')==targets['scriptSha256']==report['scriptSha256']
    assert all(file_hash(p)==h for p,h in report['codeHashes'].items())
    assert all(report['checkpoints'][a]==validation_report[a]['checkpointSha256'] for a in validation_report)
    assert len(report['rows'])==122 and len(targets['fresh'])==32
    transfer=json.loads(TRANSFER.read_text())
    transfer_by_id={r['target']['id']:r for r in transfer['rows']}
    assert targets['transferTargets']==[r['target']['id'] for r in transfer['rows']]
    expected_ids=targets['transferTargets']+[t['id'] for t in targets['fresh']]
    assert len(set(expected_ids))==len(expected_ids)
    assert [r['target']['id'] for r in report['rows']]==expected_ids
    fresh={t['id']:t for t in targets['fresh']}
    training={rows[i]['parameterHash'] for i in split['oldTrain']+split['newTrain']}
    train_audio={rows[i]['audioHash'] for i in split['oldTrain']+split['newTrain']}
    excluded={r['parameterHash'] for p in EXCLUSIONS for r in json.loads(p.read_text())['rows']}
    assert len({t['parameterHash'] for t in fresh.values()})==32
    assert all(t['parameterHash'] not in training|excluded and t['audioHash'] not in train_audio for t in fresh.values())
    files=replays=0;max_error=0.
    with Renderer() as renderer:
        assert renderer.inventory['sourceHash']==manifest['sourceHash']
        for row in report['rows']:
            target=row['target'];wave=read_wave(target);files+=1
            if target['id'] in transfer_by_id:
                previous=transfer_by_id[target['id']]
                assert np.array_equal(wave,read_wave(previous['target']))
                def identity(c):
                    return {k:c[k] for k in ('audioHash','params','seed','score')}
                assert [identity(c) for c in row['pools']['baseline']]==[identity(c) for c in previous['pools']['expanded']]
            if target['id'] in fresh:
                frozen=fresh[target['id']]
                assert parameter_hash(dict(synth='Transfxr',params=frozen['sourceParams']))==frozen['parameterHash']
                p,audio=renderer.render('Transfxr',frozen['sourceParams'],frozen['sourceSeed'])
                assert p==frozen['sourceParams'] and np.array_equal(audio,wave)
            objective=MatchObjective(wave)
            for arm,pool in row['pools'].items():
                assert len(pool)==4 and not row['failures'][arm]
                for c in pool:read_wave(c);files+=1
                selected=row['selected'][arm];assert selected==min(pool,key=lambda c:c['score'])
                p,audio=renderer.render('Transfxr',selected['params'],selected['seed'])
                assert p==selected['params'] and np.array_equal(audio,read_wave(selected))
                score=float(objective.score_batch([audio])[0]);error=abs(score-selected['score'])
                max_error=max(max_error,error);assert error<1e-7;replays+=1
    assert summarize(report['rows'])==report['summary']
    audit=dict(complete=True,reportSha256=file_hash(path),training=validation_report,verifiedAudioFiles=files,
               selectedDspReplays=replays,maxScoreError=max_error,summary=report['summary'],
               scope='All saved files hashed; all selections replayed/rescored. Descriptor summaries reused, not independently estimated.')
    _json_write(Path('tools/multisynth/evaluations/native-mixture-v1-audit.json'),audit)
    print(json.dumps(audit),flush=True)

if __name__=='__main__':run()
