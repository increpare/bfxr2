"""Audit frozen transfer targets and exact selected reproductions."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash,_json_write
from neural_invert.pitch_v5_eval import descriptor_pitch,compare_descriptor_pitch
from neural_invert.coverage_selection import select_candidate

ROOT=Path('tools/multisynth/runs/transfxr-transfer-v1')
def run():
    torch.set_num_threads(1)
    report=json.loads((ROOT/'results.json').read_text());assert report['complete']
    manifest=json.loads((ROOT/'targets.json').read_text());assert manifest['complete']
    assert file_hash(ROOT/'targets.json')==report['manifestSha256']
    script=Path('tools/multisynth/evaluations/transfxr-transfer-v1.py')
    assert file_hash(script)==manifest['scriptSha256']==report['scriptSha256']
    for path,digest in report['codeHashes'].items():assert file_hash(path)==digest
    for arm,h in report['checkpoints'].items():assert file_hash(Path('tools/multisynth/runs/native-coverage-v1/models')/arm/'best.pt')==h
    assert manifest['targets']==[r['target'] for r in report['rows']]
    def read(c):
        assert file_hash(c['waveFile'])==c['waveFileSha256']
        w,rate=sf.read(c['waveFile'],dtype='float32')
        assert rate==44100 and audio_hash(w)==c['audioHash'];return w
    files=0;replays=0;maxerror=0.;pairs=[]
    clean={};details=[]
    with Renderer() as renderer:
        assert renderer.inventory['sourceHash']==manifest['sourceHash']
        for row in report['rows']:
            # The evaluator's accepted-list slicing preserves four attempted
            # old slots only when no proposal is missing or fails rendering.
            assert not any(row['failures'].values())
            assert len(row['pools']['control'])==8 and len(row['pools']['expanded'])==4
            t=row['target'];target=read(t);files+=1
            assert descriptor_pitch(target)==row['targetPitch']
            objective=MatchObjective(target)
            for pool in row['pools'].values():
                for c in pool:read(c);files+=1
            old=row['pools']['control'];new=row['pools']['expanded']
            baseline=min(old[:4],key=lambda c:c['score'])
            assert row['selected']['old-four']==baseline
            assert row['selected']['old-eight']==min(old,key=lambda c:c['score'])
            assert row['selected']['expanded-four']==min(new,key=lambda c:c['score'])
            assert row['selected']['ensemble']==select_candidate(row['targetPitch'],baseline,old[:4]+new)
            for c in {c['audioHash']:c for c in row['selected'].values()}.values():
                p,w=renderer.render('Transfxr',c['params'],c['seed'])
                assert p==c['params'] and np.array_equal(w,read(c));replays+=1
                error=abs(float(objective.score_batch([w])[0])-c['score']);assert error<1e-8;maxerror=max(maxerror,error)
                pitch=descriptor_pitch(w)
                assert pitch==c['pitch'] and compare_descriptor_pitch(row['targetPitch'],pitch)==c['pitchComparison']
            if t.get('variant')=='clean':clean[t['baseId']]=row
            if t.get('variant') and t['variant']!='clean':
                cr=clean[t['baseId']]
                for arm,c in cr['selected'].items():
                    error=abs(float(objective.score_batch([read(c)])[0])-row['frozenClean'][arm]['score'])
                    assert error<1e-8;maxerror=max(maxerror,error)
                c=row['selected']['ensemble'];b=cr['selected']['ensemble']
                tp=row['targetPitch'];cp=cr['targetPitch']
                targetdelta=12*np.log2(tp['medianHz']/cp['medianHz']) if tp['reliable'] and cp['reliable'] else None
                candidate_delta=12*np.log2(c['pitch']['medianHz']/b['pitch']['medianHz']) if c['pitch']['reliable'] and b['pitch']['reliable'] else None
                pairs.append(dict(id=t['id'],variant=t['variant'],anchor=t['group']=='self-anchor',
                    cleanDistance=b['score'],adaptedDistance=c['score'],frozenCleanDistance=row['frozenClean']['ensemble']['score'],
                    targetPitchShiftSemitones=targetdelta,candidatePitchShiftSemitones=candidate_delta,
                    targetReliable=tp['reliable'],candidateReliable=c['pitch']['reliable'],comparison=c['pitchComparison']))
            details.append(dict(id=t['id'],group=t['group'],sourceSynth=t['sourceSynth'],
                scores={a:c['score'] for a,c in row['selected'].items()},
                targetReliable=row['targetPitch']['reliable'],ensemblePitch=row['selected']['ensemble']['pitchComparison']))
    spec=importlib.util.spec_from_file_location('transfer_eval',script);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module.summaries(report['rows'])==report['summaries']
    paired={}
    for variant in module.VARIANTS[1:]:
        rows=[r for r in pairs if r['variant']==variant]
        paired[variant]=dict(cases=len(rows),meanCleanDistance=float(np.mean([r['cleanDistance'] for r in rows])),
            meanAdaptedDistance=float(np.mean([r['adaptedDistance'] for r in rows])),
            meanFrozenCleanDistance=float(np.mean([r['frozenCleanDistance'] for r in rows])),
            adaptedBeatsFrozenClean=sum(r['adaptedDistance']<r['frozenCleanDistance']-1e-8 for r in rows),
            reliableTargets=sum(r['targetReliable'] for r in rows),reliableCandidatesAndTargets=sum(r['targetReliable'] and r['candidateReliable'] for r in rows))
    out=dict(complete=True,scriptSha256=file_hash(__file__),reportSha256=file_hash(ROOT/'results.json'),
        filesVerified=files,selectedDspReplays=replays,maxScoreError=maxerror,targetFailures=manifest['failures'],
        summaries=report['summaries'],paired=paired,details=details,perturbationDetails=pairs,
        scope='Small development test. Numeric distance not calibrated across targets; no human-quality or synth-capacity claim. Targets and all candidates hash-verified; selected outputs independently replayed/rescored. Transform/source replay is a separate check.')
    dest=Path('tools/multisynth/evaluations/transfxr-transfer-v1-audit.json')
    assert not dest.exists();_json_write(dest,out)
    print(json.dumps(dict(filesVerified=files,selectedDspReplays=replays,maxScoreError=maxerror,paired=paired)),flush=True)
if __name__=='__main__':run()
