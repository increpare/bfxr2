import copy
import json
import re

import numpy as np
import pytest
import soundfile as sf

from multisynth.coverage_feedback import export_coverage
from multisynth.listening import retain_feedback


def fixture(tmp_path):
    report = tmp_path/'run'
    (report/'001').mkdir(parents=True)
    wave = np.arange(-2000, 2000, dtype='int16')
    for file in ('target.wav', 'auto.wav', 'previous.wav', 'guided.wav'):
        sf.write(report/'001'/file, wave, 44100, subtype='PCM_16')
    c = {'label':'Automatic match', 'role':'automatic', 'synth':'Soundboard',
         'params':{'freq':.2}, 'seed':7, 'sourceHash':'dsp-v1', 'file':'auto.wav',
         'provenance':{'renderer':'original'}, 'score':.23456}
    records = [{'folder':'001','source':{'name':'coin.wav','path':'original/coin.wav','sha256':'source'},
                'candidates':[c,dict(c,label='Previous best',role='previous',file='previous.wav'),
                              dict(c,label='Category-guided',role='guided',sourceHash='dsp-v2',file='guided.wav')]}]
    export_coverage(report, records, {'purpose':'diagnostic','libraryManifestHash':'library'})
    page = (report/'index.html').read_text()
    model = json.loads(re.search(r'id="feedback-data">(.*?)</script>', page).group(1))
    feedback = {'schemaVersion':2, **copy.deepcopy(model)}
    for c in feedback['targets'][0]['candidates']:
        c.update(likeness=2, usefulness=5)
    feedback['targets'][0]['note']='fun, unlike the coin'
    raw = tmp_path/'ratings.json'
    raw.write_text(json.dumps(feedback))
    return raw, report, wave, records, model


def test_gallery_audio_and_source_provenance_identity(tmp_path):
    raw, report, wave, records, model = fixture(tmp_path)
    a,b,c = model['targets'][0]['candidates']
    assert a['id'] == b['id']
    assert a['id'] != c['id']
    assert a['audioSha256'] and a['sourceHash'] == 'dsp-v1'
    page = (report/'index.html').read_text().split('<script',1)[0]
    assert page.count('<audio ') == 4
    assert '0.23456' not in page
    assert 'Likeness to reference' in page and 'Useful/fun game sound' in page
    assert 'category-guided' in page.lower() and 'unseen' in page
    sf.write(report/'001'/'auto.wav', -wave, 44100, subtype='PCM_16')
    with pytest.raises(ValueError,match='experiment|provenance'):
        retain_feedback(raw,report,tmp_path/'changed')
    assert not (tmp_path/'changed').exists()


def test_gallery_can_explain_a_new_experiment_without_raw_html(tmp_path):
    _,report,_,records,_=fixture(tmp_path)
    export_coverage(report,records,{'galleryTitle':'Large run <v4>',
                                  'galleryIntro':['Rate the gesture & feel.','<script>not code</script>']})
    page=(report/'index.html').read_text()
    assert '<h1>Large run &lt;v4&gt;</h1>' in page
    assert '<p>Rate the gesture &amp; feel.</p>' in page
    assert '<p>&lt;script&gt;not code&lt;/script&gt;</p>' in page
    assert 'A small development diagnostic' not in page


def test_html_only_refresh_preserves_frozen_results_audio_and_experiment(tmp_path):
    _, report, _, records, model = fixture(tmp_path)
    results_path = report/'results.json'
    results = json.loads(results_path.read_text())
    # Formatting is part of the frozen artifact too: refreshing UI must not rewrite it.
    results_path.write_text(json.dumps(results, separators=(',', ':')))
    before = {p.relative_to(report):p.read_bytes() for p in report.rglob('*')
              if p.is_file() and p.suffix in ('.json', '.wav')}
    refreshed = export_coverage(report, records, results['metadata'], html_only=True)
    assert refreshed == model
    assert before == {p.relative_to(report):p.read_bytes() for p in report.rglob('*')
                      if p.is_file() and p.suffix in ('.json', '.wav')}


def test_archives_exact_pcm_raw_feedback_full_parameters_and_idempotency(tmp_path):
    raw,report,wave,_,model = fixture(tmp_path)
    out=tmp_path/'archive'
    summary=retain_feedback(raw,report,out)
    assert (out/'feedback.json').read_bytes() == raw.read_bytes()
    manifest=json.loads((out/'manifest.json').read_text())
    assert manifest['schemaVersion'] == 2
    assert summary['uniqueRatedCandidates'] == 2
    assert len(manifest['candidates']) == 2
    for candidate in manifest['candidates']:
        assert candidate['params'] == {'freq':.2}
        assert candidate['seed'] == 7 and candidate['sourceHash']
        assert candidate['likeness'] == 2 and candidate['usefulness'] == 5
        pcm,rate=sf.read(out/candidate['audio']['file'],dtype='int16')
        np.testing.assert_array_equal(pcm,wave)
        assert rate == 44100
    assert manifest['targets'][0]['source']['path'] == 'original/coin.wav'
    assert retain_feedback(raw,report,out) == summary
    clip=next((out/'audio').glob('*.flac'))
    sf.write(clip,-wave,44100,subtype='PCM_16')
    with pytest.raises(ValueError,match='verification'):
        retain_feedback(raw,report,out)


