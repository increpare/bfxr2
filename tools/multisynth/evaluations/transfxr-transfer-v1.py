"""Frozen-checkpoint perturbation and external-source diagnostic."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash, draw_target
from neural_invert.coverage_train import load
from neural_invert.coverage_selection import select_candidate, POLICY
from neural_invert.data import file_hash, _json_write
from neural_invert.evaluate import rendered_candidates, serializable
from neural_invert.pitch_v5_eval import descriptor_pitch, compare_descriptor_pitch
from neural_invert.temporal import predict_temporal

OUT=Path('tools/multisynth/runs/transfxr-transfer-v1')
SOURCE=Path('tools/multisynth/runs/coverage-selection-v1/results.json')
VARIANTS=('clean','mp3-32k','mp3-96k','pcm8','lowpass-1800','highpass-350','transpose+5','transpose-5')
ANCHORS={'Transfxr-selection-17860','Transfxr-selection-17445','Transfxr-selection-21373'}

def write_wave(path, wave):
    wave=np.asarray(wave,dtype=np.float32);sf.write(path,wave,44100,subtype='FLOAT')
    decoded,rate=sf.read(path,dtype='float32')
    assert rate==44100 and np.array_equal(wave,decoded)
    return dict(waveFile=str(path.resolve()),waveFileSha256=file_hash(path),audioHash=audio_hash(wave),samples=len(wave))

def read(c):
    assert file_hash(c['waveFile'])==c['waveFileSha256']
    wave,rate=sf.read(c['waveFile'],dtype='float32')
    assert rate==44100 and audio_hash(wave)==c['audioHash']
    return wave

def transform(source, name, path):
    wave,rate=sf.read(source,dtype='float32');assert rate==44100
    recipe=dict(name=name,commands=[])
    def run(args):
        command=['ffmpeg','-hide_banner','-loglevel','error','-nostdin',*args]
        subprocess.run(command,check=True,capture_output=True);recipe['commands'].append(command)
    if name=='clean':return wave,recipe
    if name=='pcm8':
        recipe.update(bits=8,quantization='round to nearest 1/128, clip [-1,127/128]')
        return np.clip(np.rint(wave*128),-128,127).astype(np.float32)/128,recipe
    if name.startswith('mp3'):
        codec=path.with_suffix('.mp3')
        run(['-i',str(source),'-codec:a','libmp3lame','-b:a',name.split('-')[1],str(codec)])
        recipe['codecFileSha256']=file_hash(codec)
        run(['-i',str(codec),'-ar','44100','-ac','1','-c:a','pcm_f32le',str(path)])
    else:
        if name.startswith('transpose'):
            semitones=int(name.removeprefix('transpose'));newrate=round(44100*2**(semitones/12))
            filt=f'asetrate={newrate},aresample=44100,atempo={44100/newrate:.12f}'
            recipe.update(requestedSemitones=semitones,actualRateSemitones=float(12*np.log2(newrate/44100)),durationCompensation='ffmpeg atempo; not artifact-free')
        elif name.startswith('lowpass'):filt='lowpass=f=1800'
        else:filt='highpass=f=350'
        run(['-i',str(source),'-af',filt,'-ar','44100','-ac','1','-c:a','pcm_f32le',str(path)])
    decoded,rate=sf.read(path,dtype='float32');assert rate==44100
    recipe['decodedSamples']=len(decoded)
    # Fix codec/time-stretch tail lengths, without aligning or replacing content.
    decoded=np.pad(decoded,(0,max(0,len(wave)-len(decoded))))[:len(wave)]
    assert np.isfinite(decoded).all()
    return decoded,recipe

def summaries(rows):
    result={}
    groups={}
    for r in rows:
        label=r['target']['group']+('/'+r['target']['variant'] if r['target']['group'].startswith('self-') else '')
        groups.setdefault(label,[]).append(r)
    for group,subset in groups.items():
        result[group]={arm:dict(count=len(subset),meanDistance=float(np.mean([r['selected'][arm]['score'] for r in subset])),
            reliableTargets=sum(r['targetPitch']['reliable'] for r in subset),
            reliableCandidateAndTarget=sum(r['targetPitch']['reliable'] and r['selected'][arm]['pitch']['reliable'] for r in subset),
            pitchWithinSemitone=sum(r['targetPitch']['reliable'] and r['selected'][arm]['pitchComparison']['medianErrorSemitones'] is not None and r['selected'][arm]['pitchComparison']['medianErrorSemitones']<=1 for r in subset))
            for arm in subset[0]['selected']}
        result[group]['ensembleVersusOldEight']=dict(wins=sum(r['selected']['ensemble']['score']<r['selected']['old-eight']['score']-1e-8 for r in subset),
            ties=sum(abs(r['selected']['ensemble']['score']-r['selected']['old-eight']['score'])<=1e-8 for r in subset))
    return result

def run():
    torch.set_num_threads(1);OUT.mkdir(parents=True,exist_ok=False)
    original=json.loads(SOURCE.read_text());assert original['complete']
    bases=[r for r in original['fresh'] if r['target']['id'] in ANCHORS]
    bases += [r for r in original['fresh'] if r['target']['id'] not in ANCHORS][:5]
    assert len(bases)==8
    targets=[];failures=[]
    with Renderer() as renderer:
        for row in bases:
            t=row['target'];p,w=renderer.render('Transfxr',t['sourceParams'],t['sourceSeed'])
            assert p==t['sourceParams'] and audio_hash(w)==t['audioHash']
            gain=.5/float(np.max(np.abs(w)));w=(w*gain).astype(np.float32)
            folder=OUT/t['id'];folder.mkdir();source=folder/'source.wav';source_info=write_wave(source,w)
            for variant in VARIANTS:
                path=folder/(variant+'.wav');audio,recipe=transform(source,variant,path)
                targets.append(dict(id=t['id']+'/'+variant,baseId=t['id'],group='self-anchor' if t['id'] in ANCHORS else 'self-other',
                    variant=variant,sourceSynth='Transfxr',sourceTarget=t,sourceGain=gain,sourceAudio=source_info,transform=recipe,**write_wave(path,audio)))
        prior=json.loads(Path('tools/multisynth/runs/neural-v2/paired-fresh/results.json').read_text())
        excluded={r['parameterHash'] for r in prior['results']}
        engines=[s['name'] for s in renderer.inventory['synths'] if s.get('collectionCompatible') and s['name']!='Transfxr']
        for i,name in enumerate(engines):
            try:t=draw_target(renderer,name,'native',excluded,20261031+i*104729)
            except ValueError as error:
                failures.append(dict(sourceSynth=name,error=str(error)));continue
            w=t.pop('wave');gain=.5/float(np.max(np.abs(w)));w=(w*gain).astype(np.float32)
            folder=OUT/('external-'+name);folder.mkdir()
            targets.append(dict(id='external-'+name,group='other-synth',sourceSynth=name,sourceTarget=t,sourceGain=gain,**write_wave(folder/'target.wav',w)))
        real=Path('tools/multisynth/runs/pitch-calibration-listening-v1')
        for i,record in enumerate(json.loads((real/'results.json').read_text())['results']):
            source=real/record['folder']/'target.wav';w,rate=sf.read(source,dtype='float32');assert rate==44100
            folder=OUT/f'real-{i:02d}';folder.mkdir()
            targets.append(dict(id=f'real-{i:02d}',group='real-repeated',sourceSynth=None,source=record['source'],sourceWavSha256=file_hash(source),**write_wave(folder/'target.wav',w)))
        manifest=dict(complete=True,sourceHash=renderer.inventory['sourceHash'],targets=targets,failures=failures,externalEngines=engines,
            sourceReportSha256=file_hash(SOURCE),scriptSha256=file_hash(__file__),
            ffmpegVersion=subprocess.check_output(['ffmpeg','-version'],text=True).splitlines()[0])
        _json_write(OUT/'targets.json',manifest)
        models={a:load(Path('tools/multisynth/runs/native-coverage-v1/models')/a) for a in ('control','expanded')}
        report=dict(complete=False,manifestSha256=file_hash(OUT/'targets.json'),scriptSha256=file_hash(__file__),policy=POLICY,
            checkpoints={a:m['checkpointHash'] for a,(_,m) in models.items()},
            codeHashes={str(p):file_hash(p) for p in [Path('tools/neural_invert/temporal.py'),Path('tools/neural_invert/features.py'),Path('tools/neural_invert/coverage_selection.py'),*Path('tools/match').glob('*.py'),*Path('tools/neural_invert').glob('pitch_v5*.py')]},
            scope='Frozen inversion diagnostic; no engine-capacity or human-quality claim. Equal raw proposal budgets; no local refinement.',rows=[])
        clean={}
        for t in targets:
            wave=read(t);pitch=descriptor_pitch(wave);objective=MatchObjective(wave);pools={};errors={}
            folder=Path(t['waveFile']).parent/(Path(t['waveFile']).stem+'-candidates');folder.mkdir()
            for arm,count in [('control',8),('expanded',4)]:
                proposed=predict_temporal(*models[arm],wave,renderer,count=count)
                accepted,rejected=rendered_candidates(proposed,renderer,objective)
                errors[arm]=rejected+[dict(error='missing proposal slot') for _ in range(count-len(proposed))]
                saved=[]
                for i,c in enumerate(accepted):
                    cp=descriptor_pitch(c['wave']);info=write_wave(folder/f'{arm}-{i}.wav',c['wave'])
                    saved.append(dict(**serializable(c),origin=arm,pitch=cp,pitchComparison=compare_descriptor_pitch(pitch,cp),**info))
                assert saved;pools[arm]=saved
            old=pools['control'];new=pools['expanded'];base=min(old[:4],key=lambda c:c['score'])
            selected={'old-four':base,'old-eight':min(old,key=lambda c:c['score']),'expanded-four':min(new,key=lambda c:c['score']),
                      'ensemble':select_candidate(pitch,base,old[:4]+new)}
            row=dict(target=t,targetPitch=pitch,pools=pools,failures=errors,selected=selected)
            if t.get('variant')=='clean':clean[t['baseId']]=deepcopy(selected)
            elif t.get('variant'):
                row['frozenClean']={arm:dict(audioHash=c['audioHash'],score=float(objective.score_batch([read(c)])[0]),
                    pitchComparison=compare_descriptor_pitch(pitch,c['pitch']),newCandidateDiffers=c['audioHash']!=selected[arm]['audioHash']) for arm,c in clean[t['baseId']].items()}
            for c in {c['audioHash']:c for c in selected.values()}.values():
                p,w=renderer.render('Transfxr',c['params'],c['seed']);assert p==c['params'] and np.array_equal(w,read(c))
            report['rows'].append(row);_json_write(OUT/'results.json',report)
            print(json.dumps(dict(done=len(report['rows']),total=len(targets),id=t['id'],old=selected['old-eight']['score'],ensemble=selected['ensemble']['score'])),flush=True)
        report.update(complete=True,summaries=summaries(report['rows']));_json_write(OUT/'results.json',report)
        print(json.dumps(report['summaries']),flush=True)

if __name__=='__main__':run()
