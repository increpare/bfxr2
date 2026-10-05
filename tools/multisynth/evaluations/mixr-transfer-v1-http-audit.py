"""Verify served experiment bytes, including every listening audio file."""
from pathlib import Path
import hashlib
import json
from urllib.parse import quote
from urllib.request import urlopen
from neural_invert.data import file_hash, _json_write

BASE = Path('tools/multisynth')
ROOT = BASE/'runs/mixr-transfer-v1-listening'
URL = 'http://127.0.0.1:8765/tools/multisynth/runs/mixr-transfer-v1-listening/'


def main():
    receipt = json.loads((BASE/'evaluations/mixr-transfer-v1-listening-audit.json').read_text())
    assert receipt['complete'] and receipt['htmlSha256']==file_hash(ROOT/'index.html')
    assert receipt['resultsSha256']==file_hash(ROOT/'results.json')
    files = [ROOT/'index.html',ROOT/'results.json',*sorted(ROOT.glob('*/*.wav'))]
    checks = []
    for path in files:
        relative = str(path.relative_to(ROOT))
        with urlopen(URL+quote(relative),timeout=20) as response:
            assert response.status==200
            body = response.read()
        checksum = hashlib.sha256(body).hexdigest()
        assert checksum==file_hash(path), relative
        checks.append(dict(file=relative,sha256=checksum,bytes=len(body)))
    assert len(checks)==2+len(receipt['audioFiles'])
    assert {c['file'] for c in checks[2:]}==set(receipt['audioFiles'])
    output = dict(complete=True,experimentId=receipt['experimentId'],checks=checks,baseUrl=URL,
        listeningAuditSha256=file_hash(BASE/'evaluations/mixr-transfer-v1-listening-audit.json'),scriptSha256=file_hash(__file__))
    _json_write(BASE/'evaluations/mixr-transfer-v1-http-audit.json',output)
    print(json.dumps(dict(complete=True,files=len(checks),experimentId=receipt['experimentId'])))


if __name__=='__main__':
    main()
