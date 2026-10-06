"""Nonparametric control head over an existing learned audio embedding."""
from copy import deepcopy
import json
from pathlib import Path
import numpy as np
import torch
from .data import file_hash, _json_write

VERSION='learned-embedding-memory-v1'
STD_FLOOR=.05


def bindings():
    return {str(Path(__file__).with_name(name)):file_hash(Path(__file__).with_name(name))
            for name in ('memory.py','features.py','predict.py','model.py')}


def encode_features(model, metadata, features, batch=256):
    mean,std=(np.asarray(metadata['normalization'][k],np.float32) for k in ('mean','std'))
    x=np.asarray(features,np.float32)
    if x.ndim!=2 or x.shape[1:]!=mean.shape or not len(x) or not np.isfinite(x).all() or batch<1:
        raise ValueError('Invalid memory encoder features')
    device=next(model.encoder.parameters(),torch.empty(0)).device
    result=[]
    with torch.no_grad():
        for start in range(0,len(x),batch):
            packed=(x[start:start+batch]-mean)/std
            if metadata.get('ignorePeakGain',True):packed[:,-2]=0
            result.append(model.encoder(torch.from_numpy(packed).to(device)).cpu().numpy())
    return np.concatenate(result)


class MemoryIndex:
    def __init__(self,embeddings,rows,mean,std,metadata):
        self.embeddings=np.array(embeddings,dtype=np.float32,copy=True)
        self.mean=np.array(mean,dtype=np.float32,copy=True);self.std=np.array(std,dtype=np.float32,copy=True)
        self.rows=deepcopy(rows);self.metadata=deepcopy(metadata)
        if (self.embeddings.ndim!=2 or len(self.rows)!=len(self.embeddings) or not len(rows)
                or self.mean.shape!=self.embeddings.shape[1:] or self.std.shape!=self.mean.shape
                or not all(np.isfinite(x).all() for x in (self.embeddings,self.mean,self.std)) or (self.std<=0).any()):
            raise ValueError('Invalid memory index')
        if any(not all(k in row for k in ('synth','params','seed','parameterHash','audioHash')) for row in rows):
            raise ValueError('Incomplete memory controls/provenance')

    @classmethod
    def fit(cls,embeddings,rows,metadata):
        x=np.asarray(embeddings,np.float32)
        if x.ndim!=2 or len(x)!=len(rows) or not len(rows) or not np.isfinite(x).all():
            raise ValueError('Need finite training embeddings and matching rows')
        return cls(x,rows,x.mean(0),np.maximum(x.std(0),STD_FLOOR),metadata)

    def retrieve(self,embedding,quotas):
        q=np.asarray(embedding,np.float32)
        if q.shape!=self.mean.shape or not np.isfinite(q).all() or any(type(n)!=int or n<0 for n in quotas.values()):
            raise ValueError('Invalid retrieval query or quotas')
        # Centering cancels in pairwise differences; std is fitted on training rows only.
        distances=np.mean(((self.embeddings-q)/self.std)**2,axis=1)
        counts={};groups=set();selected=[]
        for index in np.argsort(distances,kind='stable'):
            row=self.rows[index];engine=row['synth'];group=(engine,row['parameterHash'])
            if counts.get(engine,0)>=quotas.get(engine,0) or group in groups:continue
            groups.add(group);counts[engine]=counts.get(engine,0)+1
            selected.append({**deepcopy(row),'memoryIndex':int(index),'embeddingDistance':float(distances[index])})
        return selected

    def save(self,path):
        path=Path(path)
        if path.exists():raise FileExistsError('Preserve memory index')
        path.mkdir(parents=True)
        np.savez_compressed(path/'index.npz',embeddings=self.embeddings,mean=self.mean,std=self.std)
        _json_write(path/'index.json',dict(version=VERSION,stdFloor=STD_FLOOR,bindings=bindings(),
            arraySha256=file_hash(path/'index.npz'),rows=self.rows,metadata=self.metadata))

    @classmethod
    def load(cls,path):
        path=Path(path);d=json.loads((path/'index.json').read_text())
        if (d.get('version')!=VERSION or d.get('stdFloor')!=STD_FLOOR or d.get('bindings')!=bindings()
                or d.get('arraySha256')!=file_hash(path/'index.npz')):
            raise ValueError('Memory index integrity/code policy mismatch')
        with np.load(path/'index.npz',allow_pickle=False) as z:
            return cls(z['embeddings'],d['rows'],z['mean'],z['std'],d['metadata'])
