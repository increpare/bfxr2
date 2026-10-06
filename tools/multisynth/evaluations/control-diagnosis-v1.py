"""Seven predeclared, native one-control-family listening interventions."""
import argparse
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.bfxr_io import render_worker_cmd
from match.renderer import BfxrRenderer
from match.objective import MatchObjective
from multisynth.control_diagnosis import control_variants
from multisynth.coverage import verify_archived_audio
from multisynth.coverage_feedback import export_coverage
from multisynth.features import describe
from multisynth.preference import PreferenceMetric
from multisynth.renderer import Renderer
from multisynth.soft_periodicity import SoftPeriodicityObjective
from neural_invert.benchmark import audio_hash,pitch_diagnostic
from neural_invert.data import file_hash,_json_write
from neural_invert.experiment import audition_pcm

BASE=Path('tools/multisynth');ROOT=BASE/'runs/control-diagnosis-v1';GALLERY=BASE/'runs/control-diagnosis-v1-listening'
ARCHIVE=BASE/'listening_data/2026-10-06-fresh-gesture-v1-quick-01'
REVIEW=BASE/'evaluations/fresh-gesture-v1-quick-01-human-review.json'
PLAN=Path('docs/superpowers/plans/2026-10-06-control-diagnosis.md')
METRIC=BASE/'models/preference-neural-v2.json'
CASE='hit/OBJLug_Case_Closed06_InMotionAudio_InstrumentCase.wav'
TRIALS=[('footstep/footstep08.ogg','pitch'),('footstep/footstep08.ogg','tone'),
        (CASE,'voltage'),(CASE,'spark'),('footstep/footstep_carpet_000.ogg','wetness'),
        ('laser/Fox - Laser Gun.wav','bitCrush'),('bell/impactBell_heavy_002.ogg','pitch')]
ASSETS=['quick_choice.js','coverage_feedback.js','coverage_feedback.py','quick_audio.js','quick_listening.html',
        'quick_listening.css','quick_mismatch.js','quick_mismatch.css','quick_listening_diagnostic.js']
CODE=[Path(__file__),BASE/'control_diagnosis.py',BASE/'features.py',BASE/'gesture.py',BASE/'preference.py',
      BASE/'soft_periodicity.py',BASE/'renderer.py',Path('tools/neural_invert/experiment.py'),
      Path('tools/neural_invert/benchmark.py'),Path('tools/match/renderer.py'),Path('tools/match/bfxr_io.py'),
      *[Path('tools/match')/name for name in ('structure.py','objective.py','features.py','audio.py')]]


def archived(info):
    verify_archived_audio(ARCHIVE,info)
    w,r=sf.read(ARCHIVE/info['file'],dtype='float32');assert r==44100
    return w


def freeze():
    if ROOT.exists():raise FileExistsError('Preserve frozen protocol')
    m=json.loads((ARCHIVE/'manifest.json').read_text());cs={c['id']:c for c in m['candidates']}
    targets={t['source']['name']:t for t in m['targets']};trials=[]
    for name,axis in TRIALS:
        t=targets[name];choice=t['choice'];assert choice['kind']=='best'
        cid=choice['preferredCandidateIds'][0];assert cid in choice['auditionedCandidateIds']
        c=cs[cid];archived(t['referenceAudio']);archived(c['audio'])
        variants=control_variants(c['synth'],c['params'],axis)
        trials.append(dict(source=t['source'],referenceAudio=t['referenceAudio'],parent=c,axis=axis,
            variants=variants,parentChoice=choice,parentNote=t['note'],parentTargetId=t['id']))
    with Renderer() as renderer:
        assert all(t['parent']['sourceHash']==renderer.inventory['sourceHash'] for t in trials)
        source_hash=renderer.inventory['sourceHash']
    backend=render_worker_cmd();ROOT.mkdir()
    protocol=dict(complete=True,trials=trials,sourceHash=source_hash,
        archiveManifestSha256=file_hash(ARCHIVE/'manifest.json'),feedbackSha256=file_hash(ARCHIVE/'feedback.json'),
        reviewSha256=file_hash(REVIEW),planSha256=file_hash(PLAN),metricSha256=file_hash(METRIC),
        codeHashes={str(p):file_hash(p) for p in CODE},uiCodeHashes={n:file_hash(BASE/n) for n in ASSETS},
        bfxrBackend=dict(command=backend,sha256=file_hash(backend[0])),
        policy='Seven fixed trials, exact prior chosen clip and two native control variants each. No score selection or dropped cases. Repeated external development references, all historically present in original-Bfxr real-training list. No new inverse or metric trained.',
        limitations=['Voltage, spark, wetness and bitCrush are coupled perceptual controls, not pure pitch/timbre axes.',
                    'Native pitch edits preserve other control values but their DSP can couple pitch to decay and texture.',
                    'Peak normalization is fixed; perceived loudness may still change. No invented human labels for perturbations.'])
    _json_write(ROOT/'protocol.json',protocol)
    _json_write(BASE/'evaluations/control-diagnosis-v1-protocol.json',protocol|{'protocolSha256':file_hash(ROOT/'protocol.json')})
    print(json.dumps(dict(frozen=True,trials=len(trials))),flush=True)


