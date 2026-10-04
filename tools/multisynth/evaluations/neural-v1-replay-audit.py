import io,json,hashlib
from pathlib import Path
import numpy as np,soundfile as sf,torch
from match.renderer import BfxrRenderer
from match.audio import normalize_peak
from match.objective import MatchObjective
from multisynth.renderer import Renderer
from multisynth.big_run import history,latest_best
from neural_invert.predict import load_model
from neural_invert.data import verify_dataset_files
from neural_invert.evaluate import digest

torch.set_num_threads(1)
base=Path('tools/multisynth/runs/neural-v1')
_,metadata=load_model(base/'model/best.pt')
assert digest(base/'data/manifest.json')==metadata['dataManifestHash']
verify_dataset_files(base/'data',json.loads((base/'data/manifest.json').read_text()))
archives=[Path('tools/multisynth/listening_data')/p for p in ['2026-10-03-real-v1','2026-10-03-tagged-v2','2026-10-03-coverage-v3','2026-10-04-big-v4']]
old=history(archives)
counts={'neuralRenders':0,'originalBfxrRenders':0,'previousPcmCopies':0,'referenceCopies':0,'syntheticReferences':0,'tonalReferences':0}
score_differences=[]
def same_pcm(path,wave):
    buf=io.BytesIO();sf.write(buf,normalize_peak(wave),44100,format='WAV',subtype='PCM_16');buf.seek(0)
    expected,rate=sf.read(buf,dtype='int16');actual,actual_rate=sf.read(path,dtype='int16')
    assert rate==actual_rate==44100 and np.array_equal(expected,actual),str(path)
def same_archive(path,archive_path):
    x,rx=sf.read(path,dtype='int16');y,ry=sf.read(archive_path,dtype='int16')
    assert rx==ry and np.array_equal(x,y),str(path)
def replay(candidate,path,objective):
    if candidate.get('expert')=='original-bfxr':
        wave=bfxr.render(candidate['params'],candidate['seed']);counts['originalBfxrRenders']+=1
    else:
        _,wave=renderer.render(candidate['synth'],candidate['params'],candidate['seed']);counts['neuralRenders']+=1
    same_pcm(path,wave)
    delta=abs(float(objective.score_batch([wave])[0])-candidate['score'])
    assert delta<1e-5,(str(path),delta)
    score_differences.append(delta)
with Renderer() as renderer,BfxrRenderer(jobs=1) as bfxr:
    assert renderer.inventory['sourceHash']==metadata['sourceHash']
    tagged=Path('tools/multisynth/runs/neural-v1-listening')
    report=json.loads((tagged/'results.json').read_text());assert report['metadata']['complete']
    assert report['metadata']['modelSha256']==metadata['checkpointHash']
    for row in report['results']:
        folder=tagged/row['folder'];prev=latest_best(old[row['source']['sha256']])
        same_archive(folder/'target.wav',prev['archive']/prev['target']['referenceAudio']['file']);counts['referenceCopies']+=1
        wave,_=sf.read(folder/'target.wav',dtype='float32');objective=MatchObjective(wave)
        for c in row['candidates']:
            if c['role']=='previous':
                assert c['provenance']['candidateId']==prev['candidate']['id']
                same_archive(folder/c['file'],prev['archive']/prev['candidate']['audio']['file']);counts['previousPcmCopies']+=1
            else:replay(c,folder/c['file'],objective)
    print('Tagged comparison replay verified',flush=True)
    for mode in ['tonal-verified','synthetic']:
        report=json.loads((base/mode/'results.json').read_text())
        assert report['metadata']['modelSha256']==metadata['checkpointHash']
        for index,row in enumerate(report['results']):
            if mode=='synthetic':
                t=row['target'];folder=base/mode/t['folder']
                _,source_wave=renderer.render(t['synth'],t['params'],t['seed']);counts['syntheticReferences']+=1
                same_pcm(folder/'target.wav',source_wave);reference,_=sf.read(folder/'target.wav',dtype='float32')
            else:
                folder=base/mode/f'{index+1:03d}'
                _,source_wave=renderer.render(row['sourceSynth'],row['sourceParams'],row['sourceSeed']);counts['tonalReferences']+=1
                same_pcm(folder/'target.wav',source_wave);reference=source_wave
            objective=MatchObjective(reference)
            for role,c in row['candidates'].items():
                if c is not None:replay(c,folder/(role+'.wav'),objective)
        print(mode+' replay verified',flush=True)
out={'modelSha256':metadata['checkpointHash'],'dataManifestSha256':metadata['dataManifestHash'],'sourceHash':metadata['sourceHash'],'counts':counts,'allAuditionPcmReplayedExactly':True,'maximumScoreReplayDifference':max(score_differences),'humanQualityClaim':False,
     'verificationScriptSha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
     'evaluationCodeSha256':{name:hashlib.sha256((Path('tools/neural_invert')/(name+'.py')).read_bytes()).hexdigest() for name in ['evaluate','predict','experiment','tonal']}}
Path('tools/multisynth/evaluations/neural-v1-replay-verification.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps(out,indent=2))
