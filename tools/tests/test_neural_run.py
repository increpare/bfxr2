from types import SimpleNamespace
import numpy as np
import pytest


def test_existing_inference_output_is_never_overwritten(tmp_path):
    from neural_invert.run import run
    output=tmp_path/'old';output.mkdir();(output/'keep').write_text('immutable')
    with pytest.raises(ValueError,match='fresh'):
        run(SimpleNamespace(output=output))
    assert (output/'keep').read_text()=='immutable'


def test_cli_renders_exported_candidate_and_records_provenance(tmp_path,monkeypatch):
    import json
    import soundfile as sf
    import neural_invert.run as runner
    from contextlib import nullcontext
    target=tmp_path/'source.wav';wave=np.sin(np.arange(5000)*.03).astype('float32')
    sf.write(target,wave,44100)
    checkpoint=tmp_path/'best.pt';checkpoint.write_bytes(b'model')
    old=tmp_path/'old.pt';old.write_bytes(b'old')
    metadata={'sourceHash':'dsp','engines':['Bfxr'],'checkpointHash':'modelhash'}
    monkeypatch.setattr(runner,'load_model',lambda path:(object(),metadata))
    class Renderer:
        inventory={'sourceHash':'dsp'}
    monkeypatch.setattr(runner,'Renderer',lambda:nullcontext(Renderer()))
    monkeypatch.setattr(runner,'BfxrRenderer',lambda jobs:nullcontext(object()))
    monkeypatch.setattr(runner,'OriginalBfxr',lambda *args:object())
    row={'synth':'Bfxr','params':{'waveType':2},'seed':12,'wave':wave,'score':1.,'provenance':{'actual':'DSP'}}
    monkeypatch.setattr(runner,'approximate',lambda *a,**k:{'raw':row,'neural':row,'selected':row,'original':row,'allRaw':[row],'allRefined':[row],'failures':[],'evaluations':10})
    output=tmp_path/'new'
    report=runner.run(SimpleNamespace(target=target,model=checkpoint,bfxr_checkpoint=old,output=output,
        selector_model=None,starts=4,budget=128,bfxr_budget=2000,seed=123))
    saved=json.loads((output/'result.json').read_text())
    assert saved['selected']['params']==row['params']
    assert saved['metadata']['modelSha256']=='modelhash'
    assert saved['metadata']['sourceHash']=='dsp' and saved['metadata']['complete']
    played,rate=sf.read(output/'selected.wav')
    assert rate==44100 and len(played)==len(wave)
    assert report['selected']['provenance']['actual']=='DSP'


def test_exported_pcm_scores_and_hashes_describe_the_actual_audition(tmp_path):
    import hashlib
    import soundfile as sf
    from match.objective import MatchObjective
    from neural_invert.experiment import _write_wave,audition_details,audition_pcm
    time=np.arange(22050,dtype='float32')/44100
    reference=np.sin(2*np.pi*440*time).astype('float32')*.5
    candidate=(np.sin(2*np.pi*451*time)*np.exp(-time*30)).astype('float32')*.2
    path=tmp_path/'candidate.wav';_write_wave(path,candidate)
    played,rate=sf.read(path,dtype='float32')
    objective=MatchObjective(reference);details=audition_details(path,objective)
    assert np.array_equal(played,audition_pcm(candidate))
    assert details['auditionMatchObjectiveScore']==pytest.approx(float(objective.score_batch([played])[0]))
    assert details['auditionWavSha256']==hashlib.sha256(path.read_bytes()).hexdigest()
    assert details['auditionPitchDiagnostic']['activeFrames']>0


def test_already_canonical_selection_is_exported_without_a_second_gain_change(tmp_path):
    import soundfile as sf
    from neural_invert.experiment import audition_pcm,_write_wave
    rng=np.random.default_rng(817)
    for _ in range(10):
        wave=(rng.normal(size=4096)*10**rng.uniform(-4,2)).astype('float32')
    selected=audition_pcm(wave)
    assert not np.array_equal(selected,audition_pcm(selected))
    path=tmp_path/'selected.wav';_write_wave(path,selected,canonical=True)
    played,_=sf.read(path,dtype='float32')
    assert np.array_equal(selected,played)
