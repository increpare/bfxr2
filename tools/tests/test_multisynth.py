import numpy as np
import pytest

from multisynth.features import describe, distances, prepare


def tone(freq=440, seconds=.3, sweep=0):
    t = np.arange(int(seconds * 44100), dtype=np.float32) / 44100
    return (np.sin(2*np.pi*(freq*t + sweep*t*t/2))*np.minimum(t/.005, 1)*np.exp(-t*5)).astype(np.float32)


def test_identity_gain_and_padding_invariance():
    wave = tone()
    ref = describe(wave)
    assert distances(ref, np.array([ref]))[0] == pytest.approx(0)
    padded = np.pad(wave*.2, (5000, 4000))
    assert distances(ref, np.array([describe(padded)]))[0] < .01


def test_pitch_sweep_and_duration_rankings():
    ref = describe(tone(350, .5, 1500))
    near = describe(tone(365, .5, 1400))
    reversed_sweep = describe(tone(1100, .5, -1500))
    noise = describe(np.random.default_rng(1).normal(0, .1, 22050).astype('float32'))
    scores = distances(ref, np.array([near, reversed_sweep, noise]))
    assert scores[0] < scores[1] < scores[2]
    ref = describe(tone())
    assert distances(ref, np.array([describe(tone(seconds=.31))]))[0] < distances(ref, np.array([describe(tone(seconds=1))]))[0]


def test_invalid_audio_rejected():
    for wave in [np.zeros(1000), np.array([]), np.array([np.nan]), np.array([np.inf])]:
        with pytest.raises(ValueError):
            prepare(wave)


def test_library_roundtrip_and_synth_balanced_retrieval(tmp_path):
    from multisynth.library import Library
    rows = [{'synth': s, 'params': {}, 'seed': i, 'preset': 'x'} for i,s in enumerate(['Bfxr','Bfxr','Clonkr'])]
    descriptors = np.array([describe(tone(440)), describe(tone(450)), describe(tone(800))])
    library = Library(rows, descriptors, {'sourceHash':'abc', 'featureVersion': 'auditory-v1'})
    library.save(tmp_path)
    loaded = Library.load(tmp_path, source_hash='abc')
    seeds = loaded.retrieve(descriptors[0], per_synth=1)
    assert [r['synth'] for r in seeds] == ['Bfxr','Clonkr']
    assert seeds[0]['score'] == 0
    with pytest.raises(ValueError, match='source'):
        Library.load(tmp_path, source_hash='changed')


def test_control_codec_handles_transitions_and_categories():
    from multisynth.search import ControlSpace
    spec = {'params': [
        {'name':'duration','type':'RANGE','min':.1,'max':4,'default':1},
        {'name':'kind','type':'BUTTONSELECT','values':[0,3,8],'default':0},
        {'name':'pitch','type':'KNOB_TRANSITION','min':0,'max':1,'default':{'start':.2,'end':.8,'curve':'linear'},'values':['linear','step']},
        {'name':'masterVolume','type':'RANGE','min':0,'max':1,'default':.5}]}
    space = ControlSpace(spec)
    params = {'duration':1,'kind':3,'pitch':{'start':.2,'end':.8,'curve':'linear'},'masterVolume':.5}
    rng = np.random.default_rng(1)
    for _ in range(30):
        p = space.mutate(params, rng, 1)
        assert .1 <= p['duration'] <= 4
        assert p['kind'] in [0,3,8]
        assert 0 <= p['pitch']['start'] <= 1
        assert 0 <= p['pitch']['end'] <= 1
        assert p['pitch']['curve'] in ['linear','step']
        assert p['masterVolume'] == .5
    assert params['pitch']['start'] == .2


def test_search_replay_budget_and_export(tmp_path):
    from multisynth.renderer import Renderer
    from multisynth.library import Library
    from multisynth.search import approximate
    from multisynth.report import export_match
    with Renderer() as renderer:
        params = renderer.sample('Clonkr', renderer.specs['Clonkr']['presets'][0], 123)
        params, wave = renderer.render('Clonkr', params, 123)
        library = Library([{'synth':'Clonkr','preset':'x','params':params,'seed':123}],
                          np.array([describe(wave)]), {})
        result = approximate(renderer, library, wave, experts=1, budget=4)
        assert result['search_evaluations'] == 4
        assert result['candidates'][0]['score'] == pytest.approx(0, abs=1e-6)
        assert np.all(np.diff(result['candidates'][0]['trace']) <= 0)
        export_match(tmp_path, wave, result, {'name':'test <unsafe>'})
        import json
        saved = json.loads((tmp_path/'matches.bcol').read_text())
        restored = json.loads(saved['Clonkr']['files'][0][1])
        _, replay = renderer.render('Clonkr', restored, 123)
        np.testing.assert_array_equal(wave, replay)
        assert 'test &lt;unsafe&gt;' in (tmp_path/'index.html').read_text()


