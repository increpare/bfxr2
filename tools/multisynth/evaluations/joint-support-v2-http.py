"""Verify the exact published gallery and every local audition asset over HTTP."""
import hashlib
import json
from pathlib import Path
from urllib.request import urlopen
from neural_invert.data import file_hash,_json_write

BASE=Path('tools/multisynth');gallery=BASE/'runs/joint-support-v2-listening'
output=BASE/'evaluations/joint-support-v2-http-audit.json'
if output.exists():raise FileExistsError('Preserve HTTP audit')
audit=json.loads((BASE/'evaluations/joint-support-v2-listening-audit.json').read_text())
files={'index.html':audit['htmlSha256'],'results.json':audit['resultsSha256'],**audit['audioFiles']}
url='http://127.0.0.1:8765/tools/multisynth/runs/joint-support-v2-listening/'
rows=[]
for name,expected in files.items():
    with urlopen(url+name,timeout=15) as response:
        body=response.read();status=response.status
    digest=hashlib.sha256(body).hexdigest()
    assert status==200 and digest==expected==file_hash(gallery/name)
    rows.append(dict(path=name,status=status,sha256=digest,bytes=len(body)))
result=dict(complete=True,scriptSha256=file_hash(__file__),experimentId=audit['experimentId'],baseUrl=url,files=rows)
_json_write(output,result);print(json.dumps(dict(complete=True,files=len(rows),experimentId=audit['experimentId'])))
