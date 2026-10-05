"""Immutable source validation and exact actual-render calibration artifacts."""
from copy import deepcopy
import importlib
import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf
import torch

from match.objective import MatchObjective
from multisynth.renderer import Renderer
from neural_invert.benchmark import audio_hash, probe_controls
from neural_invert.data import file_hash
from neural_invert.pitch_v5_features import FEATURE_HASH, FEATURE_CODE_HASH


torch.set_num_threads(1)
ENGINES = ('Bfxr', 'Transfxr', 'Pluckr')
VERSIONS = ('temporal-v3', 'pitch-v4', 'pitch-v5')


def api():
    assert importlib.util.find_spec('neural_invert.pitch_calibration_eval'), 'evaluator component missing'
    return importlib.import_module('neural_invert.pitch_calibration_eval')


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, allow_nan=False))


def tone(hz):
    return (.4*np.sin(2*np.pi*hz*np.arange(22050)/44100)).astype(np.float32)


class ToneRenderer:
    def __init__(self, specs):
        self.specs = deepcopy(specs)
        self.inventory = {'sourceHash': 'dsp-fixture'}
        self.calls = []
        self.failure = None

    def render(self, synth, params, seed):
        self.calls.append((synth, deepcopy(params), seed))
        if self.failure and len(self.calls) > 1:
            if isinstance(self.failure, BaseException):
                raise self.failure
            return deepcopy(params), self.failure.copy()
        hz = 3528*(params['frequency_start']**2+.001) if synth == 'Bfxr' else (
            40*2**(7*params['pitch']['start']) if synth == 'Transfxr' else 55*2**(4*params['pitch']))
        return deepcopy(params), tone(hz)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


@pytest.fixture(scope='module')
def specs():
    with Renderer() as renderer:
        return renderer.specs


@pytest.fixture
def frozen(tmp_path, monkeypatch, specs):
    module = api()
    renderer = ToneRenderer(specs)
    models, directories, bundles = {}, {}, {}
    for version in VERSIONS:
        root = tmp_path/'models'/version
        directories[version] = str(root)
        models[version], bundles[version] = {}, {}
        write(root/'assembly.json', {'complete': True})
        for name in ENGINES:
            folder = root/name
            folder.mkdir()
            (folder/'best.pt').write_bytes((version+name).encode())
            data = tmp_path/'data'/version
            write(data/'manifest.json', {'complete': True})
            meta = dict(checkpointHash=file_hash(folder/'best.pt'), dataManifestHash=file_hash(data/'manifest.json'),
                        featureHash='feature-'+version, featureCodeHash='code-'+version, sourceHash='dsp-fixture',
                        datasetPath=str(data), datasetFiles={}, spec=specs[name])
            write(folder/'training.json', {'metadata': meta, 'complete': True})
            models[version][name] = {k: meta[k] for k in ('checkpointHash','dataManifestHash','featureHash','featureCodeHash','sourceHash')}
            bundles[version][name] = (None, meta)
    monkeypatch.setattr(module, 'load_experts', lambda root, version: (bundles[version], lambda *a: pytest.fail('prediction forbidden')))
    source = tmp_path/'source'
    params = probe_controls(specs['Bfxr'], np.random.default_rng(1), 440, 'stationary')[0]
    _, target = renderer.render('Bfxr', params, 99)
    source.mkdir()
    target_path = source/'reference.wav'
    sf.write(target_path, target, 44100, subtype='FLOAT')
    parent_row = dict(id='probe-01', family='static', sourceSynth='Bfxr', sourceParams=params, sourceSeed=99,
                      sourceHash='dsp-fixture', audioHash=audio_hash(target), waveFile=str(target_path),waveFileSha256=file_hash(target_path))
    parent = tmp_path/'parent.json'
    write(parent, {'metadata': {'complete':True,'sourceHash':'dsp-fixture'}, 'results':[parent_row]})
    row = {k: parent_row[k] for k in ('id','family','sourceSynth','sourceParams','sourceSeed')}
    row.update(referenceAudioHash=audio_hash(target),referenceWaveFile=str(target_path),referenceWaveFileSha256=file_hash(target_path))
    objective = MatchObjective(target)
    candidates = []
    for name in ENGINES:
        for i in range(4):
            params = probe_controls(specs[name], np.random.default_rng(1), 220, 'stationary')[0]
            _, wave = renderer.render(name, params, i)
            path = source/'probe-01'/'temporal-v3'/f'{len(candidates):02}.wav'
            path.parent.mkdir(parents=True, exist_ok=True)
            sf.write(path, wave, 44100, subtype='FLOAT')
            candidates.append(dict(synth=name, params=params, seed=i, score=float(objective.score_batch([wave])[0]),
                                   waveFile=str(path), waveFileSha256=file_hash(path), audioHash=audio_hash(wave),
                                   provenance={'checkpointHash':models['temporal-v3'][name]['checkpointHash']}))
    row['arms'] = {'temporal-v3':dict(candidates=candidates,proposals=[{k:c[k] for k in ('synth','params','seed','provenance')} for c in candidates],failures=[],
        selected=candidates[0],unrestrictedSelected=min(candidates,key=lambda c:c['score']))}
    metadata = dict(complete=True,experiment='pitch-initial-lobe-v5',benchmarkPath=str(parent),benchmarkSha256=file_hash(parent),
                    sourceHash='dsp-fixture',models=models,modelDirectories=directories,candidateBudgetPerEngine=4,candidateBudgetTotal=12,
                    codeHashes=module.source_code_hashes(),v5DiagnosticFeatureHash=FEATURE_HASH,v5DiagnosticCodeHash=FEATURE_CODE_HASH)
    document = dict(metadata=metadata,results=[row])
    write(source/'manifest.json', metadata)
    write(source/'probe-01'/'report.json', row)
    write(source/'results.json', document)
    anchor=tmp_path/'source-audit.json'
    write(anchor, {'complete':True,'reports':{'fixture':{'reportPath':str(source/'results.json'), 'reportSha256':file_hash(source/'results.json')}}})
    monkeypatch.setattr(module,'SOURCE_AUDIT',anchor)
    renderer.calls.clear()
    return module, source/'results.json', document, renderer


