"""Publish all eight matched initialization tests with exact retained human choices."""
import importlib.util
import json
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from match.renderer import BfxrRenderer
from multisynth.coverage_feedback import export_coverage
from multisynth.renderer import Renderer
from multisynth.preference import PreferenceMetric
from neural_invert.benchmark import audio_hash, exact_replay
from neural_invert.coverage_mixture_eval import read_wave
from neural_invert.data import file_hash, _json_write
from neural_invert.experiment import audition_pcm

BASE=Path('tools/multisynth');ROOT=BASE/'runs/memory-inverse-v1';GALLERY=BASE/'runs/memory-inverse-v1-listening'
ASSETS=['quick_choice.js','coverage_feedback.js','coverage_feedback.py','quick_audio.js','quick_listening.html',
        'quick_listening.css','quick_mismatch.js','quick_mismatch.css','quick_listening_diagnostic.js']
SCRIPT=BASE/'evaluations/memory-inverse-v1.py'
spec=importlib.util.spec_from_file_location('memory_experiment',SCRIPT)
experiment=importlib.util.module_from_spec(spec);spec.loader.exec_module(experiment)


def main():
    if GALLERY.exists():raise FileExistsError('Preserve published session')
    p=json.loads((ROOT/'protocol.json').read_text());experiment.verify(p)
    report=json.loads((ROOT/'results.json').read_text());fit=json.loads((ROOT/'fit.json').read_text())
    assert report['complete'] and len(report['rows'])==8 and report['protocolSha256']==file_hash(ROOT/'protocol.json')
    assert report['fitSha256']==file_hash(ROOT/'fit.json') and fit['indexJsonSha256']==file_hash(ROOT/'memory/index.json')
    torch.set_num_threads(1);metric=PreferenceMetric.load(experiment.METRIC);GALLERY.mkdir();records=[];audit_rows=[]
    with Renderer() as renderer,BfxrRenderer(jobs=1) as bfxr:
        assert renderer.inventory['sourceHash']==p['sourceHash']
        for i,row in enumerate(report['rows']):
            assert row['target']==p['targets'][i] and row['protocolSha256']==report['protocolSha256'] and row['fitSha256']==report['fitSha256']
            target=row['target'];folder=GALLERY/f'{i+1:03d}';folder.mkdir()
            reference=experiment.archived(target['referenceAudio']);sf.write(folder/'target.wav',reference,44100,subtype='PCM_16')
            pref=experiment.objectives.PreferenceObjective(reference,metric)
            soft=experiment.objectives.SoftAudition(reference);legacy=experiment.objectives.AuditionObjective(reference)
            options=[];by_pcm={}
            choices=[('previous',row['anchor']),*[(arm,row['arms'][arm]['selected']) for arm in ('regression','memory')]]
            for role,c in choices:
                w=read_wave(c);exact_replay({**c,'wave':w},renderer,bfxr);pcm=audition_pcm(w)
                assert audio_hash(pcm)==c['auditionHash']
                if role=='previous':assert np.array_equal(pcm,experiment.archived(target['parent']['audio']))
                for field,obj in [('preferenceDistance',pref),('softDistance',soft),('legacyDistance',legacy)]:
                    assert abs(float(obj.score_batch([w])[0])-c[field])<1e-6
                if c['auditionHash'] in by_pcm:
                    by_pcm[c['auditionHash']]['provenance']['selectionAliases'].append(role)
                    continue
                filename=f'option-{len(options)+1}.wav';sf.write(folder/filename,pcm,44100,subtype='PCM_16')
                heard,sr=sf.read(folder/filename,dtype='float32');assert sr==44100 and np.array_equal(heard,pcm)
                provenance={**c['provenance'],'origin':c['origin'],'selectionRole':role,'selectionAliases':[role],
                    'inputPcmHash':audio_hash(reference),'auditionWavSha256':file_hash(folder/filename),
                    'auditionPcmSha256':audio_hash(pcm),'auditionTransform':'One peak normalization and PCM16; no time stretch or waveform pitch shift',
                    'softPeriodicity':c['softDistance'],'preferenceNeuralV2':c['preferenceDistance'],'auditionMatchObjective':c['legacyDistance'],
                    'protocolSha256':report['protocolSha256'],'fitSha256':report['fitSha256'],'reportSha256':file_hash(ROOT/'results.json'),
                    'originalBfxrBackend':p['bfxrBackend'] if c.get('expert')=='original-bfxr' else None,
                    'parentCandidateId':target['parent']['id'] if role=='previous' else None}
                option={**c,'role':role,'label':{'previous':'Earlier chosen clip','regression':'Predicted controls','memory':'Training-preset memory'}[role],
                    'file':filename,'provenance':provenance}
                options.append(option);by_pcm[c['auditionHash']]=option
            assert 2<=len(options)<=3
            records.append(dict(folder=folder.name,source=target['source'],candidates=options,
                note='Eight repeated external sounds. Earlier chosen clip versus two initialization methods. Judge likeness now; earlier choices are not assumed convincing.'))
            audit_rows.append(dict(source=target['source'],candidateRoles=[c['provenance']['selectionAliases'] for c in options],
                exactAnchorPcm=audio_hash(experiment.archived(target['parent']['audio'])),
                nativeReplays=len(choices),candidatePcm=[c['auditionHash'] for c in options]))
    metadata=dict(experiment='memory-inverse-v1-listening',complete=True,targetCount=8,humanReviewRequired=True,
        galleryTitle='Can better starting presets help?',galleryIntro=[
            'Eight familiar external sounds, including earlier successes and failures. Your exact earlier chosen clip remains in each comparison.',
            'Two new fits compare predicted controls with complete training presets found through the same learned audio encoder. Both use the same synth quotas, scorer and native refinement budget. Encoder weights stay frozen.',
            'Choose the closest, then how close. Optional mismatch notes and instant replay work as before. These are development comparisons; all references overlap original Bfxr’s historical training.'],
        scope=p['policy'],limitations=p['limitations'],protocolSha256=report['protocolSha256'],fitSha256=report['fitSha256'],
        reportSha256=file_hash(ROOT/'results.json'),publicationScriptSha256=file_hash(__file__),
        uiCodeHashes={name:file_hash(BASE/name) for name in ASSETS},
        selectionPolicy='All eight predeclared references. Earlier human choice, best regression arm, best memory arm under fixed preference metric. Exact PCM aliases deduplicated; never replace a converged winner to fabricate variety.')
    experiment.verify(p);model=export_coverage(GALLERY,records,metadata)
    page=(GALLERY/'index.html').read_text();old='<script>'+(BASE/'quick_listening.js').read_text()+'</script>';assert page.count(old)==1
    page=page.replace(old,'<script>'+(BASE/'quick_mismatch.js').read_text()+'</script><script>'+(BASE/'quick_listening_diagnostic.js').read_text()+'</script>')
    page=page.replace('</html>','<style>'+(BASE/'quick_mismatch.css').read_text()+'</style></html>')
    help_text='Choose the closest, then say how close it is while it’s still here.';assert page.count(help_text)==1
    page=page.replace(help_text,'Eight familiar sounds, two new fits and your earlier chosen clip. Choose the closest, then how close. The mismatch question is optional (S skips).')
    page=page.replace('<div class="quick-topline">','<details class="quick-help"><summary>What changed?</summary><p>Predicted controls versus complete synthetic training presets retrieved with the same learned audio encoder. Both get equal candidate quotas and refinement attempts. The encoder was not retrained. Your earlier chosen audio is preserved; no improvement is assumed. These repeated external development references overlap original Bfxr’s historical training.</p></details><div class="quick-topline">')
    page=page.replace('S = skip / not sure · Space','1–6 = mismatch reason when asked · S = skip / not sure · Space')
    (GALLERY/'index.html').write_text(page)
    audit=dict(complete=True,experimentId=model['experimentId'],targets=8,candidates=sum(len(t['candidates']) for t in model['targets']),
        rows=audit_rows,resultsSha256=file_hash(GALLERY/'results.json'),htmlSha256=file_hash(GALLERY/'index.html'),
        uiCodeHashes=metadata['uiCodeHashes'],protocolSha256=report['protocolSha256'],fitSha256=report['fitSha256'],
        publicationScriptSha256=file_hash(__file__),reportSha256=file_hash(ROOT/'results.json'),
        audioFiles={str(q.relative_to(GALLERY)):file_hash(q) for q in sorted(GALLERY.glob('*/*.wav'))},
        scope='Exact native final replays and earlier chosen auditions verified. No new candidate has human quality approval.')
    _json_write(BASE/'evaluations/memory-inverse-v1-listening-audit.json',audit)
    print(json.dumps(dict(complete=True,experimentId=model['experimentId'],targets=8,candidates=audit['candidates'])),flush=True)


if __name__=='__main__':main()
