import json
import re

import numpy as np
import pytest
import soundfile as sf

from multisynth.feedback import feedback_gallery
from multisynth.listening import retain_feedback


def gallery_model(records, metadata):
    page = feedback_gallery(records, metadata)
    return json.loads(re.search(r'id="feedback-data">(.*?)</script>', page).group(1))


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


def test_v1_experiment_identity_is_unchanged(tmp_path):
    raw, report, _ = fixture(tmp_path)
    feedback = json.loads(raw.read_text())
    assert feedback['experimentId'] == '92bb61ae60316fcd43196b025a4ed8d04bd3a8d91a8d70ccb83a3e0587d3cb99'
    assert 'previous' not in feedback['targets'][0]
    assert 'objectiveVersion' not in feedback['provenance']
    assert 'modelHash' not in feedback['provenance']


def previous_fixture(tmp_path, shared=False):
    raw, report, wave = fixture(tmp_path)
    data = json.loads((report/'results.json').read_text())
    previous = dict(data['results'][0]['candidates'][0], file='previous.wav')
    if not shared:
        previous.update(synth='Pew', params={'frequency': .4}, seed=19, score=.7)
    data['results'][0]['previous'] = previous
    data['metadata'].update(objectiveVersion='gesture-v1', modelHash='weights-abc')
    sf.write(report/'001'/'previous.wav', wave if shared else -wave, 44100, subtype='PCM_16')
    (report/'results.json').write_text(json.dumps(data))
    model = gallery_model(data['results'], data['metadata'])
    feedback = {'schemaVersion': 1, **model}
    for role in ('selected', 'bfxr', 'previous'):
        feedback['targets'][0][role]['rating'] = 4 if role == 'previous' or shared else None
    raw.write_text(json.dumps(feedback))
    return raw, report, wave, data


def test_previous_only_rating_retains_exact_audio_and_replay_parameters(tmp_path):
    raw, report, wave, _ = previous_fixture(tmp_path)
    out = tmp_path/'archive'
    summary = retain_feedback(raw, report, out)
    manifest = json.loads((out/'manifest.json').read_text())
    previous_id = manifest['targets'][0]['previous']
    previous = next(c for c in manifest['candidates'] if c['id'] == previous_id)
    assert previous['params'] == {'frequency': .4}
    assert previous['seed'] == 19
    assert previous['rating'] == 4
    preserved, rate = sf.read(out/previous['audio']['file'], dtype='int16')
    np.testing.assert_array_equal(preserved, -wave)
    assert rate == 44100
    assert summary['uniqueRatedCandidates'] == 1
    assert summary['meanSelectedRating'] is None
    assert summary['meanBfxrRating'] is None
    assert summary['meanPreviousRating'] == 4
    assert manifest['provenance']['objectiveVersion'] == 'gesture-v1'
    assert manifest['provenance']['modelHash'] == 'weights-abc'
    assert retain_feedback(raw, report, out) == summary


def test_previous_shared_identity_requires_consistent_ratings(tmp_path):
    raw, report, _, _ = previous_fixture(tmp_path, shared=True)
    feedback = json.loads(raw.read_text())
    assert feedback['targets'][0]['selected']['id'] == feedback['targets'][0]['previous']['id']
    assert retain_feedback(raw, report, tmp_path/'shared')['uniqueRatedCandidates'] == 1
    feedback['targets'][0]['previous']['rating'] = 2
    raw.write_text(json.dumps(feedback))
    with pytest.raises(ValueError, match='contradictory'):
        retain_feedback(raw, report, tmp_path/'conflict')


def test_previous_gallery_has_four_cards_and_no_incomparable_scores(tmp_path):
    _, report, _, data = previous_fixture(tmp_path)
    from multisynth.report import export_benchmark
    export_benchmark(report, data['results'], data['metadata'])
    page = (report/'index.html').read_text()
    assert '<strong>New model</strong>' in page
    assert '<strong>Previous model</strong>' in page
    assert 'gesture and feel' in page.lower()
    assert 'Your ratings will tell us which changes help' in page
    cards = page.split('<section class="comparison"', 1)[1].split('<script', 1)[0]
    assert cards.count('<audio ') == 4
    assert 'distance' not in cards.lower()


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
