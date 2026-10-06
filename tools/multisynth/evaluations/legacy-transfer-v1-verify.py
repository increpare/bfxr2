"""Verify arm isolation, fresh-listening targets, native run accounting and HTTP."""
import hashlib
import json
from pathlib import Path
import re
from urllib.request import urlopen
import numpy as np
import soundfile as sf
from multisynth.coverage import verify_archived_audio
from multisynth.coverage_feedback import coverage_model
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash,_json_write

BASE=Path('tools/multisynth');ROOT=BASE/'runs/legacy-transfer-v1';GALLERY=BASE/'runs/legacy-transfer-v1-listening'
OUTPUT=BASE/'evaluations/legacy-transfer-v1-http-audit.json'


def main():
    if OUTPUT.exists():raise FileExistsError('Preserve delivery receipt')
    frozen=json.loads((ROOT/'targets.json').read_text());run=json.loads((ROOT/'results.json').read_text())
    audit=json.loads((BASE/'evaluations/legacy-transfer-v1-listening-audit.json').read_text())
    report=json.loads((GALLERY/'results.json').read_text())
    assert run['targetsSha256']==file_hash(ROOT/'targets.json') and audit['reportSha256']==file_hash(ROOT/'results.json')
    assert run['scriptSha256']==frozen['scriptSha256']==file_hash(BASE/'evaluations/legacy-transfer-v1.py')
    assert all(file_hash(path)==h for path,h in frozen['codeHashes'].items())
    assert frozen['designSha256']==file_hash('docs/superpowers/plans/2026-10-06-legacy-transfer.md')
    if 'preflightCorrection' in frozen:
        correction=frozen['preflightCorrection']
        assert file_hash(ROOT/'preflight-targets.json')==correction['previousTargetsSha256']
        assert file_hash(ROOT/'preflight-plan.md')==correction['previousPlanSha256']
        assert json.loads((ROOT/'preflight-targets.json').read_text())['rows']==frozen['rows']
    seen_files=set();seen_pcm=set()
    for path,sha in frozen['priorArchives'].items():
        path=Path(path);assert file_hash(path)==sha
        for target in json.loads(path.read_text())['targets']:
            seen_files.add(target['source'].get('sha256'));verify_archived_audio(path.parent,target['referenceAudio'])
            w,sr=sf.read(path.parent/target['referenceAudio']['file'],dtype='float32');assert sr==44100
            seen_pcm.add(audio_hash(w))
    assert len(run['rows'])==len(frozen['rows'])==6
    proposals=0;mutations=0;original_evaluations=0
    for i,row in enumerate(run['rows']):
        t=frozen['rows'][i];assert row['target']==t and row['complete']
        assert t['source']['sha256'] not in seen_files and t['auditionHash'] not in seen_pcm
        assert file_hash(t['source']['path'])==t['source']['sha256']
        assert row['proposals']==row['validProposals']+len(row['failures'])
        assert row['validProposals']==len(row['raw']) and len(row['refined'])==4
        for arm,field in [('legacy','legacyDistance'),('preference','preferenceDistance')]:
            fits=[c for c in row['refined'] if c['provenance']['refinementObjective']==arm];assert len(fits)==2
            assert len({c['synth'] for c in fits})==2
            for slot,c in enumerate(fits):
                r=c['provenance']['refinement'];assert r['budget']==512 and r['seed']==t['seed']+slot*71
                assert len(r['trace'])==513 and all(b<=a for a,b in zip(r['trace'],r['trace'][1:]))
                mutations+=r['budget']
            chosen=min(row['raw']+fits,key=lambda c:c[field])
            visible=next(f for f in row['finalists'] if arm in f['aliases'])
            assert visible['candidate']['auditionHash']==chosen['auditionHash']
        visible_original=next(f for f in row['finalists'] if 'original' in f['aliases'])
        assert visible_original['candidate']['auditionHash']==row['original']['auditionHash']
        assert row['original']['provenance']['budget']==2000
        proposals+=row['proposals'];original_evaluations+=row['original']['provenance']['evaluations']
    assert mutations==12288
    assert audit['htmlSha256']==file_hash(GALLERY/'index.html') and audit['resultsSha256']==file_hash(GALLERY/'results.json')
    model=coverage_model(GALLERY,report['results'],report['metadata']);assert model['experimentId']==audit['experimentId']
    page=(GALLERY/'index.html').read_text()
    assert json.loads(re.search(r'id="feedback-data">(.*?)</script>',page).group(1))==model
    for name,h in audit['uiCodeHashes'].items():assert file_hash(BASE/name)==h
    for name in ('quick_choice.js','coverage_feedback.js','quick_audio.js','quick_mismatch.js','quick_listening_diagnostic.js'):
        assert '<script>'+(BASE/name).read_text()+'</script>' in page
    assert '<script>'+(BASE/'quick_listening.js').read_text()+'</script>' not in page
    assert 'Six fresh comparisons' in page and 'All six files occur in historical original-Bfxr training' in page
    assert len(model['targets'])==6
    for i,t in enumerate(model['targets']):
        assert 2<=len(t['candidates'])<=3 and len({c['audioSha256'] for c in t['candidates']})==len(t['candidates'])
        aliases=[a for c in report['results'][i]['candidates'] for a in c['provenance']['selectionAliases']]
        assert sorted(aliases)==['legacy','original','preference']
    assert all(file_hash(GALLERY/p)==h for p,h in audit['audioFiles'].items())
    for p in audit['audioFiles']:
        w,sr=sf.read(GALLERY/p,dtype='float32');assert sr==44100 and w.ndim==1 and np.isfinite(w).all() and max(abs(w))>0
    files={'index.html':audit['htmlSha256'],'results.json':audit['resultsSha256'],**audit['audioFiles']}
    for path,sha in files.items():
        with urlopen('http://127.0.0.1:8765/'+str(GALLERY/path),timeout=20) as response:
            assert response.status==200 and hashlib.sha256(response.read()).hexdigest()==sha
    result=dict(complete=True,experimentId=model['experimentId'],servedFiles=len(files),files=files,
        references=6,candidates=sum(len(t['candidates']) for t in model['targets']),rawProposals=proposals,
        generalArmMutationAttempts=mutations,originalBfxrEvaluations=original_evaluations,
        listeningAuditSha256=file_hash(BASE/'evaluations/legacy-transfer-v1-listening-audit.json'),verifierSha256=file_hash(__file__),
        scope='Exact prior-file/PCM exclusion, isolated matched scorer arms, unchanged UI/identities and HTTP delivery. Native final replays/scores verified at publication; human likeness unknown.')
    _json_write(OUTPUT,result);print(json.dumps({k:result[k] for k in ('complete','servedFiles','references','candidates','rawProposals','generalArmMutationAttempts','originalBfxrEvaluations')}),flush=True)


if __name__=='__main__':main()
