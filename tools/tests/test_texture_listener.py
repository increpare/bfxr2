import json
import numpy as np
import pytest
from multisynth.texture import describe, components, BAND_CENTERS, MOD_EDGES
from multisynth.texture_listener import fit, TextureListener, PRIOR


def tone(mod=10., phase=0., carrier=1000., seconds=2.):
    t=np.arange(int(seconds*44100))/44100
    return ((.6+.4*np.sin(2*np.pi*mod*t+phase))*np.sin(2*np.pi*carrier*t)).astype(np.float32)


def test_gain_polarity_short_clip_and_invalid_inputs():
    a=describe(tone(seconds=.3));b=describe(-.2*tone(seconds=.3))
    np.testing.assert_allclose(components(a,b),0,atol=2e-6)
    assert np.isfinite(np.concatenate(list(describe(np.array([0.,.2,-.3,.1])).values()))).all()
    for x in (np.zeros(20),np.array([np.nan]),np.ones((2,2))):
        with pytest.raises(ValueError):describe(x)


def test_modulation_frequency_is_preserved_not_time_normalized():
    a,b=describe(tone(10)),describe(tone(40))
    band=int(np.argmin(abs(BAND_CENTERS-1000)))
    low=a['modulation'].reshape(24,-1)[band];high=b['modulation'].reshape(24,-1)[band]
    assert MOD_EDGES[low.argmax()]<=10<MOD_EDGES[low.argmax()+1]
    assert MOD_EDGES[high.argmax()]<=40<MOD_EDGES[high.argmax()+1]


def test_cross_band_correlation_separates_shared_and_opposed_fluctuations():
    a=describe(tone(carrier=1000)+tone(carrier=5000))
    b=describe(tone(carrier=1000)+tone(carrier=5000,phase=np.pi))
    ids=np.triu_indices(24,1);i=int(np.argmin(abs(BAND_CENTERS-1000)));j=int(np.argmin(abs(BAND_CENTERS-5000)))
    pair=np.flatnonzero((ids[0]==i)&(ids[1]==j))[0]
    assert a['correlation'][pair]>.4 and b['correlation'][pair]<-.4


def test_fit_direction_train_only_scales_and_persistence(tmp_path):
    x=np.zeros((12,27));x[:,21]=-1;x[:,0]=1
    m=fit(x,np.ones(12),np.repeat(['a','b','c'],4))
    assert (x@(m.weights/m.scales)<0).all()
    assert m.scales[21]==pytest.approx(1) and m.scales[22]==pytest.approx(.01)
    assert m.weights.sum()==pytest.approx(1) and np.all(m.weights>=0)
    p=tmp_path/'model.json';m.save(p,{'test':True});loaded=TextureListener.load(p)
    np.testing.assert_array_equal(m.weights,loaded.weights)
    with pytest.raises(FileExistsError):m.save(p,{})
    d=json.loads(p.read_text());d['recipe']['steps']+=1;p.write_text(json.dumps(d))
    with pytest.raises(ValueError):TextureListener.load(p)
    with pytest.raises(ValueError):fit(x,np.zeros(12),np.arange(12))
