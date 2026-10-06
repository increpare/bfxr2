from copy import deepcopy
import json
import numpy as np
import pytest
import torch
from neural_invert.memory import MemoryIndex, encode_features


def rows():
    return [dict(synth=s,params={'x':i},seed=i,parameterHash=str(i),audioHash='audio'+str(i)) for i,s in enumerate(['A','A','B','B'])]


def test_training_statistics_and_per_engine_nearest_controls_are_not_averaged():
    x=np.array([[0.,0.],[2.,0.],[5.,0.],[7.,0.]],np.float32);r=rows();idx=MemoryIndex.fit(x,r,{'sourceHash':'test'})
    assert idx.mean.tolist()==[3.5,0.]
    assert idx.std[1]==pytest.approx(.05)
    result=idx.retrieve(np.array([1.9,0.]),{'A':1,'B':1})
    assert [q['params'] for q in result]==[r[1]['params'],r[2]['params']]
    result[0]['params']['x']=999;assert idx.rows[1]['params']['x']==1


def test_stable_ties_and_control_group_deduplication():
    r=rows();r[1]['parameterHash']=r[0]['parameterHash'];r[1]['params']=deepcopy(r[0]['params'])
    idx=MemoryIndex.fit(np.zeros((4,2)),r,{})
    result=idx.retrieve(np.zeros(2),{'A':2,'B':2})
    assert [q['seed'] for q in result]==[0,2,3]
    with pytest.raises(ValueError):idx.retrieve(np.array([np.nan,0.]),{'A':1})
    with pytest.raises(ValueError):MemoryIndex.fit(np.zeros((3,2)),r,{})


def test_persistence_rejects_corrupt_arrays_and_preserves_original(tmp_path):
    idx=MemoryIndex.fit(np.arange(8).reshape(4,2),rows(),{'sourceHash':'test'});out=tmp_path/'index';idx.save(out)
    loaded=MemoryIndex.load(out);assert loaded.metadata==idx.metadata
    np.testing.assert_array_equal(idx.embeddings,loaded.embeddings)
    with pytest.raises(FileExistsError):idx.save(out)
    (out/'index.npz').write_bytes(b'wrong')
    with pytest.raises(ValueError):MemoryIndex.load(out)


def test_encoder_normalization_matches_prediction_peak_mask():
    model=type('Model',(),{'encoder':torch.nn.Identity()})()
    metadata={'normalization':{'mean':[1.,2.,3.],'std':[2.,4.,8.]},'ignorePeakGain':True}
    x=np.array([[3.,6.,11.]],np.float32)
    out=encode_features(model,metadata,x)
    np.testing.assert_array_equal(out,[[1.,0.,1.]])
    np.testing.assert_array_equal(x,[[3.,6.,11.]])


def test_persistence_rejects_changed_encoder_binding(tmp_path):
    idx=MemoryIndex.fit(np.arange(8).reshape(4,2),rows(),{});out=tmp_path/'index';idx.save(out)
    path=out/'index.json';data=json.loads(path.read_text())
    data['bindings'][next(iter(data['bindings']))]='different-code'
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='integrity/code'):MemoryIndex.load(out)