def refresh(frozen):
    module, path, doc, _ = frozen
    write(path, doc)
    write(module.SOURCE_AUDIT, {'complete':True,'reports':{'fixture':{'reportPath':str(path),'reportSha256':file_hash(path)}}})
    write(path.parent/'manifest.json',doc['metadata'])
    for row in doc['results']:
        if '/' not in row['id'] and '\\' not in row['id']:
            write(path.parent/row['id']/'report.json',row)


def test_end_to_end_preserves_all_originals_and_three_selections(frozen,tmp_path,monkeypatch):
    module,path,doc,renderer = frozen
    monkeypatch.setattr(module,'Renderer',lambda:renderer)
    result = module.benchmark(path,tmp_path/'out')
    assert result['metadata']['complete'] is True
    row = result['results'][0]
    assert len(row['originals']) == 12
    assert [c['sourceCandidateIndex'] for c in row['originals']] == list(range(12))
    assert row['accounting']['originalValidationReplays'] == 12
    assert row['accounting']['additionalRenderCount'] <= 36
    assert row['accounting']['targetValidationReplays'] == 1
    for scope in ('unrestricted','sourceEngine'):
        assert set(('baseline','expandedObjective','selected','eligibility')) <= row[scope].keys()
        assert row[scope]['selected']['score'] <= row[scope]['baseline']['score']
    for candidate in row['originals']+row['accepted']:
        wave,rate=sf.read(candidate['waveFile'],dtype='float32')
        assert rate == 44100 and sf.info(candidate['waveFile']).subtype == 'FLOAT'
        assert audio_hash(wave) == candidate['audioHash']
        assert file_hash(candidate['waveFile']) == candidate['waveFileSha256']
        _,replay=renderer.render(candidate['synth'],candidate['params'],candidate['seed'])
        assert np.array_equal(wave,replay)
        assert candidate['score'] == pytest.approx(float(MatchObjective(tone(440)).score_batch([wave])[0]),abs=1e-8)
    json.loads((tmp_path/'out'/'results.json').read_text(),parse_constant=lambda value:pytest.fail(value))


