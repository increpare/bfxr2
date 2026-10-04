"""Behavioural checks for expert selection and unrestricted refinement."""
import numpy as np

from neural_invert.evaluate import rank_candidates, mutate_controls, pitch_summary


def test_rank_preserves_original_bfxr_as_separate_baseline():
    rows = [{'synth':'Clonkr','score':1.0},
            {'synth':'Bfxr','score':2.0,'expert':'original-bfxr'}]
    selected = rank_candidates(rows)
    assert selected['selected']['synth'] == 'Clonkr'
    assert selected['original']['expert'] == 'original-bfxr'


def test_musical_controls_can_move_across_full_range():
    spec = {'params':[{'name':'octave','type':'KNOB','min':1,'max':7},
                      {'name':'waveType','type':'BUTTONSELECT','values':[0,2,5]}]}
    anchor = {'octave':1,'waveType':0}
    rng = np.random.default_rng(12)
    draws = [mutate_controls(anchor,spec,rng,1.0) for _ in range(200)]
    assert max(p['octave'] for p in draws) > 6
    assert {p['waveType'] for p in draws} == {0,2,5}


def test_text_structure_is_preserved_and_numeric_controls_change():
    spec = {'params':[{'name':'phrase','type':'TEXT'},
                      {'name':'pitch','type':'KNOB','min':0,'max':1}]}
    anchor = {'phrase':'C4 E4 G4','pitch':.5}
    proposal = mutate_controls(anchor,spec,np.random.default_rng(1),.2)
    assert proposal['phrase'] == anchor['phrase']
    assert proposal['pitch'] != anchor['pitch']


def test_pitch_diagnostic_accepts_short_transients():
    summary = pitch_summary(np.ones(445,dtype=np.float32))
    assert summary['activeFrames'] >= 0


def test_original_expert_survives_all_neural_render_failures(monkeypatch):
    from neural_invert.evaluate import approximate
    import neural_invert.predict
    monkeypatch.setattr(neural_invert.predict,'predict',lambda *a,**k: [
        {'synth':'Broken','params':{},'seed':1}])
    class Renderer:
        def render(self,*a):raise ValueError('Broken learned proposal')
    class Original:
        def approximate(self,*a,**k):return {'synth':'Bfxr','score':1.,'expert':'original-bfxr',
            'wave':np.ones(4096,dtype=np.float32),'provenance':{'evaluations':10}}
    result=approximate(None,{},np.ones(4096,dtype=np.float32),Renderer(),Original(),budget=1)
    assert result['selected']['expert']=='original-bfxr'
    assert result['raw'] is None
    assert len(result['failures']) == 1


def test_synthetic_holdout_rejects_wrong_training_dataset(tmp_path,monkeypatch):
    from types import SimpleNamespace
    import pytest
    import neural_invert.predict
    from neural_invert.experiment import synthetic
    data=tmp_path/'data';data.mkdir();(data/'manifest.json').write_text('{}')
    monkeypatch.setattr(neural_invert.predict,'load_model',lambda p:(None,{'dataManifestHash':'wrong'}))
    output=tmp_path/'output'
    with pytest.raises(ValueError,match='training data'):
        synthetic(SimpleNamespace(model=tmp_path/'model.pt',data=data,output=output))
    assert not output.exists()


def test_transition_curve_is_a_mutable_category():
    spec={'params':[{'name':'bend','type':'KNOB_TRANSITION','min':0,'max':1,
                    'values':['Linear','Steps']}]}
    params={'bend':{'start':.2,'end':.8,'curve':'Linear'}}
    rng=np.random.default_rng(33)
    draws=[mutate_controls(params,spec,rng,.2) for _ in range(100)]
    assert {p['bend']['curve'] for p in draws} == {'Linear','Steps'}


def test_audition_preserves_scored_onset_and_duration(tmp_path):
    import soundfile as sf
    from neural_invert.experiment import _write_wave
    wave=np.r_[np.zeros(1200),np.sin(np.arange(4000)*.07),np.zeros(5000)].astype(np.float32)
    path=tmp_path/'audition.wav';_write_wave(path,wave)
    played,rate=sf.read(path,dtype='float32')
    assert rate==44100
    assert len(played)==len(wave)
    np.testing.assert_allclose(played,wave/max(np.max(np.abs(wave)),1e-9)*.5,atol=1/32768)


def test_pitch_summary_serializes_numpy_errors_and_missing_candidates():
    import json
    from neural_invert.tonal import summarize_pitch
    records=[{'candidates':{'selected':{'absolutePitchErrorSemitones':np.float64(.2)},'original':None}},
             {'candidates':{'selected':{'absolutePitchErrorSemitones':None},'original':None}}]
    result=json.loads(json.dumps(summarize_pitch(records),allow_nan=False))
    assert result['selected']['withinOneSemitone']==1
    assert result['selected']['unreliableOrMissing']==1
    assert result['original']['medianAbsoluteSemitones'] is None
