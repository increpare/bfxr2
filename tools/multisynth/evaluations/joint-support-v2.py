"""Equal-attempt native Stackr joint-source versus locked-source refinement."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import time
import numpy as np
import soundfile as sf
import torch
from match.objective import MatchObjective
from multisynth.support_objective import SupportObjective,POLICY as SUPPORT_POLICY
from multisynth.renderer import Renderer
from multisynth.timeline import TimelineRenderer
from multisynth.joint_timeline import refine
from multisynth.coverage import verify_archived_audio,copy_archived_audio
from multisynth.coverage_feedback import export_coverage
from neural_invert.data import file_hash,_json_write
from neural_invert.benchmark import audio_hash
from neural_invert.experiment import audition_pcm

BASE=Path('tools/multisynth');ROOT=BASE/'runs/joint-support-v2';GALLERY=BASE/'runs/joint-support-v2-listening'
ARCHIVE=BASE/'listening_data/2026-10-06-learned-events-v1-quick-01'
PARENT=BASE/'runs/learned-events-v1/results.json'
PLAN=Path('docs/superpowers/plans/2026-10-06-joint-support.md')

class Objective(SupportObjective):
    def score_batch(self,waves):
        return super().score_batch([audition_pcm(w) if w is not None and len(w) else w for w in waves])

def bindings():
    files=[Path(__file__),PLAN,BASE/'evaluations/joint-support-v2-parallel.py',ARCHIVE/'manifest.json',ARCHIVE/'feedback.json',PARENT,
        Path('tools/multisynth/joint_timeline.py'),Path('tools/multisynth/support_objective.py'),Path('tools/neural_invert/evaluate.py'),
        Path('tools/neural_invert/experiment.py'),Path('tools/match/objective.py'),
        Path('tools/match/features.py'),Path('tools/match/audio.py')]
    return {str(p):file_hash(p) for p in files}

def freeze():
    if ROOT.exists():raise FileExistsError('Preserve run')
    manifest=json.loads((ARCHIVE/'manifest.json').read_text());cs={c['id']:c for c in manifest['candidates']}
    prior=json.loads(PARENT.read_text());rows=[]
    for row in prior['rows']:
        if row['entry']['arm']!='heuristic' or len(row['parts'])<2:continue
        target=next(t for t in manifest['targets'] if t['referenceAudio']['pcmSha256']==row['entry']['target']['referenceAudio']['pcmSha256'])
        previous=cs[target['choice']['preferredCandidateIds'][0]]
        assert previous['id'] in target['choice']['auditionedCandidateIds']
        initial=next(c for c in row['options'] if c['role']=='scheduled')
        rows.append(dict(target=target,previous=previous,initial=initial,trialIndex=row['entry']['trialIndex'],seed=20261107+1009*row['entry']['trialIndex']))
    assert len(rows)==4 and [r['trialIndex'] for r in rows]==[0,1,2,5]
    with TimelineRenderer() as timeline:inventory=timeline.inventory
    protocol=dict(complete=True,analysisPolicy=SUPPORT_POLICY,codeHashes=bindings(),inventory=inventory,rows=rows,budget=768,
        arms=['timeline','joint'],seedPolicy='20261107+1009*originalTrialIndex',
        scope='SupportObjective removes the appended-silence incentive in analysis; audition PCM remains complete. Four repeated external development sources with historical original-Bfxr overlap. Existing heuristic event patches; no timing or synth-control weights retrained. Equal768 mutation attempts per arm, not equal wall-clock cost.',
        selection='All four multievent heuristic references retained regardless of score. Two optimized arms plus exact latest human winner; merge exact PCM.')
    ROOT.mkdir();_json_write(ROOT/'protocol.json',protocol);_json_write(BASE/'evaluations/joint-support-v2-protocol.json',protocol)
    print(json.dumps(dict(frozen=[r['target']['source']['name'] for r in rows])),flush=True)

def checked():
    p=json.loads((ROOT/'protocol.json').read_text());assert p['complete'] and p['codeHashes']==bindings();return p

def run():
    p=checked();torch.set_num_threads(1)
    if (ROOT/'results.json').exists():raise FileExistsError('Preserve results')
    rows=[]
    with Renderer() as source,TimelineRenderer() as timeline:
        assert timeline.inventory==p['inventory']
        assert source.inventory['sourceHash']==timeline.inventory['baseSourceHash']
        for i,entry in enumerate(p['rows']):
            dest=ROOT/f'{i+1:03d}';dest.mkdir();target=entry['target'];verify_archived_audio(ARCHIVE,target['referenceAudio'])
            reference,rate=sf.read(ARCHIVE/target['referenceAudio']['file'],dtype='float32');assert rate==44100
            objective=Objective(reference);initial=entry['initial']
            pp,raw=timeline.render(initial['params'],uncached=True)
            assert pp==initial['params'] and audio_hash(raw)==initial['nativeHash']
            options=[]
            for arm in p['arms']:
                started=time.monotonic()
                result=refine(pp,timeline,source.specs,objective,p['budget'],entry['seed'],joint=arm=='joint')
                replay,actual=timeline.render(result['params'],uncached=True)
                assert replay==result['params'] and np.array_equal(actual,result['wave'])
                pcm=audition_pcm(actual);sf.write(dest/(arm+'.wav'),pcm,44100,subtype='PCM_16')
                assert abs(result['score']-SupportObjective(reference).score(pcm))<1e-6
                option={k:v for k,v in result.items() if k!='wave'}|dict(role=arm,synth='Stackr',seed=0,
                    sourceHash=timeline.inventory['sourceHash'],nativeHash=audio_hash(actual),auditionHash=audio_hash(pcm),
                    wavSha256=file_hash(dest/(arm+'.wav')),seconds=time.monotonic()-started)
                options.append(option);_json_write(dest/(arm+'.json'),option)
                print(json.dumps(dict(target=i+1,arm=arm,initial=result['trace'][0],final=result['score'],accepted=result['accepted'],seconds=round(option['seconds'],1))),flush=True)
            row=dict(entry=entry,options=options);rows.append(row);_json_write(dest/'result.json',row)
    assert checked()==p
    result=dict(complete=True,protocolSha256=file_hash(ROOT/'protocol.json'),rows=rows)
    _json_write(ROOT/'results.json',result);_json_write(BASE/'evaluations/joint-support-v2-evaluation.json',result)

def publish():
    p=checked();report=json.loads((ROOT/'results.json').read_text())
    assert report['complete'] and report['protocolSha256']==file_hash(ROOT/'protocol.json')
    if GALLERY.exists():raise FileExistsError('Preserve gallery')
    GALLERY.mkdir();records=[]
    with TimelineRenderer() as renderer:
        assert renderer.inventory==p['inventory']
        for i,row in enumerate(report['rows']):
            entry=row['entry'];dest=GALLERY/f'{i+1:03d}';dest.mkdir()
            copy_archived_audio(ARCHIVE/entry['target']['referenceAudio']['file'],dest/'target.wav')
            options=[];seen={}
            for c in row['options']:
                pp,wave=renderer.render(c['params'],uncached=True);pcm=audition_pcm(wave)
                assert pp==c['params'] and audio_hash(wave)==c['nativeHash'] and audio_hash(pcm)==c['auditionHash']
                if c['auditionHash'] in seen:
                    seen[c['auditionHash']]['provenance']['selectionAliases'].append(c['role']);continue
                filename=c['role']+'.wav';sf.write(dest/filename,pcm,44100,subtype='PCM_16')
                assert file_hash(dest/filename)==c['wavSha256']
                option={k:c[k] for k in ('synth','params','seed','sourceHash','role')}|dict(file=filename,label='Comparison option',
                    provenance=dict(origin='native-stackr-joint-controls',selectionAliases=[c['role']],protocolSha256=report['protocolSha256'],
                        nativeHash=c['nativeHash'],auditionHash=c['auditionHash'],wholeSoundScore=c['score'],
                        attempted=c['attempted'],accepted=c['accepted'],neuralWeightsRetrained=False,
                        nativeSeed=.5,seedFieldMeaning='Integer gallery identifier; actual native seed is params.seed'))
                options.append(option);seen[c['auditionHash']]=option
            previous=entry['previous'];verify_archived_audio(ARCHIVE,previous['audio'])
            copy_archived_audio(ARCHIVE/previous['audio']['file'],dest/'previous.wav')
            pcm,rate=sf.read(dest/'previous.wav',dtype='float32');assert rate==44100
            if audio_hash(pcm) in seen:seen[audio_hash(pcm)]['provenance']['selectionAliases'].append('previous')
            else:options.append({k:v for k,v in previous.items() if k not in ('id','audio','targetId','audioSha256','paramsSha256')}|
                dict(role='previous',file='previous.wav',label='Comparison option',provenance={**previous['provenance'],
                    'parentCandidateId':previous['id'],'parentExperimentId':json.loads((ARCHIVE/'manifest.json').read_text())['experimentId'],
                    'selectionAliases':['previous'],'exactEarlierPcmSha256':previous['audio']['pcmSha256']}))
            assert len(options)>1,'No useful comparison; stop publication'
            records.append(dict(folder=dest.name,source=entry['target']['source'],candidates=options,
                note='Repeated external sound. Judge the whole gesture, texture and feel.'))
    assets=['quick_choice.js','coverage_feedback.js','coverage_feedback.py','quick_audio.js','quick_listening.html',
        'quick_listening.css','quick_mismatch.js','quick_mismatch.css','quick_listening_diagnostic.js']
    metadata=dict(experiment='joint-support-v2-listening',complete=True,targetCount=len(records),humanReviewRequired=True,
        galleryTitle='Four new recreations — fitting events together',galleryIntro=[
            'Four comparisons: book flip, metal footstep, attack and coin. Your exact previous choice is included each time.',
            'Two new versions start from the same event patch. One adjusts timing, volume and pitch; the other can also change each synth’s envelope and timbre while matching the complete sound.',
            'Both use a corrected experimental matcher that gives no bonus for extra silence. These are familiar development sounds; judge audible likeness, not technical scores.'],
        scope=p['scope'],selectionPolicy=p['selection'],protocolSha256=report['protocolSha256'],reportSha256=file_hash(ROOT/'results.json'),
        uiCodeHashes={f:file_hash(BASE/f) for f in assets},diagnosticQuestion=dict(version='quick-mismatch-v1',optional=True,trigger='similar, least-bad, or none close'))
    model=export_coverage(GALLERY,records,metadata)
    page=(GALLERY/'index.html').read_text();old='<script>'+(BASE/'quick_listening.js').read_text()+'</script>';assert page.count(old)==1
    page=page.replace(old,'<script>'+(BASE/'quick_mismatch.js').read_text()+'</script><script>'+(BASE/'quick_listening_diagnostic.js').read_text()+'</script>')
    page=page.replace('</html>','<style>'+(BASE/'quick_mismatch.css').read_text()+'</style></html>');(GALLERY/'index.html').write_text(page)
    audit=dict(complete=True,experimentId=model['experimentId'],targetCount=len(records),optionCounts=[len(r['candidates']) for r in records],
        reportSha256=file_hash(ROOT/'results.json'),resultsSha256=file_hash(GALLERY/'results.json'),htmlSha256=file_hash(GALLERY/'index.html'),
        audioFiles={str(f.relative_to(GALLERY)):file_hash(f) for f in sorted(GALLERY.glob('*/*.wav'))},uiCodeHashes=metadata['uiCodeHashes'])
    _json_write(BASE/'evaluations/joint-support-v2-listening-audit.json',audit)
    print(json.dumps(dict(experimentId=model['experimentId'],counts=audit['optionCounts'])),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['freeze','run','publish']);globals()[parser.parse_args().stage]()