@pytest.mark.parametrize('damage',['manifest','report','parent','source_audio','missing_audio','checkpoint','incomplete','missing_original','code','dsp','target_controls','candidate_score','unsafe_id'])
def test_refuses_modified_or_incomplete_inputs(frozen,tmp_path,monkeypatch,damage):
    module,path,doc,renderer=frozen
    monkeypatch.setattr(module,'Renderer',lambda:renderer)
    row=doc['results'][0]
    if damage in ('manifest','report'):
        changed=path.parent/('manifest.json' if damage=='manifest' else 'probe-01/report.json')
        write(changed,{})
    elif damage=='parent': Path(doc['metadata']['benchmarkPath']).write_text('{}')
    elif damage=='source_audio': Path(row['referenceWaveFile']).write_bytes(b'bad')
    elif damage=='missing_audio': Path(row['arms']['temporal-v3']['candidates'][0]['waveFile']).unlink()
    elif damage=='checkpoint': (Path(doc['metadata']['modelDirectories']['temporal-v3'])/'Bfxr/best.pt').write_bytes(b'bad')
    elif damage=='dsp': renderer.inventory['sourceHash']='different'
    else:
        if damage=='incomplete': doc['metadata']['complete']=False
        elif damage=='missing_original': row['arms']['temporal-v3']['candidates'].pop()
        elif damage=='code': doc['metadata']['codeHashes']['pitch_v5_eval.py']='bad'
        elif damage=='target_controls': row['sourceParams']['frequency_start']=.123
        elif damage=='candidate_score': row['arms']['temporal-v3']['candidates'][0]['score']+=1
        elif damage=='unsafe_id': row['id']='../escape'
        refresh(frozen)
    with pytest.raises((ValueError,FileNotFoundError)):
        module.benchmark(path,tmp_path/'out')
    if (tmp_path/'out'/'manifest.json').exists():
        assert json.loads((tmp_path/'out'/'manifest.json').read_text())['complete'] is False


def test_existing_output_is_never_reused(frozen,tmp_path):
    module,path,_,_=frozen
    out=tmp_path/'out';out.mkdir()
    with pytest.raises(FileExistsError): module.benchmark(path,out)


@pytest.mark.parametrize('bad', [np.array([np.nan,1],dtype=np.float32), np.ones((2,3),dtype=np.float32), np.array([],dtype=np.float32)])
def test_invalid_pcm_preserved_in_npy(tmp_path,bad):
    saved=api().save_audio(tmp_path/'failed',bad)
    assert saved['failureArtifact']['shape']==list(bad.shape)
    path=saved['failureArtifact']['path']
    assert file_hash(path)==saved['failureArtifact']['sha256']
    assert np.array_equal(np.load(path),bad,equal_nan=True)
    json.dumps(saved,allow_nan=False)


def test_silent_pcm_is_saved_as_float(tmp_path):
    saved=api().save_audio(tmp_path/'silent',np.zeros(200,dtype=np.float32))
    assert sf.info(saved['waveFile']).subtype=='FLOAT'
    assert saved['audible'] is False


@pytest.mark.parametrize('mode',['error','silent','nonfinite','shape','bounds'])
def test_proposal_failures_and_bounds_have_exact_call_accounting(frozen,tmp_path,mode):
    module,path,doc,renderer=frozen
    original_render=renderer.render
    originals=doc['results'][0]['arms']['temporal-v3']['candidates']
    def render(name,params,seed):
        is_original=any(c['synth']==name and c['params']==params and c['seed']==seed for c in originals)
        if is_original or (seed==99 and params==doc['results'][0]['sourceParams']):
            return original_render(name,params,seed)
        if mode=='error': raise RuntimeError('proposal failure')
        if mode=='silent': return deepcopy(params),np.zeros(22050,dtype=np.float32)
        if mode=='nonfinite': return deepcopy(params),np.array([np.nan,np.inf],dtype=np.float32)
        if mode=='shape': return deepcopy(params),np.ones((2,3),dtype=np.float32)
        return original_render(name,params,seed)
    renderer.render=render
    if mode=='bounds':
        for name in ENGINES:
            control=next(p for p in renderer.specs[name]['params'] if p['name']==('frequency_start' if name=='Bfxr' else 'pitch'))
            value=originals[ENGINES.index(name)*4]['params'][control['name']]
            if isinstance(value,dict): value=value['start']
            control.update(min=value,max=value)
    result=module.evaluate_target(doc['results'][0],renderer,tmp_path/'target')
    attempts=[a for c in result['calibrations'] for a in c['attempts']]
    assert result['accounting']['additionalRenderCount']==sum(a['renderCount'] for a in attempts)
    assert result['accounting']['failedRenderCalls']==(12 if mode=='error' else 0)
    if mode=='bounds':
        assert all(a['renderCount']==0 and a['reason']=='bounds_unchanged' for a in attempts)
    elif mode in ('nonfinite','shape'):
        assert all('failureArtifact' in a for a in attempts)
    elif mode=='silent':
        assert all(a['reason']=='silent_audio' and not a['audible'] and 'waveFile' in a for a in attempts)
    else:
        assert all(a['reason']=='render_error' and 'waveFile' not in a for a in attempts)
    json.dumps(result,allow_nan=False)


