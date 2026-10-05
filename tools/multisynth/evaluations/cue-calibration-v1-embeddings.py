"""Freeze independent encoder predictions before receiving cue judgments."""
import json,hashlib
from pathlib import Path
import soundfile as sf
import torch
from multisynth.embedding import Encoder,cosine
BASE=Path('tools/multisynth');RUN=BASE/'runs/cue-calibration-v1-listening'
def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def main():
    output=BASE/'evaluations/cue-calibration-v1-embedding-predictions.json'
    if output.exists():raise FileExistsError('Preserve predictions')
    torch.set_num_threads(2);model=Encoder(BASE/'runs/clap-weights')
    extraction=json.loads((BASE/'evaluations/embedding-v1-extraction.json').read_text())
    assert digest(BASE/'embedding.py')==extraction['binding']['encoderSha256']
    for name,sha in extraction['binding']['weights'].items():assert digest(BASE/'runs/clap-weights'/name)==sha
    report=json.loads((RUN/'results.json').read_text());rows=[]
    for record in report['results']:
        x,rate=sf.read(RUN/record['folder']/'target.wav',dtype='float32');assert rate==44100
        target=model(x);options=[]
        for c in record['candidates']:
            path=RUN/record['folder']/c['file'];assert digest(path)==c['provenance']['auditionWavSha256']
            x,rate=sf.read(path,dtype='float32');assert rate==44100
            values=model(x)
            options.append(dict(transform=c['params'],audioSha256=digest(path),scores={k:cosine(target[k],values[k]) for k in values}))
        rows.append(dict(source=record['source']['name'],options=options))
    output.write_text(json.dumps(dict(complete=True,scriptSha256=digest(__file__),
        resultsSha256=digest(RUN/'results.json'),extractionSha256=digest(BASE/'evaluations/embedding-v1-extraction.json'),
        rows=rows),indent=2)+'\n')
    print('Frozen embedding predictions for five fixed contrasts')
if __name__=='__main__':main()
