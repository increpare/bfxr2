"""Equal-budget legacy/continuous-periodicity refinement of identical starts."""
import json,time
from pathlib import Path
import numpy as np
import torch
from match.objective import MatchObjective
from multisynth.soft_periodicity import SoftPeriodicityObjective
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash,exact_replay
from neural_invert.coverage_mixture_eval import read_wave,write_wave
from neural_invert.data import file_hash,_json_write
from neural_invert.evaluate import refine_candidate,serializable
from neural_invert.experiment import audition_pcm

BASE=Path('tools/multisynth');OUT=BASE/'runs/soft-periodicity-v1'
SOURCE=BASE/'runs/tagged-coverage-v1/results.json'

class LegacyAudition(MatchObjective):
    def score_batch(self,waves):return super().score_batch([audition_pcm(w) if w is not None and len(w) else w for w in waves])
class SoftAudition(SoftPeriodicityObjective):
    def score_batch(self,waves):return super().score_batch([audition_pcm(w) if w is not None and len(w) else w for w in waves])

def key(c):return json.dumps([c['synth'],c['params'],c['seed']],sort_keys=True)

def main():
    if OUT.exists():raise FileExistsError('Preserve completed/partial experiment')
    torch.set_num_threads(1)
    evaluation=BASE/'evaluations/soft-periodicity-v1-evaluation.json'
    e=json.loads(evaluation.read_text());assert e['gate']['historicalNonRegression']
    source=json.loads(SOURCE.read_text());OUT.mkdir()
    protocol=dict(scriptSha256=file_hash(__file__),objectiveSha256=file_hash(BASE/'soft_periodicity.py'),
        sourceReportSha256=file_hash(SOURCE),evaluationSha256=file_hash(evaluation),
        budgetPerStartPerArm=256,starts=2,seed=20261123,
        startPolicy='Best existing training-retrieval/refined controls by each scorer; if identical, best different-engine soft-scored controls. Both arms receive same starts.',
        scope='Five repeated tagged development references. Same proposal RNG seed and attempt budget per start, but accepted paths diverge. No new inverse network training.')
    _json_write(OUT/'protocol.json',protocol);_json_write(BASE/'evaluations/soft-periodicity-v1-search-protocol.json',protocol)
    rows=[]
    with Renderer() as renderer:
        protocol_source=renderer.inventory['sourceHash']
        for i,row in enumerate(source['rows']):
            begin=time.time();dest=OUT/f'{i+1:03d}';dest.mkdir()
            ref=read_wave(row['reference']);objectives={'legacy':LegacyAudition(ref),'soft':SoftAudition(ref)}
            pool=[]
            for c in row['pools']['retrieved']+row['pools']['refined']:
                assert c['sourceHash']==protocol_source
                wave=read_wave(c);scores={k:float(obj.score_batch([wave])[0]) for k,obj in objectives.items()}
                pool.append({**c,'wave':wave,'newScores':scores})
            starts=[min(pool,key=lambda c:c['newScores']['legacy'])]
            soft_best=min(pool,key=lambda c:c['newScores']['soft'])
            if key(soft_best)==key(starts[0]):soft_best=min((c for c in pool if c['synth']!=starts[0]['synth']),key=lambda c:c['newScores']['soft'])
            starts.append(soft_best)
            for c in starts:exact_replay(c,renderer,None)
            arms={}
            for arm,obj in objectives.items():
                final=[]
                for j,c in enumerate(starts):
                    initial={**c,'score':c['newScores'][arm]}
                    result=refine_candidate(initial,renderer,obj,256,20261123+i*1000+j*71)
                    assert result['score']<=initial['score']+1e-7
                    exact_replay(result,renderer,None)
                    result['provenance']={**result['provenance'],'searchArm':arm,'initialControlKey':key(c),
                        'initialSourceWavSha256':c['waveFileSha256'],'objectiveSha256':protocol['objectiveSha256'],
                        'protocolSha256':file_hash(OUT/'protocol.json')}
                    result.update(write_wave(dest/f'{arm}-{j}.wav',result['wave']))
                    result['newScores']={k:float(o.score_batch([result['wave']])[0]) for k,o in objectives.items()}
                    result['auditionHash']=audio_hash(audition_pcm(result['wave']))
                    final.append(serializable(result))
                    print(json.dumps(dict(target=i+1,arm=arm,start=j+1,synth=result['synth'],initial=initial['score'],final=result['score'])),flush=True)
                arms[arm]=dict(finalists=final,selected=min(final,key=lambda c:c['newScores'][arm]))
            result=dict(target=row['target'],reference=row['reference'],starts=[serializable(c) for c in starts],arms=arms,seconds=time.time()-begin,folder=dest.name)
            _json_write(dest/'result.json',result);rows.append(result)
        assert protocol_source==renderer.inventory['sourceHash']
    result=dict(complete=True,protocol=protocol,sourceHash=protocol_source,rows=rows,mutationAttempts=5*2*2*256)
    _json_write(OUT/'results.json',result);_json_write(BASE/'evaluations/soft-periodicity-v1-search.json',result)
    print('Completed 5120 mutation attempts',flush=True)
if __name__=='__main__':main()