def test_interruption_retains_incomplete_manifest_and_render_call(frozen,tmp_path,monkeypatch):
    module,path,doc,renderer=frozen
    monkeypatch.setattr(module,'Renderer',lambda:renderer)
    original_render=renderer.render
    calls=0
    def interrupt(name,params,seed):
        nonlocal calls
        calls+=1
        if calls==3: raise KeyboardInterrupt('test interruption')
        return original_render(name,params,seed)
    renderer.render=interrupt
    out=tmp_path/'out'
    with pytest.raises(KeyboardInterrupt): module.benchmark(path,out)
    manifest=json.loads((out/'manifest.json').read_text())
    assert manifest['complete'] is False
    assert not (out/'results.json').exists()
    journal=json.loads((out/'probe-01/candidate-00/01.json').read_text())
    assert journal['renderCount']==1 and journal['status']=='render_error'
    assert (out/'probe-01/candidate-00/00.wav').is_file()
    partial=json.loads((out/'probe-01/report.json').read_text())
    assert partial['accounting']['originalValidationReplays']==1
    assert partial['accounting']['additionalRenderCount']==1
    assert partial['accounting']['failedRenderCalls']==1


def test_changes_during_run_leave_incomplete_output(frozen,tmp_path,monkeypatch):
    module,path,doc,renderer=frozen
    monkeypatch.setattr(module,'Renderer',lambda:renderer)
    original=module.evaluate_target
    def evaluate(*args):
        result=original(*args)
        Path(doc['metadata']['benchmarkPath']).write_text('{}')
        return result
    monkeypatch.setattr(module,'evaluate_target',evaluate)
    with pytest.raises(ValueError,match='changed during evaluation'):
        module.benchmark(path,tmp_path/'out')
    assert json.loads((tmp_path/'out/manifest.json').read_text())['complete'] is False


def test_production_audit_anchor_rejects_modified_whole_report(tmp_path,monkeypatch):
    module=api()
    path=tmp_path/'results.json';write(path,{'summary':{'test':1}})
    anchor=tmp_path/'anchor.json'
    write(anchor,{'complete':True,'reports':{'paired':{'reportPath':str(path),'reportSha256':file_hash(path)}}})
    monkeypatch.setattr(module,'SOURCE_AUDIT',anchor)
    bindings={}
    module.bind_source_audit(path,bindings)
    assert str(anchor.resolve()) in bindings
    write(path,{'summary':{'test':2}})
    with pytest.raises(ValueError,match='binding'):
        module.bind_source_audit(path,{})


def test_real_dsp_candidate_artifact_exact_identity(tmp_path):
    module=api()
    with Renderer() as renderer:
        params=probe_controls(renderer.specs['Bfxr'],np.random.default_rng(11),220,'stationary')[0]
        canonical,wave=renderer.render('Bfxr',params,713)
        source=module.save_audio(tmp_path/'source',wave)
        objective=MatchObjective(wave)
        candidate=dict(synth='Bfxr',params=canonical,seed=713,score=float(objective.score_batch([wave])[0]),**source)
        audited=module._AuditedRenderer(renderer,candidate,objective,tmp_path/'replayed',0)
        replay_controls,replay=audited.render('Bfxr',canonical,713)
        assert replay_controls==canonical and np.array_equal(wave,replay)
        saved=audited.calls[0]
        assert audio_hash(sf.read(saved['waveFile'],dtype='float32')[0])==audio_hash(wave)
        assert saved['status']=='validated'


