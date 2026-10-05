"""Locally encode frozen archived PCM with pinned LAION weights."""
import json
import hashlib
from pathlib import Path
import time
import importlib.metadata
import numpy as np
import soundfile as sf
import torch
from multisynth.embedding import Encoder
def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _json_write(path,value):
    Path(path).write_text(json.dumps(value,indent=2,allow_nan=False)+'\n')


def read_pcm(root,info):
    path=(root/info['file']).resolve()
    if not path.is_relative_to(root.resolve()):raise ValueError('Audio path escapes archive')
    x,rate=sf.read(path,dtype='int16',always_2d=True)
    actual=hashlib.sha256(str((rate,x.shape)).encode()+x.astype('<i2').tobytes()).hexdigest()
    if actual!=info['pcmSha256'] or rate!=44100 or x.shape[1]!=1:
        raise ValueError('Archived PCM checksum or format differs')
    return x[:,0].astype(np.float32)/32768


BASE=Path('tools/multisynth'); RUN=BASE/'runs/embedding-v1'; WEIGHTS=BASE/'runs/clap-weights'

def main():
    torch.set_num_threads(2)
    receipt=BASE/'evaluations/embedding-v1-extraction.json'
    if receipt.exists():raise FileExistsError('Preserve completed extraction receipt')
    data_path=RUN/'data.json';data=json.loads(data_path.read_text())
    protocol=json.loads((BASE/'evaluations/embedding-v1-protocol.json').read_text())
    assert file_hash(data_path)==protocol['dataSha256']
    binding=dict(dataSha256=file_hash(data_path),encoderSha256=file_hash(BASE/'embedding.py'),
        extractScriptSha256=file_hash(__file__),upstream=json.loads((WEIGHTS/'revision.json').read_text()),
        weights={p.name:file_hash(p) for p in WEIGHTS.iterdir() if p.is_file()},
        packages={p:importlib.metadata.version(p) for p in ['torch','transformers','numpy','scipy','soundfile']},
        preprocessing='Exact PCM16/32768 mono 44100, scipy resample_poly(160,147), right-zero-pad 480000; no trim/repeat/gain/text',
        style='First three stages, every transformer block output, concatenate channel mean and population std over spatial tokens')
    cache=RUN/'cache';cache.mkdir(exist_ok=True)
    binding_path=cache/'binding.json'
    if binding_path.exists():assert json.loads(binding_path.read_text())==binding
    else:_json_write(binding_path,binding)
    model=Encoder(WEIGHTS)
    started=time.time();records=[]
    for i,(pcm,a) in enumerate(data['audio'].items()):
        wave=read_pcm(Path(a['root']),a['info'])
        dest=cache/(pcm+'.npz')
        sidecar=dest.with_suffix('.json')
        if dest.exists():
            saved=json.loads(sidecar.read_text())
            assert saved==dict(pcmSha256=pcm,embeddingSha256=file_hash(dest),bindingSha256=file_hash(binding_path))
        else:
            values=model(wave)
            if i==0:
                again=model(wave)
                assert all(np.array_equal(values[k],again[k]) for k in values)
            np.savez(dest,**values)
            _json_write(sidecar,dict(pcmSha256=pcm,embeddingSha256=file_hash(dest),bindingSha256=file_hash(binding_path)))
        with np.load(dest) as f:
            assert f['task'].shape==(512,) and f['style'].shape==(5760,)
            assert all(np.isfinite(f[k]).all() for k in f.files)
        records.append(dict(pcmSha256=pcm,embeddingSha256=file_hash(dest),samples=len(wave)))
        if i%50==0:print(json.dumps(dict(done=i+1,total=len(data['audio']),seconds=round(time.time()-started,1))),flush=True)
    _json_write(receipt,dict(complete=True,binding=binding,
        blocks=model.blocks,records=records,seconds=time.time()-started))
    print('Extraction complete',len(records),flush=True)

if __name__=='__main__':main()