def test_duration_augmentation_uses_actual_bfxr_controls():
    from multisynth.library import duration_variant
    p = {'attackTime':.2,'sustainTime':.3,'decayTime':.4,'waveType':2}
    q = duration_variant('Bfxr', p, .25)
    assert q['attackTime'] == pytest.approx(.1)
    assert q['sustainTime'] == pytest.approx(.15)
    assert q['decayTime'] == pytest.approx(.2)
    assert p['attackTime'] == .2


def test_jinglr_phrase_snapshot_does_not_search_ineffective_generator_controls():
    from multisynth.renderer import Renderer
    from multisynth.search import ControlSpace
    with Renderer() as renderer:
        space = ControlSpace(renderer.specs['Jinglr'])
        assert not {'noteCount','contour','rhythm'} & {path[0] for path,_ in space.controls}


def test_audit_detects_noise_seed_sensitivity():
    from multisynth.audit import seed_sensitivity
    from multisynth.renderer import Renderer
    with Renderer() as renderer:
        params, wave = renderer.render('Bfxr', {'waveType':3,'sustainTime':.05,'decayTime':.08}, 1)
        result = seed_sensitivity(renderer, {'synth':'Bfxr','params':params,'seed':1}, describe(wave), [1,2,3])
        assert result['scores'][0] == pytest.approx(0, abs=1e-7)
        assert result['mean'] > 0
        assert result['std'] > 0


def test_exported_collection_is_consumed_by_real_app_importer(tmp_path):
    import json
    import subprocess
    from pathlib import Path
    from multisynth.report import add_preset
    from multisynth.renderer import Renderer
    collection = {}
    with Renderer() as renderer:
        active = [s for s in renderer.specs.values() if s['collectionCompatible']]
        for spec in active:
            params = renderer.sample(spec['name'], spec['presets'][0], 7)
            add_preset(collection, {'synth':spec['name'], 'params':params}, spec['name']+' match')
    # Exercise actual SaveLoad.load_serialized_collection; UI hooks are inert.
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const data=JSON.parse(fs.readFileSync(0,'utf8'));
const inventory=require('./tools/render/multisynth_context').createMultisynthContext().inventory();
const tabs=inventory.synths.filter(s=>s.collectionCompatible).map(s=>({
 synth:{name:s.name,locked_params:{}},ui_initialized:false,update_ui(){},set_active_tab(){},
 set_selected_file(name){this.selected=this.files.find(f=>f[0]===name);}
}));
const ctx=vm.createContext({tabs,console,localStorage:{setItem(){}}});
vm.runInContext(fs.readFileSync('js/SaveLoad.js','utf8'),ctx);
ctx.payload=JSON.stringify(data);vm.runInContext('SaveLoad.load_serialized_collection(payload)',ctx);
for(const [name,record] of Object.entries(data)){
 if(name==='active_tab_name')continue;
 const tab=tabs.find(t=>t.synth.name===name);assert.ok(tab,name+' has a visible tab');
 assert.deepEqual(JSON.parse(JSON.stringify(tab.selected)),record.files[0]);
}
console.log(tabs.filter(t=>t.selected).length);
'''
    process = subprocess.run(['node','-e',script], input=json.dumps(collection), text=True,
                             cwd=Path(__file__).resolve().parents[2], capture_output=True)
    assert process.returncode == 0, process.stderr
    assert process.stdout.strip().splitlines()[-1] == str(len(active))


def test_audit_refuses_replaced_reference(tmp_path):
    from multisynth.audit import verify_source
    import hashlib
    reference = tmp_path/'source.wav'
    reference.write_bytes(b'original')
    record = {'path':str(reference),'sha256':hashlib.sha256(b'original').hexdigest()}
    verify_source(record)
    reference.write_bytes(b'changed')
    with pytest.raises(ValueError, match='changed'):
        verify_source(record)