@pytest.mark.parametrize('field,value',[('likeness',True),('usefulness',6),('id','wrong'),('sourceHash','wrong'),('audioSha256','wrong')])
def test_invalid_candidate_rejected_before_output(tmp_path,field,value):
    raw,report,_,_,_=fixture(tmp_path)
    data=json.loads(raw.read_text())
    data['targets'][0]['candidates'][0][field]=value
    raw.write_text(json.dumps(data))
    out=tmp_path/'does-not-exist'/'archive'
    with pytest.raises(ValueError):
        retain_feedback(raw,report,out)
    assert not out.parent.exists()


def test_alias_ratings_must_agree_and_note_only_preserves_null(tmp_path):
    raw,report,_,_,_=fixture(tmp_path)
    data=json.loads(raw.read_text())
    data['targets'][0]['candidates'][1]['usefulness']=3
    raw.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='contradictory'):
        retain_feedback(raw,report,tmp_path/'bad')
    for c in data['targets'][0]['candidates']:
        c.update(likeness=None,usefulness=None)
    raw.write_text(json.dumps(data))
    summary=retain_feedback(raw,report,tmp_path/'notes')
    assert summary['uniqueRatedCandidates']==0


@pytest.mark.parametrize('escape',['../outside.wav','/tmp/outside.wav'])
def test_path_escape_rejected_before_output(tmp_path,escape):
    raw,report,_,_,_=fixture(tmp_path)
    data=json.loads((report/'results.json').read_text())
    data['results'][0]['candidates'][0]['file']=escape
    (report/'results.json').write_text(json.dumps(data))
    with pytest.raises(ValueError,match='path|file'):
        retain_feedback(raw,report,tmp_path/'bad')
    assert not (tmp_path/'bad').exists()


def test_archive_rejects_raw_rewrite_and_missing_candidates(tmp_path):
    raw,report,_,_,_=fixture(tmp_path)
    data=json.loads(raw.read_text())
    out=tmp_path/'archive'
    retain_feedback(raw,report,out)
    raw.write_text(json.dumps(data,indent=4))
    with pytest.raises(ValueError,match='different data'):
        retain_feedback(raw,report,out)
    data['targets'][0]['candidates'].pop()
    raw.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='identities'):
        retain_feedback(raw,report,tmp_path/'missing')


def test_rejects_symlink_escape_and_non_pcm16_before_output(tmp_path):
    raw,report,wave,records,_=fixture(tmp_path)
    outside=tmp_path/'outside.wav'
    sf.write(outside,wave,44100,subtype='PCM_16')
    clip=report/'001'/'auto.wav'
    clip.unlink()
    clip.symlink_to(outside)
    with pytest.raises(ValueError,match='escapes'):
        retain_feedback(raw,report,tmp_path/'escape')
    clip.unlink()
    sf.write(clip,wave.astype('float32')/32768,44100,subtype='FLOAT')
    model=export_coverage(report,records,{'purpose':'diagnostic','libraryManifestHash':'library'})
    for target in model['targets']:
        for c in target['candidates']:
            c.update(likeness=3,usefulness=None)
    raw.write_text(json.dumps({'schemaVersion':2,**model}))
    with pytest.raises(ValueError,match='PCM_16'):
        retain_feedback(raw,report,tmp_path/'float')
    assert not (tmp_path/'float').exists()


def test_render_provenance_changes_identity_and_metadata_tamper_is_rejected(tmp_path):
    raw,report,_,records,model=fixture(tmp_path)
    records[0]['candidates'][1]['provenance']={'renderer':'different'}
    changed=export_coverage(report,records,model['provenance'])
    assert changed['targets'][0]['candidates'][0]['id'] != changed['targets'][0]['candidates'][1]['id']
    with pytest.raises(ValueError,match='experiment/provenance'):
        retain_feedback(raw,report,tmp_path/'bad')


def test_local_editor_and_collection_links_are_optional_and_escaped(tmp_path):
    _,report,_,records,model=fixture(tmp_path)
    records[0]['candidates'][0]['editUrl']='pinned/index.html?sfx=Soundboard&seed=7'
    export_coverage(report,records,{**model['provenance'],'collectionUrl':'choices.json'})
    page=(report/'index.html').read_text()
    assert '<h1>Which recreations work?</h1>' in page
    assert 'href="pinned/index.html?sfx=Soundboard&amp;seed=7"' in page
    assert 'href="choices.json"' in page
    records[0]['candidates'][0]['editUrl']='javascript:alert(1)'
    with pytest.raises(ValueError,match='relative local'):
        export_coverage(report,records,model['provenance'])


def test_archive_verifies_flac_format_and_rejects_nonfinite_manifest_before_writing(tmp_path):
    raw,report,wave,_,_=fixture(tmp_path)
    out=tmp_path/'archive'
    retain_feedback(raw,report,out)
    clip=next((out/'audio').glob('*.flac'))
    sf.write(clip,wave,44100,subtype='PCM_16',format='WAV')
    with pytest.raises(ValueError,match='verification'):
        retain_feedback(raw,report,out)
    results=json.loads((report/'results.json').read_text())
    results['results'][0]['candidates'][0]['score']=float('nan')
    (report/'results.json').write_text(json.dumps(results))
    new=tmp_path/'new-parent'/'archive'
    with pytest.raises(ValueError):
        retain_feedback(raw,report,new)
    assert not new.parent.exists()