def test_target_render_failure_is_counted_and_retained(frozen,tmp_path,monkeypatch):
    module,path,doc,renderer=frozen
    monkeypatch.setattr(module,'Renderer',lambda:renderer)
    def fail(*args): raise RuntimeError('target replay failure')
    renderer.render=fail
    with pytest.raises(RuntimeError,match='target replay'):
        module.benchmark(path,tmp_path/'out')
    row=json.loads((tmp_path/'out/probe-01/report.json').read_text())
    assert row['accounting']['targetValidationReplays']==1
    assert row['accounting']['failedRenderCalls']==1
    journal=json.loads((tmp_path/'out/probe-01/target-validation.json').read_text())
    assert journal['renderCount']==1 and journal['status']=='render_error'


def test_bound_checkpoint_symlink_cannot_be_retargeted(tmp_path):
    module=api()
    first=tmp_path/'first.pt';first.write_bytes(b'frozen')
    second=tmp_path/'second.pt';second.write_bytes(b'replacement')
    link=tmp_path/'best.pt';link.symlink_to(first)
    bindings={}
    module._bind(bindings,link)
    link.unlink();link.symlink_to(second)
    with pytest.raises(ValueError,match='binding changed'):
        module._check_bindings(bindings)


def test_relocated_report_requires_audited_whole_file_hash(tmp_path,monkeypatch):
    module=api()
    path=tmp_path/'original.json';write(path,{'summary':{'test':1}})
    anchor=tmp_path/'anchor.json'
    write(anchor,{'complete':True,'reports':{'paired':{'reportPath':str(path),'reportSha256':file_hash(path)}}})
    monkeypatch.setattr(module,'SOURCE_AUDIT',anchor)
    relocated=tmp_path/'relocated.json';relocated.write_bytes(path.read_bytes())
    module.bind_source_audit(relocated,{})
    write(relocated,{'summary':{'test':2}})
    with pytest.raises(ValueError,match='binding'):
        module.bind_source_audit(relocated,{})


@pytest.mark.parametrize('stage',['audio','before_call','after_call','error_journal'])
@pytest.mark.parametrize('failure_type',[OSError,ValueError])
def test_artifact_persistence_failure_aborts_incomplete_run(frozen,tmp_path,monkeypatch,stage,failure_type):
    module,path,doc,renderer=frozen
    monkeypatch.setattr(module,'Renderer',lambda:renderer)
    original_save,original_write=module.save_audio,module._json_write
    original_render=renderer.render
    actual_calls=0
    def render(*args):
        nonlocal actual_calls
        actual_calls+=1
        if stage=='error_journal' and actual_calls==3:
            raise RuntimeError('real renderer failure')
        return original_render(*args)
    renderer.render=render
    injected=False
    def save(stem,wave):
        nonlocal injected
        if stage=='audio' and Path(stem).parent.name=='candidate-00' and Path(stem).name=='01':
            injected=True
            raise failure_type('injected disk failure')
        return original_save(stem,wave)
    def write_json(dest,value):
        nonlocal injected
        statuses={'before_call':'started','after_call':'returned','error_journal':'render_error'}
        if (stage in statuses and not injected and Path(dest).parent.name=='candidate-00' and
                Path(dest).name=='01.json' and value.get('status')==statuses[stage]):
            injected=True
            raise failure_type('injected journal failure')
        return original_write(dest,value)
    monkeypatch.setattr(module,'save_audio',save)
    monkeypatch.setattr(module,'_json_write',write_json)
    out=tmp_path/'out'
    with pytest.raises(Exception,match='[Aa]rtifact persistence'):
        module.benchmark(path,out)
    assert injected
    assert json.loads((out/'manifest.json').read_text())['complete'] is False
    assert not (out/'results.json').exists()
    row=json.loads((out/'probe-01/report.json').read_text())
    assert row['complete'] is False
    assert row['accounting']['additionalRenderCount']==(0 if stage=='before_call' else 1)
    assert row['accounting']['failedRenderCalls']==(1 if stage=='error_journal' else 0)
    assert actual_calls==(2 if stage=='before_call' else 3)
    assert row['failure']['type']=='ArtifactPersistenceError'
