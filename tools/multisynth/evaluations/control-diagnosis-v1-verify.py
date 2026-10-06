"""Verify published identities, frozen UI, audio, and bytes served over local HTTP."""
import hashlib
import json
from pathlib import Path
import re
from urllib.request import urlopen
import numpy as np
import soundfile as sf
from multisynth.coverage_feedback import coverage_model
from neural_invert.data import file_hash, _json_write

BASE=Path('tools/multisynth')
GALLERY=BASE/'runs/control-diagnosis-v1-listening'
OUTPUT=BASE/'evaluations/control-diagnosis-v1-http-audit.json'


def main():
    if OUTPUT.exists():raise FileExistsError('Preserve HTTP receipt')
    report=json.loads((GALLERY/'results.json').read_text())
    audit=json.loads((BASE/'evaluations/control-diagnosis-v1-evaluation.json').read_text())
    assert audit['resultsSha256']==file_hash(GALLERY/'results.json')
    assert audit['htmlSha256']==file_hash(GALLERY/'index.html')
    model=coverage_model(GALLERY,report['results'],report['metadata'])
    assert model['experimentId']==audit['experimentId']
    page=(GALLERY/'index.html').read_text()
    assert json.loads(re.search(r'id="feedback-data">(.*?)</script>',page).group(1))==model
    for name,sha in audit['uiCodeHashes'].items():assert file_hash(BASE/name)==sha
    for name in ('quick_mismatch.js','quick_listening_diagnostic.js','quick_choice.js','coverage_feedback.js','quick_audio.js'):
        assert '<script>'+(BASE/name).read_text()+'</script>' in page
    assert '<script>'+(BASE/'quick_listening.js').read_text()+'</script>' not in page
    assert 'overlap original Bfxr' in page
    assert 'Seven focused comparisons' in page
    assert len(model['targets'])==7 and all(len(t['candidates'])==3 for t in model['targets'])
    assert len(audit['audioFiles'])==28
    assert all(file_hash(GALLERY/p)==h for p,h in audit['audioFiles'].items())
    for p in audit['audioFiles']:
        wave,rate=sf.read(GALLERY/p,dtype='float32')
        assert rate==44100 and wave.ndim==1 and np.isfinite(wave).all() and np.max(np.abs(wave))>0
    files={'index.html':audit['htmlSha256'],'results.json':audit['resultsSha256'],**audit['audioFiles']}
    for rel,expected in files.items():
        url='http://127.0.0.1:8765/'+str(GALLERY/rel)
        with urlopen(url,timeout=20) as response:
            assert response.status==200
            assert hashlib.sha256(response.read()).hexdigest()==expected
    _json_write(OUTPUT,dict(complete=True,experimentId=model['experimentId'],files=files,
        verifiedFiles=len(files),references=5,trials=7,candidates=21,uiCodeHashes=audit['uiCodeHashes'],
        listeningAuditSha256=file_hash(BASE/'evaluations/control-diagnosis-v1-evaluation.json'),
        verifierSha256=file_hash(__file__),scope='Exact native replay and scores are in the evaluation audit. HTTP checks establish delivery, not perceptual quality.'))
    print(json.dumps(dict(complete=True,servedFiles=len(files),references=5,trials=7,candidates=21)),flush=True)


if __name__=='__main__':main()