def verify(p):
    assert p['archiveManifestSha256']==file_hash(ARCHIVE/'manifest.json') and p['feedbackSha256']==file_hash(ARCHIVE/'feedback.json')
    assert p['reviewSha256']==file_hash(REVIEW) and p['planSha256']==file_hash(PLAN) and p['metricSha256']==file_hash(METRIC)
    assert all(file_hash(path)==h for path,h in p['codeHashes'].items())
    assert all(file_hash(BASE/n)==h for n,h in p['uiCodeHashes'].items())
    assert p['bfxrBackend']['command']==render_worker_cmd() and p['bfxrBackend']['sha256']==file_hash(render_worker_cmd()[0])


def run():
    p=json.loads((ROOT/'protocol.json').read_text());verify(p)
    if GALLERY.exists():raise FileExistsError('Preserve published listening session')
    GALLERY.mkdir();torch.set_num_threads(1);metric=PreferenceMetric.load(METRIC)
    records=[];audit_rows=[]
    with Renderer() as renderer,BfxrRenderer(jobs=1) as bfxr:
        assert renderer.inventory['sourceHash']==p['sourceHash']
        for i,t in enumerate(p['trials']):
            parent=t['parent'];is_original=parent['provenance']['origin']=='original-bfxr'
            folder=f'{i+1:03d}';dest=GALLERY/folder;dest.mkdir();raw_dest=ROOT/folder;raw_dest.mkdir()
            reference=archived(t['referenceAudio']);anchor=archived(parent['audio'])
            sf.write(dest/'target.wav',reference,44100,subtype='PCM_16')
            descriptor=describe(reference);soft=SoftPeriodicityObjective(reference);legacy=MatchObjective(reference)
            def render(params):
                if is_original:return params,bfxr.render(params,seed=parent['seed'])
                return renderer.render(parent['synth'],params,parent['seed'])
            candidates=[];hashes=set();details=[]
            assert t['variants']==control_variants(parent['synth'],parent['params'],t['axis'])
            for j,params in enumerate([parent['params'],*t['variants']]):
                if j:
                    changed={k for k in params if params[k]!=parent['params'][k]}
                    assert changed=={t['axis']} and set(params)==set(parent['params'])
                canonical,w=render(params);canonical2,replay=render(params)
                assert canonical==canonical2==params and np.array_equal(w,replay)
                assert w.ndim==1 and np.isfinite(w).all() and np.max(np.abs(w))>1e-7
                heard=audition_pcm(w)
                if j==0:assert np.array_equal(heard,anchor),'Anchor differs from exact archived audition'
                assert audio_hash(heard) not in hashes,'Unresponsive axis: cannot fabricate distinct options'
                hashes.add(audio_hash(heard))
                filename=f'option-{j+1}.wav';sf.write(dest/filename,heard,44100,subtype='PCM_16')
                saved,rate=sf.read(dest/filename,dtype='float32');assert rate==44100 and np.array_equal(saved,heard)
                sf.write(raw_dest/f'option-{j+1}-float.wav',w,44100,subtype='FLOAT')
                scores=dict(softPeriodicity=float(soft.score(heard)),preferenceNeuralV2=float(metric.distances(descriptor,describe(heard))[0]),
                            auditionMatchObjective=float(legacy.score(heard)))
                provenance=dict(method='retained-human-choice' if j==0 else 'native-control-intervention',
                    origin=parent['provenance']['origin'] if j==0 else 'controlled-native-variant',
                    parentCandidateId=parent['id'],parentPcmSha256=parent['audio']['pcmSha256'],
                    parentArchiveManifestSha256=p['archiveManifestSha256'],parentProvenance=parent['provenance'],
                    interventionAxis=t['axis'],interventionIndex=j,changedTopLevelControls=[] if j==0 else [t['axis']],
                    before=parent['params'][t['axis']],after=params[t['axis']],seedPolicy='Exact parent render seed',
                    nativeFloatSha256=file_hash(raw_dest/f'option-{j+1}-float.wav'),nativeFloatPcmSha256=audio_hash(w),
                    auditionWavSha256=file_hash(dest/filename),auditionPcmSha256=audio_hash(heard),
                    auditionTransform='Same peak normalization and PCM16 as parent; no waveform pitch shift or time stretch',
                    inputPcmHash=audio_hash(reference),protocolSha256=file_hash(ROOT/'protocol.json'),
                    originalBfxrBackend=p['bfxrBackend'] if is_original else None,**scores)
                candidates.append(dict(synth=parent['synth'],params=deepcopy(params),seed=parent['seed'],sourceHash=p['sourceHash'],
                    expert='original-bfxr' if is_original else 'actual-multisynth',file=filename,
                    role='previous' if j==0 else f'variant-{j}',label='Earlier chosen clip' if j==0 else f'Controlled variant {j}',provenance=provenance))
                details.append(dict(variant=j,scores=scores,params=params,pitch=pitch_diagnostic(heard),
                                    file=filename,wavSha256=file_hash(dest/filename),exactNativeReplay=True))
            records.append(dict(folder=folder,source=t['source'],candidates=candidates,
                note='One exact earlier choice and two controlled native variants. References can repeat for different adjustments. Judge the reference likeness; ties and none-close are useful.'))
            audit_rows.append(dict(source=t['source'],folder=folder,axis=t['axis'],parentChoice=t['parentChoice'],parentNote=t['parentNote'],
                parentCandidateId=parent['id'],referencePitch=pitch_diagnostic(reference),candidates=details))
            print(json.dumps(dict(renderedTrial=i+1,synth=parent['synth'],axis=t['axis'],exactCandidates=3)),flush=True)
    metadata=dict(experiment='control-diagnosis-v1-listening',complete=True,targetCount=7,
        galleryTitle='Seven focused comparisons — which changes help?',galleryIntro=[
            'Each trial preserves your earlier chosen clip and offers two controlled native-synth variants. Some references repeat to test different adjustments.',
            'This investigates your pitch and texture notes, and also includes the bell you rated very close. Existing models are unchanged. These are repeated development cases, not an unseen test.',
            'Choose the closest, then how close. Optional mismatch questions and instant replay work as before. The references overlap original Bfxr’s historical training list.'],
        scope=p['policy'],limitations=p['limitations'],protocolSha256=file_hash(ROOT/'protocol.json'),
        archiveManifestSha256=p['archiveManifestSha256'],reviewSha256=p['reviewSha256'],
        uiCodeHashes=p['uiCodeHashes'],scriptSha256=file_hash(__file__),humanReviewRequired=True,
        selectionPolicy='All fixed variants; no numerical ranking selection or retrospective trial filtering.')
    verify(p);model=export_coverage(GALLERY,records,metadata)
    page=(GALLERY/'index.html').read_text();old='<script>'+(BASE/'quick_listening.js').read_text()+'</script>'
    assert page.count(old)==1
    page=page.replace(old,'<script>'+(BASE/'quick_mismatch.js').read_text()+'</script><script>'+(BASE/'quick_listening_diagnostic.js').read_text()+'</script>')
    page=page.replace('</html>','<style>'+(BASE/'quick_mismatch.css').read_text()+'</style></html>')
    old_help='Choose the closest, then say how close it is while it’s still here.'
    assert page.count(old_help)==1
    page=page.replace(old_help,'Seven focused comparisons. Some references repeat for different adjustments. Choose the closest, then how close. The mismatch question is optional (S skips).')
    page=page.replace('<div class="quick-topline">','<details class="quick-help"><summary>About this follow-up</summary><p>Each comparison contains your exact earlier choice and two native control variants. Includes a previously very-close bell as well as pitch/texture failures. Existing models are unchanged; these repeated development references overlap original Bfxr’s historical training. Options are not selected by metric score.</p></details><div class="quick-topline">')
    page=page.replace('S = skip / not sure · Space','1–6 = mismatch reason when asked · S = skip / not sure · Space')
    (GALLERY/'index.html').write_text(page)
    report=dict(complete=True,experimentId=model['experimentId'],protocolSha256=file_hash(ROOT/'protocol.json'),
        archiveManifestSha256=p['archiveManifestSha256'],sourceHash=p['sourceHash'],bfxrBackend=p['bfxrBackend'],rows=audit_rows,
        resultsSha256=file_hash(GALLERY/'results.json'),htmlSha256=file_hash(GALLERY/'index.html'),uiCodeHashes=p['uiCodeHashes'],
        audioFiles={str(q.relative_to(GALLERY)):file_hash(q) for q in sorted(GALLERY.glob('*/*.wav'))},
        nativeExactReplays=21,scope='Controlled native interventions on five external development references in seven trials. Human likeness is unknown for new variants; scores did not select them.')
    assert len(report['audioFiles'])==28 and len(model['targets'])==7
    _json_write(ROOT/'evaluation.json',report);_json_write(BASE/'evaluations/control-diagnosis-v1-evaluation.json',report)
    print(json.dumps(dict(complete=True,experimentId=model['experimentId'],trials=7,options=21)),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('stage',choices=['freeze','run']);args=parser.parse_args()
    {'freeze':freeze,'run':run}[args.stage]()
