"""Replay existing synthetic examples into a separately versioned feature cache."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import time

import io
import soundfile as sf

import numpy as np
import torch

from . import features, perceptual
from .library import Library
from .renderer import Renderer
from .soundboard import BoardRenderer


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def audition_hash(wave):
    """Exact PCM16 audition identity, shared with synthetic holdout validation."""
    buffer=io.BytesIO()
    sf.write(buffer,features.prepare(wave)*.5,44100,format="WAV",subtype="PCM_16")
    buffer.seek(0)
    pcm,rate=sf.read(buffer,dtype="int16",always_2d=True)
    return hashlib.sha256(str((rate,pcm.shape)).encode()+pcm.astype("<i2").tobytes()).hexdigest()


def feature_hash():
    root=Path(__file__).resolve().parents[1]
    paths=['multisynth/perceptual.py','multisynth/features.py','match/features.py','match/audio.py']
    return hashlib.sha256(b''.join((root/p).read_bytes() for p in paths)).hexdigest()


class CachedLibrary:
    def __init__(self,rows,descriptors,metadata):
        self.rows=rows;self.descriptors=np.asarray(descriptors,dtype=np.float32);self.metadata=metadata
        if not metadata.get('complete'):
            raise ValueError('Feature cache is not complete')
        if metadata.get('featureVersion')!=perceptual.VERSION:
            raise ValueError('Feature version changed; rebuild cache')
        if not rows or self.descriptors.shape!=(len(rows),perceptual.DIM):
            raise ValueError('Invalid feature cache shape')
        if not np.isfinite(self.descriptors).all():
            raise ValueError('Feature cache must be finite')

    @classmethod
    def load(cls,path,source_hash=None,feature_hash=None,base_library_hash=None):
        path=Path(path);payload=json.loads((path/'library.json').read_text());meta=payload['metadata']
        if feature_hash is None:
            feature_hash=globals()['feature_hash']()
        for key,value in [('sourceHash',source_hash),('featureHash',feature_hash),('baseLibraryHash',base_library_hash)]:
            if value is not None and meta.get(key)!=value:
                raise ValueError(key+' changed; rebuild cache')
        with np.load(path/'descriptors.npz',allow_pickle=False) as archive:
            descriptors=archive['descriptors']
        return cls(payload['rows'],descriptors,meta)


def build(library,output,backend,snapshot=None,jobs=4,limit=0):
    library,output=Path(library),Path(output)
    if output.exists():
        raise ValueError('Use a fresh output directory')
    if jobs<1 or limit<0 or backend not in ('legacy','board'):
        raise ValueError('Invalid cache arguments')
    if backend=='board' and snapshot is None:
        raise ValueError('Board cache requires a pinned snapshot')
    torch.set_num_threads(1)
    make_renderer=lambda: Renderer() if backend=='legacy' else BoardRenderer(snapshot)
    with make_renderer() as renderer:
        source_hash=renderer.inventory['sourceHash']
    original=Library.load(library,source_hash)
    count=min(limit,len(original.rows)) if limit else len(original.rows)
    rows=original.rows[:count];descriptors=np.empty((count,perceptual.DIM),np.float32)
    frozen_feature_hash=feature_hash();base_hash=digest(library/'library.json');base_descriptors=digest(library/'descriptors.npz')
    failures=[];started=time.monotonic();output.mkdir(parents=True)
    def chunk(worker):
        done=[];errors=[]
        with make_renderer() as renderer:
            if renderer.inventory['sourceHash']!=source_hash:
                raise ValueError('DSP changed during cache build')
            for i in range(worker,count,jobs):
                row=rows[i]
                try:
                    _,wave=renderer.render(row['params'],row['seed']) if backend=='board' else renderer.render(row['synth'],row['params'],row['seed'])
                    descriptor=perceptual.describe(wave)
                    if not np.allclose(descriptor[:features.DIM],original.descriptors[i],rtol=0,atol=1e-5):
                        raise ValueError('Original descriptor does not replay')
                    descriptors[i]=descriptor
                    row["auditionPcmSha256"]=audition_hash(wave)
                    done.append(i)
                except (ValueError,RuntimeError) as exc:
                    errors.append({'index':i,'synth':row['synth'],'error':str(exc)})
                if (len(done)+len(errors))%128==0:
                    print(f'{backend} worker {worker}: {len(done)} replayed, {len(errors)} rejected',flush=True)
        return done,errors
    with ThreadPoolExecutor(max_workers=jobs) as executor:
        for done,errors in executor.map(chunk,range(jobs)):
            failures.extend(errors)
    if failures:
        (output/'failures.json').write_text(json.dumps(failures,indent=2)+'\n')
        raise ValueError(f'{len(failures)} examples failed; incomplete cache not published')
    if feature_hash()!=frozen_feature_hash or digest(library/'library.json')!=base_hash or digest(library/'descriptors.npz')!=base_descriptors:
        raise ValueError('Source files changed during cache build')
    meta={'featureVersion':perceptual.VERSION,'featureHash':frozen_feature_hash,'sourceHash':source_hash,
          'baseLibraryHash':base_hash,'baseDescriptorHash':base_descriptors,'backend':backend,
          'rows':count,'originalRows':len(original.rows),'subset':count!=len(original.rows),
          'complete':True,'baseDescriptorReplayTolerance':1e-5,'failures':[],
          'seconds':time.monotonic()-started}
    CachedLibrary(rows,descriptors,meta)
    np.savez_compressed(output/'descriptors.npz',descriptors=descriptors)
    (output/'library.json').write_text(json.dumps({'metadata':meta,'rows':rows},indent=2)+'\n')
    return meta


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--library',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--backend',choices=['legacy','board'],required=True);p.add_argument('--snapshot',type=Path)
    p.add_argument('--jobs',type=int,default=4);p.add_argument('--limit',type=int,default=0)
    args=p.parse_args();print(json.dumps(build(**vars(args)),indent=2))


if __name__=='__main__':main()
