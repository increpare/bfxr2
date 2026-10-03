import json

import numpy as np
import pytest
import soundfile as sf

from multisynth.feedback import feedback_gallery
from multisynth.listening import retain_feedback


def fixture(tmp_path):
    report = tmp_path/'run'
    (report/'001').mkdir(parents=True)
    wave=np.arange(-2000,2000,dtype='int16')
    for file in ['target.wav','01-Bfxr.wav']:
        sf.write(report/'001'/file,wave,44100,subtype='PCM_16')
    candidate={'synth':'Bfxr','params':{'waveType':3},'seed':7,'score':.2,'file':'01-Bfxr.wav'}
    records=[{'folder':'001','source':{'name':'click/a.wav','sha256':'abc'},'candidates':[candidate]}]
    metadata={'sourceHash':'dsp','featureVersion':'v1'}
    html=feedback_gallery(records,metadata)
    import re
    model=json.loads(re.search(r'id="feedback-data">(.*?)</script>',html).group(1))
    (report/'index.html').write_text(html)
    (report/'results.json').write_text(json.dumps({'results':records,'metadata':metadata}))
    feedback={'schemaVersion':1,'experimentId':model['experimentId'],'provenance':model['provenance'],
              'ratingScale':{'min':1,'max':5},'targets':model['targets']}
    feedback['targets'][0]['selected']['rating']=2
    feedback['targets'][0]['bfxr']['rating']=2
    feedback['targets'][0]['note']='too buzzy'
    raw=tmp_path/'ratings.json';raw.write_text(json.dumps(feedback))
    return raw,report,wave


def test_retains_raw_ratings_exact_audio_and_replay_parameters(tmp_path):
    raw,report,wave=fixture(tmp_path)
    out=tmp_path/'archive'
    summary=retain_feedback(raw,report,out)
    assert (out/'feedback.json').read_bytes()==raw.read_bytes()
    assert summary['uniqueRatedCandidates']==1
    manifest=json.loads((out/'manifest.json').read_text())
    assert len(manifest['candidates'])==1
    candidate=manifest['candidates'][0]
    assert candidate['params']=={'waveType':3}
    preserved,rate=sf.read(out/candidate['audio']['file'],dtype='int16')
    np.testing.assert_array_equal(preserved,wave)
    assert rate==44100
    assert summary['meanSelectedRating']==2
    assert retain_feedback(raw,report,out)==summary


def test_invalid_identity_or_rating_does_not_create_archive(tmp_path):
    raw,report,_=fixture(tmp_path)
    data=json.loads(raw.read_text())
    for key,value in [('rating',6),('id','wrong')]:
        changed=json.loads(json.dumps(data));changed['targets'][0]['selected'][key]=value
        raw.write_text(json.dumps(changed))
        out=tmp_path/key
        with pytest.raises(ValueError):
            retain_feedback(raw,report,out)
        assert not out.exists()


def test_conflicting_shared_ratings_and_corrupt_archive_are_rejected(tmp_path):
    raw, report, _ = fixture(tmp_path)
    original = raw.read_bytes()
    data = json.loads(original)
    data['targets'][0]['bfxr']['rating'] = 3
    raw.write_text(json.dumps(data))
    with pytest.raises(ValueError, match='contradictory'):
        retain_feedback(raw, report, tmp_path/'bad')
    raw.write_bytes(original)
    out = tmp_path/'archive'
    retain_feedback(raw, report, out)
    clip = next((out/'audio').glob('*.flac'))
    sf.write(clip, np.zeros(4000, dtype='int16'), 44100, subtype='PCM_16')
    with pytest.raises(ValueError, match='verification'):
        retain_feedback(raw, report, out)


def test_benchmark_prefers_tagged_corpus_and_allows_explicit_full_corpus(tmp_path):
    from multisynth.cli import benchmark_root
    tags = tmp_path/'tags'
    tags.mkdir()
    assert benchmark_root(tmp_path) == tags
    assert benchmark_root(tags) == tags
    assert benchmark_root(tmp_path, all_collections=True) == tmp_path
    generic = tmp_path/'other'
    generic.mkdir()
    assert benchmark_root(generic) == generic
