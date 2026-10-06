"""Independent run accounting, exact gallery identities and served-byte audit."""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import re
from urllib.request import urlopen
import numpy as np
import soundfile as sf
from multisynth.coverage_feedback import coverage_model
from neural_invert.benchmark import audio_hash
from neural_invert.data import file_hash, _json_write

BASE=Path('tools/multisynth');ROOT=BASE/'runs/memory-inverse-v1';GALLERY=BASE/'runs/memory-inverse-v1-listening'
OUTPUT=BASE/'evaluations/memory-inverse-v1-http-audit.json'
SCRIPT=BASE/'evaluations/memory-inverse-v1.py'


def main():
    if OUTPUT.exists():raise FileExistsError('Preserve verification receipt')
    spec=importlib.util.spec_from_file_location('memory_experiment',SCRIPT)
    experiment=importlib.util.module_from_spec(spec);spec.loader.exec_module(experiment)
    protocol=json.loads((ROOT/'protocol.json').read_text());experiment.verify(protocol)
    numerical=json.loads((ROOT/'results.json').read_text());fit=json.loads((ROOT/'fit.json').read_text())
    assert numerical['protocolSha256']==file_hash(ROOT/'protocol.json') and numerical['fitSha256']==file_hash(ROOT/'fit.json')
    assert fit['indexJsonSha256']==file_hash(ROOT/'memory/index.json') and fit['indexArraySha256']==file_hash(ROOT/'memory/index.npz')
    index=json.loads((ROOT/'memory/index.json').read_text())
    assert len(index['rows'])==fit['trainRows']==43525
    assert all(r['split']=='train' for r in index['rows'])
    assert len(numerical['rows'])==8
    training_replays=0;mutations=0;proposals=0
    for i,row in enumerate(numerical['rows']):
        assert row['target']==protocol['targets'][i] and row['complete']
        assert row['arms']['regression']['quotas']==row['arms']['memory']['quotas']
        for name,arm in row['arms'].items():
            assert arm['proposals']==sum(arm['quotas'].values())
            assert arm['validProposals']==len(arm['raw']) and len(arm['raw'])+len(arm['failures'])==arm['proposals']
            assert len(arm['refined'])==len(arm['starts'])==2 and len({arm['raw'][j]['synth'] for j in arm['starts']})==2
            assert arm['selected']==min(arm['raw']+arm['refined'],key=lambda c:c['preferenceDistance'])
            for slot,c in enumerate(arm['refined']):
                refinement=c['provenance']['refinement']
                assert refinement['budget']==128 and refinement['seed']==row['target']['seed']+slot*71
                trace=refinement['trace'];assert len(trace)==129 and all(b<=a for a,b in zip(trace,trace[1:]))
                mutations+=refinement['budget']
            proposals+=arm['proposals']
            if name=='memory':
                assert dict(Counter(c['synth'] for c in arm['raw']))==arm['quotas']
                for c in arm['raw']:
                    origin=c['provenance'];stored=index['rows'][origin['memoryIndex']]
                    assert stored['params']==c['params'] and stored['seed']==c['seed'] and stored['synth']==c['synth']
                    assert stored['audioHash']==origin['trainingAudioHash']==c['audioHash']
                    assert stored['trainingRow']==origin['trainingRow'] and stored['parameterHash']==origin['trainingParameterHash']
                training_replays+=row['memoryNativeTrainingReplays']
    assert mutations==4096
    report=json.loads((GALLERY/'results.json').read_text());audit=json.loads((BASE/'evaluations/memory-inverse-v1-listening-audit.json').read_text())
    assert audit['reportSha256']==file_hash(ROOT/'results.json') and audit['resultsSha256']==file_hash(GALLERY/'results.json')
    assert audit['htmlSha256']==file_hash(GALLERY/'index.html')
    model=coverage_model(GALLERY,report['results'],report['metadata']);assert model['experimentId']==audit['experimentId']
    page=(GALLERY/'index.html').read_text()
    assert json.loads(re.search(r'id="feedback-data">(.*?)</script>',page).group(1))==model
    for name,sha in audit['uiCodeHashes'].items():assert file_hash(BASE/name)==sha
    for name in ('quick_mismatch.js','quick_listening_diagnostic.js','quick_choice.js','coverage_feedback.js','quick_audio.js'):
        assert '<script>'+(BASE/name).read_text()+'</script>' in page
    assert '<script>'+(BASE/'quick_listening.js').read_text()+'</script>' not in page
    assert 'overlap original Bfxr' in page and 'Eight familiar sounds' in page
    assert len(model['targets'])==8
    for i,t in enumerate(model['targets']):
        assert 2<=len(t['candidates'])<=3
        assert len({c['audioSha256'] for c in t['candidates']})==len(t['candidates'])
        recorded=report['results'][i];aliases=[a for c in recorded['candidates'] for a in c['provenance']['selectionAliases']]
        assert sorted(aliases)==['memory','previous','regression']
        previous=next(c for c in recorded['candidates'] if 'previous' in c['provenance']['selectionAliases'])
        wave,sr=sf.read(GALLERY/recorded['folder']/previous['file'],dtype='float32');assert sr==44100
        # Archive digests include the sample rate; benchmark audio_hash is raw
        # float32 bytes. Verify archive integrity in its own domain, then compare
        # the actual decoded arrays instead of mixing those digest conventions.
        parent=experiment.archived(protocol['targets'][i]['parent']['audio'])
        assert np.array_equal(wave,parent)
    assert all(file_hash(GALLERY/p)==h for p,h in audit['audioFiles'].items())
    assert len(audit['audioFiles'])==8+sum(len(t['candidates']) for t in model['targets'])
    for p in audit['audioFiles']:
        wave,rate=sf.read(GALLERY/p,dtype='float32')
        assert rate==44100 and wave.ndim==1 and np.isfinite(wave).all() and np.max(np.abs(wave))>0
    files={'index.html':audit['htmlSha256'],'results.json':audit['resultsSha256'],**audit['audioFiles']}
    for rel,expected in files.items():
        with urlopen('http://127.0.0.1:8765/'+str(GALLERY/rel),timeout=20) as response:
            assert response.status==200 and hashlib.sha256(response.read()).hexdigest()==expected
    _json_write(OUTPUT,dict(complete=True,experimentId=model['experimentId'],verifiedFiles=len(files),files=files,
        references=8,candidates=sum(len(t['candidates']) for t in model['targets']),renderedProposals=proposals,
        nativeTrainingReplays=training_replays,mutationAttempts=mutations,trainRows=fit['trainRows'],
        listeningAuditSha256=file_hash(BASE/'evaluations/memory-inverse-v1-listening-audit.json'),verifierSha256=file_hash(__file__),
        scope='Run accounting, exact parent PCM, native training-proposal hashes, frozen UI/identities and HTTP delivery. Perceptual quality remains unknown.'))
    print(json.dumps(dict(complete=True,servedFiles=len(files),targets=8,proposals=proposals,trainingReplays=training_replays,mutations=mutations)),flush=True)


if __name__=='__main__':main()
