"""Evidence and listening-contract tests; all writes use temporary directories."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from neural_invert import pitch_calibration_gallery as gallery
from neural_invert.data import file_hash
from neural_invert.experiment import audition_pcm, listening_history
from neural_invert.pitch_calibration_eval import read_audio, save_audio

ROOT = Path(__file__).resolve().parents[1]/'multisynth'


def tone(hz=300, seconds=.3):
    return (.3*np.sin(2*np.pi*hz*np.arange(int(44100*seconds))/44100)).astype('float32')


def source_fixture(tmp_path):
    path = tmp_path/'source.wav'
    sf.write(path, tone(), 44100, subtype='FLOAT')
    wave = audition_pcm(gallery.prepare_target(path))
    return dict(name='fresh.wav', path=str(path), sha256=file_hash(path),
                previouslyRatedReference=False,
                auditionFloat32Sha256=hashlib.sha256(wave.tobytes()).hexdigest()), wave


def test_fresh_reference_has_exactly_one_audition_transform(tmp_path, monkeypatch):
    source, expected = source_fixture(tmp_path)
    original = gallery.audition_pcm
    calls = []
    def once(wave):
        calls.append(True)
        return original(wave)
    monkeypatch.setattr(gallery, 'audition_pcm', once)
    output = tmp_path/'target.wav'
    actual = gallery.prepare_reference(source, output, None, {}, {})
    assert len(calls) == 1
    assert np.array_equal(actual, expected)
    assert np.array_equal(sf.read(output, dtype='float32')[0], expected)
    assert sf.info(output).subtype == 'PCM_16'
    source['auditionFloat32Sha256'] = 'wrong'
    with pytest.raises(ValueError, match='float32'):
        gallery.prepare_reference(source, tmp_path/'bad.wav', None, {}, {})


def test_charm_reference_copies_exact_archive_not_source_metadata(tmp_path):
    sources = json.loads(gallery.DEFAULT_TARGETS.read_text())['targets']
    source = sources[0]
    old = json.loads((gallery.DEFAULT_OLD_GALLERY/'results.json').read_text())['results'][4]
    refs = {}
    for archive in gallery.DEFAULT_ARCHIVES:
        for target in json.loads((archive/'manifest.json').read_text())['targets']:
            refs.setdefault(target['source']['sha256'], []).append((archive, target['referenceAudio']))
    wave = gallery.prepare_reference(source, tmp_path/'target.wav', old, refs,
                                     gallery.old_reference_bindings(gallery.DEFAULT_OLD_GALLERY))
    assert gallery.pcm_hash(tmp_path/'target.wav') == source['archivedReferencePcmSha256']
    assert gallery.pcm_hash(tmp_path/'target.wav') != source['normalizedPcmSha256']
    assert np.array_equal(wave, sf.read(gallery.DEFAULT_OLD_GALLERY/'005/target.wav', dtype='float32')[0])


def test_cards_preserve_aliases_and_fresh_baseline(tmp_path):
    def row(wave, index):
        return dict(synth='Bfxr', params={'x': index}, seed=1, score=index,
                    wave=wave, provenance={}, sourceCandidateIndex=index,
                    **save_audio(tmp_path/f'actual{index}', wave))
    baseline, original = row(tone(), 0), row(tone(400), 1)
    selection = dict(selected=baseline, baseline=baseline)
    cards = gallery.make_cards(tmp_path, selection, original, [], 'dsp')
    assert len(cards) == 2
    assert cards[0]['label'] == 'Pitch-calibrated approximation'
    assert cards[0]['provenance']['identicalPcmAliases'][0]['role'] == 'baseline'
    assert cards[1]['role'] == 'original'
    assert gallery.display_decision(cards, [], False)['included'] is True


def test_charm_both_anchors_take_precedence_and_new_pair_is_useful(tmp_path):
    source = json.loads(gallery.DEFAULT_TARGETS.read_text())['targets'][0]
    observations = gallery.baseline_observations(listening_history(gallery.DEFAULT_ARCHIVES), source)
    wave = sf.read(observations[0][1]['archive']/observations[0][1]['candidate']['audio']['file'], dtype='float32')[0]
    row = dict(synth='Bfxr', params={}, seed=1, score=1., wave=wave, provenance={})
    cards = gallery.make_cards(tmp_path, dict(selected=row, baseline=row), row, observations, 'dsp')
    roles = [c['role'] for c in cards]
    aliases = [a['role'] for c in cards for a in c['provenance'].get('identicalPcmAliases', [])]
    assert 'anchor' in roles + aliases and 'previous' in roles + aliases
    assert 'original' not in roles + aliases
    # New pair of separately heard anchors is meaningful if never compared.
    assert gallery.display_decision(cards, [{cards[0]['provenance']['auditionPcmSha256']}], True)['included']
    exact = {c['provenance']['auditionPcmSha256'] for c in cards}
    assert not gallery.display_decision(cards, [exact], True)['included']
    assert not gallery.display_decision(cards[:1], [], False)['included']


def test_existing_output_rejected_before_any_load(tmp_path):
    with pytest.raises(ValueError, match='Fresh output'):
        gallery.run(output=tmp_path)


def test_calibration_preserves_full_sixteen_member_pool_and_dynamic_budget(tmp_path, monkeypatch):
    pool = [dict(synth='Bfxr', params={'x': i}, seed=i, score=1., wave=tone(), provenance={})
            for i in range(16)]
    pool[-1]['calibrationCompatible'] = False
    class Renderer:
        specs = {}
        def render(self, synth, params, seed):
            return params, tone()
    def calibration(candidate, target, renderer, objective):
        params, wave = renderer.render(candidate['synth'], candidate['params'], candidate['seed'])
        # A failed actual call followed by an unrendered clamp is still evidence.
        renderer.render(candidate['synth'], params, candidate['seed'])
        return dict(original={**candidate, 'wave': wave}, accepted=[], status='bounds_unchanged',
                    additionalRenderCount=1, attempts=[dict(step=1, renderCount=1, accepted=False,
                    reason='duplicate_audio', wave=wave), dict(step=2, renderCount=0, accepted=False,
                    reason='bounds_unchanged', clamps=[{'control':'x'}])])
    monkeypatch.setattr(gallery, 'calibrate_candidate', calibration)
    class Objective:
        def score_batch(self, waves):
            return [1.] * len(waves)
    monkeypatch.setattr(gallery, 'MatchObjective', lambda wave: Objective())
    def selection(originals, accepted, wave):
        return dict(baseline=originals[-1], expandedObjective=originals[-1],
                    selected=originals[-1], eligibility=[], reason='weak_target')
    monkeypatch.setattr(gallery, 'select_candidates', selection)
    result = gallery.calibrate_pool(pool, tone(), Renderer(), tmp_path/'pitch')
    assert len(result['originals']) == 16 and result['accepted'] == []
    assert result['accounting']['maximumAdditionalRenders'] == 48
    assert result['accounting']['additionalRenderCount'] == 15
    assert result['accounting']['originalValidationReplays'] == 15
    assert result['calibrations'][-1]['status'] == 'incompatible_original_backend'
    assert result['selection']['selected']['sourceCandidateIndex'] == 15
    assert len(result['callJournalFiles']) == 30
    assert result['calibrations'][0]['attempts'][1]['clamps']
    assert read_audio(**dict(path=result['originals'][0]['waveFile'],
                            file_sha256=result['originals'][0]['waveFileSha256'],
                            pcm_hash=result['originals'][0]['audioHash'])).dtype == np.float32


def test_calibration_write_failure_is_fatal_and_report_stays_incomplete(tmp_path, monkeypatch):
    pool = [dict(synth='Bfxr', params={}, seed=1, score=1., wave=tone(), provenance={})]
    def fail(*args, **kwargs):
        raise OSError('disk full')
    monkeypatch.setattr(gallery, 'save_audio', fail)
    with pytest.raises(gallery.ArtifactPersistenceError, match='disk full'):
        gallery.calibrate_pool(pool, tone(), object(), tmp_path/'pitch')
    report = json.loads((tmp_path/'pitch/report.json').read_text())
    assert report['complete'] is False and report['failure']['type'] == 'ArtifactPersistenceError'


def test_original_native_pcm_is_retained_when_shipped_dsp_differs(tmp_path):
    native = tone(300)
    candidate = dict(synth='Bfxr', params={'frequency': .5}, seed=4,
                     score=0., wave=native, provenance={'evaluations': 3003, 'budget': 2000})
    class Native:
        def render(self, params, seed):
            return native
    class Shipped:
        def render(self, synth, params, seed):
            return params, tone(600)
    objective = gallery.MatchObjective(native)
    candidate['score'] = float(objective.score_batch([native])[0])
    row, diagnostic = gallery.verify_original(candidate, Native(), Shipped(), objective,
                                              tmp_path, {'sourceHash':'native', 'files':{}})
    assert row['calibrationCompatible'] is False
    assert np.array_equal(row['wave'], native)
    assert diagnostic['shippedDspMatches'] is False
    assert diagnostic['actualEvaluations'] == 3003
    assert row['renderSourceHash'] == 'native'


def test_real_dsp_calibration_pool_smoke(tmp_path):
    with gallery.Renderer() as renderer:
        spec = renderer.specs['Bfxr']
        params = deepcopy(spec['defaults'])
        params.update(waveType=2, frequency_start=.24, sustainTime=.25, decayTime=.1)
        canonical, wave = renderer.render('Bfxr', params, 19)
        target = wave.copy()
        row = dict(synth='Bfxr', params=canonical, seed=19,
                   score=float(gallery.MatchObjective(target).score_batch([wave])[0]),
                   wave=wave, provenance={})
        result = gallery.calibrate_pool([row], target, renderer, tmp_path/'pitch')
    assert result['complete'] is True
    assert result['selection']['baseline']['audioHash'] == gallery.audio_hash(wave)
    assert result['accounting']['additionalRenderCount'] <= 3


def test_gate_requires_completed_pass_and_binds_audited_reports(tmp_path, monkeypatch):
    report = tmp_path/'results.json'
    report.write_text(json.dumps({'metadata': {'complete': True}, 'results': []}))
    audit = tmp_path/'audit.json'
    data = dict(complete=True, gate={'passed': True}, reports={'paired':{
        'path': str(report), 'sha256': file_hash(report)}})
    audit.write_text(json.dumps(data))
    monkeypatch.setattr(gallery, 'GATE_SHA', file_hash(audit))
    bindings = {}
    gallery.validate_gate(audit, bindings)
    assert str(report) in bindings
    for key in ('complete', 'passed'):
        bad = deepcopy(data)
        if key == 'complete': bad['complete'] = False
        else: bad['gate']['passed'] = False
        audit.write_text(json.dumps(bad))
        monkeypatch.setattr(gallery, 'GATE_SHA', file_hash(audit))
        with pytest.raises(ValueError, match='gate'):
            gallery.validate_gate(audit, {})
    audit.write_text(json.dumps(data))
    monkeypatch.setattr(gallery, 'GATE_SHA', file_hash(audit))
    report.write_text('{}')
    with pytest.raises(ValueError, match='binding'):
        gallery.validate_gate(audit, {})


def test_fixed_manifest_order_and_identity_are_required(tmp_path, monkeypatch):
    frozen = json.loads(gallery.DEFAULT_TARGETS.read_text())
    path = tmp_path/'targets.json'
    path.write_text(json.dumps(frozen))
    monkeypatch.setattr(gallery, 'TARGETS_SHA', file_hash(path))
    assert gallery.validate_manifest(path, {}) == frozen['targets']
    frozen['targets'].reverse()
    path.write_text(json.dumps(frozen))
    monkeypatch.setattr(gallery, 'TARGETS_SHA', file_hash(path))
    with pytest.raises(ValueError, match='order'):
        gallery.validate_manifest(path, {})


def test_fresh_pool_includes_every_raw_refined_and_native_candidate(tmp_path, monkeypatch):
    raw = [dict(synth=engine, params={'i': i}, seed=i, provenance={})
           for engine in gallery.ENGINES for i in range(4)]
    class Renderer:
        specs = {}; inventory = {'sourceHash':'dsp'}
        def render(self, synth, params, seed):
            return params, tone()
    class Original:
        def approximate(self, wave, objective, budget, seed):
            assert budget == 2000 and seed == 20261011+2*1009
            return dict(synth='Bfxr', params={'i': 99}, seed=8, wave=tone(), score=1.,
                        provenance={'budget':budget, 'evaluations':3003})
    def refine(row, renderer, objective, target, budget, seed):
        assert budget == 384
        for _ in range(budget):
            renderer.render(row['synth'], row['params'], row['seed'])
        return {**row, 'provenance': {'refinement': {'seed': seed, 'budget': budget}}}
    monkeypatch.setattr(gallery, 'proposals', lambda *args: raw)
    monkeypatch.setattr(gallery, 'refine_guarded', refine)
    # Check independent fixed engine-index seeds despite an engine's order/score.
    monkeypatch.setattr(gallery, 'verify_original', lambda c, *args: (c, {'actualEvaluations':3003}))
    pool, diagnostic, original = gallery.fresh_pool({}, tone(), Renderer(), object(), Original(),
                                                  {}, tmp_path, 2)
    assert len(pool) == 16
    assert [r['poolRole'] for r in pool] == ['raw']*12+['refined']*3+['original-bfxr']
    assert diagnostic['refinementSeeds'] == {e:20261011+2*1009+i*71 for i,e in enumerate(gallery.ENGINES)}
    assert diagnostic['originalBackend']['actualEvaluations'] == 3003
    assert original['params'] == {'i':99}


def test_cached_pool_checks_score_checkpoint_and_heard_selected_pcm(tmp_path):
    old = json.loads((gallery.DEFAULT_OLD_GALLERY/'results.json').read_text())
    charm = old['results'][4]
    wave = sf.read(gallery.DEFAULT_OLD_GALLERY/'005/target.wav', dtype='float32')[0]
    experts = {name: (None, {'checkpointHash': digest}) for name, digest in old['metadata']['checkpointHashes'].items()}
    # Cheap real replay of cached rows; no inference/refinement/production writes.
    with gallery.Renderer() as renderer, gallery.BfxrRenderer(jobs=1) as native:
        backend = gallery.backend_provenance(native)
        pool, diagnostic, original = gallery.cached_pool(charm, wave, renderer, native, backend,
            tmp_path, experts, gallery.DEFAULT_OLD_GALLERY)
        assert len(pool) == 15
        assert len(diagnostic['allRaw']) == 11 and len(diagnostic['allRefined']) == 3
        assert diagnostic['failures'] == [{'synth':'Bfxr', 'error':'Silent prediction'}]
        assert original['calibrationCompatible'] is True
        broken = deepcopy(charm)
        broken['diagnostics']['allRaw'][0]['score'] += .1
        with pytest.raises(ValueError, match='score'):
            gallery.cached_pool(broken, wave, renderer, native, backend, tmp_path/'bad', experts,
                                gallery.DEFAULT_OLD_GALLERY)


def test_incompatible_original_has_its_own_refreshed_pitch_evidence(tmp_path):
    row = dict(synth='Bfxr', params={}, seed=1, score=0., wave=tone(), provenance={},
               calibrationCompatible=False)
    result = gallery.calibrate_pool([row], tone(), object(), tmp_path/'pitch')
    saved = result['originals'][0]
    assert saved['v5Pitch']['reliable'] and saved['v5PitchComparison']['directionMatches']
    assert saved['audioHash'] == gallery.audio_hash(row['wave'])


def test_failed_final_pool_write_cannot_mark_report_complete(tmp_path, monkeypatch):
    row = dict(synth='Bfxr', params={}, seed=1, score=0., wave=tone(), provenance={},
               calibrationCompatible=False)
    original = gallery._json_write
    failed = []
    def fail_final(path, value):
        if value.get('complete') is True and not failed:
            failed.append(True)
            raise OSError('final write fails')
        return original(path, value)
    monkeypatch.setattr(gallery, '_json_write', fail_final)
    with pytest.raises(OSError, match='final write fails'):
        gallery.calibrate_pool([row], tone(), object(), tmp_path/'pitch')
    assert json.loads((tmp_path/'pitch/report.json').read_text())['complete'] is False


def test_input_validation_rejects_unbound_old_report_before_model_load(tmp_path, monkeypatch):
    monkeypatch.setattr(gallery, 'validate_gate', lambda *a: {})
    monkeypatch.setattr(gallery, 'validate_manifest', lambda *a: [])
    old = tmp_path/'old'; old.mkdir()
    (old/'results.json').write_text('{}')
    class Renderer:
        inventory = {'sourceHash':'dsp'}
    with pytest.raises(ValueError, match='binding'):
        gallery.validate_inputs('targets', 'model', old, [], 'checkpoint', 'gate', Renderer())


@pytest.fixture
def run_fixture(tmp_path, monkeypatch):
    source, wave = source_fixture(tmp_path)
    sources = [{**source, 'name':str(i)} for i in range(5)]
    context = dict(sources=sources, experts={}, oldRows={}, observations={}, references={},
                   referenceBindings={}, heardSets={}, inputBindings={}, codeHashes={},
                   sourceHash='dsp', checkpointHashes={})
    monkeypatch.setattr(gallery, 'validate_inputs', lambda *a: context)
    monkeypatch.setattr(gallery, '_code_bindings', lambda: {})
    monkeypatch.setattr(gallery, 'prepare_reference', lambda s, dest, *a: (sf.write(dest, wave, 44100, subtype='PCM_16') or wave))
    class Renderer:
        specs = {}; inventory = {'sourceHash':'dsp'}
        def __init__(self, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
    monkeypatch.setattr(gallery, 'Renderer', Renderer)
    monkeypatch.setattr(gallery, 'BfxrRenderer', Renderer)
    monkeypatch.setattr(gallery, 'OriginalBfxr', lambda *a: object())
    monkeypatch.setattr(gallery, 'backend_provenance', lambda r: {'sourceHash':'native','files':{}})
    def pool(experts, target, renderer, native, model, backend, dest, index):
        a = dict(synth='Bfxr', params={'x':1}, seed=1, wave=wave, score=0., provenance={})
        b = dict(synth='Bfxr', params={'x':2}, seed=2, wave=tone(400), score=1., provenance={})
        # Last target has just one distinct PCM option and must be kept as skipped evidence.
        if index == 4: b = deepcopy(a)
        return [a,b], {'allRaw':[gallery._without_wave(a)], 'allRefined':[], 'failures':[]}, b
    monkeypatch.setattr(gallery, 'fresh_pool', pool)
    def calibrate(pool, target, renderer, dest):
        originals = [gallery.persist_candidate({**r,'sourceCandidateIndex':i}, dest/f'original-{i}') for i,r in enumerate(pool)]
        return dict(originals=originals, accepted=[], calibrations=[], accounting={}, callJournalFiles=[],
                    selection={'selected':originals[0], 'baseline':originals[0], 'expandedObjective':originals[0],
                               'eligibility':[], 'reason':'weak_target'})
    monkeypatch.setattr(gallery, 'calibrate_pool', calibrate)
    return tmp_path/'gallery'


def test_run_exports_existing_quick_ui_and_binds_all_five_reports(run_fixture):
    result = gallery.run(output=run_fixture)
    meta = json.loads((run_fixture/'manifest.json').read_text())
    report = json.loads((run_fixture/'results.json').read_text())
    assert meta['complete'] is True and report['metadata'] == meta
    assert len(meta['targetReports']) == 5 and len(meta['skippedTargets']) == 1
    assert len(result['targets']) == len(report['results']) == 4
    for row in meta['targetReports']:
        assert Path(row['reportFile']).is_absolute()
        assert file_hash(row['reportFile']) == row['reportFileSha256']
    page = (run_fixture/'index.html').read_text()
    assert 'quick-listening' in page and 'Pitch-calibrated approximation' in page
    assert meta['humanReviewRequired'] is True


def test_export_failure_leaves_incomplete_manifest(run_fixture, monkeypatch):
    def fail(*args):
        raise OSError('export disk full')
    monkeypatch.setattr(gallery, 'export_coverage', fail)
    with pytest.raises(OSError, match='export disk full'):
        gallery.run(output=run_fixture)
    meta = json.loads((run_fixture/'manifest.json').read_text())
    assert meta['complete'] is False and 'failure' in meta


def test_accepted_calibration_and_render_error_retain_exact_call_artifacts(tmp_path):
    with gallery.Renderer() as renderer:
        params = deepcopy(renderer.specs['Bfxr']['defaults'])
        params.update(waveType=2, frequency_start=.24, sustainTime=.5, decayTime=.2)
        params, wave = renderer.render('Bfxr', params, 31)
        _, target = renderer.render('Bfxr', {**params, 'frequency_start':.35}, 31)
        row = dict(synth='Bfxr', params=params, seed=31, wave=wave,
                   score=float(gallery.MatchObjective(target).score_batch([wave])[0]), provenance={})
        row['renderSourceHash'] = 'native-backend'
        good = gallery.calibrate_pool([row], target, renderer, tmp_path/'good')
        assert good['accepted']
        for accepted in good['accepted']:
            assert accepted['renderSourceHash'] == renderer.inventory['sourceHash']
            assert np.array_equal(accepted['wave'], read_audio(accepted['waveFile'],
                                  accepted['waveFileSha256'], accepted['audioHash']))
        class FailAdjustments:
            specs = renderer.specs
            inventory = renderer.inventory
            calls = 0
            def render(self, synth, params, seed):
                self.calls += 1
                if self.calls > 1:
                    raise OSError('forced DSP failure')
                return renderer.render(synth, params, seed)
        failed = gallery.calibrate_pool([row], target, FailAdjustments(), tmp_path/'failed')
    assert len(failed['originals']) == 1 and not failed['accepted']
    assert failed['calibrations'][0]['status'] == 'render_error'
    assert failed['accounting']['additionalRenderCount'] == 1
    journals = [json.loads(Path(path).read_text()) for path in failed['callJournalFiles']]
    assert journals[-1]['status'] == 'render_error' and journals[-1]['error'] == 'forced DSP failure'


@pytest.mark.parametrize('tamper_call', [1, 2])
def test_end_of_export_audio_tampering_keeps_manifest_incomplete(run_fixture, monkeypatch, tamper_call):
    original = gallery.export_coverage
    calls = []
    def tamper(output, records, metadata):
        calls.append(True)
        result = original(output, records, metadata)
        if len(calls) == tamper_call:
            (output/'001/selected.wav').write_bytes(b'changed')
        return result
    monkeypatch.setattr(gallery, 'export_coverage', tamper)
    with pytest.raises(ValueError, match='binding'):
        gallery.run(output=run_fixture)
    assert json.loads((run_fixture/'manifest.json').read_text())['complete'] is False


def test_unexpected_calibration_failure_reports_consumed_calls(tmp_path, monkeypatch):
    wave = tone()
    row = dict(synth='Bfxr', params={}, seed=1, wave=wave, score=0., provenance={})
    class Renderer:
        specs = {}
        def render(self, synth, params, seed):
            return params, wave
    def broken(candidate, target, renderer, objective):
        renderer.render(candidate['synth'], candidate['params'], candidate['seed'])
        renderer.render(candidate['synth'], candidate['params'], candidate['seed'])
        raise KeyError('unexpected diagnostic bug')
    monkeypatch.setattr(gallery, 'calibrate_candidate', broken)
    with pytest.raises(KeyError, match='unexpected diagnostic bug'):
        gallery.calibrate_pool([row], wave, Renderer(), tmp_path/'pitch')
    report = json.loads((tmp_path/'pitch/report.json').read_text())
    assert report['complete'] is False
    assert report['accounting']['originalValidationReplays'] == 1
    assert report['accounting']['additionalRenderCount'] == 1
    assert len(report['callJournalFiles']) == 2
    assert len(report['failure']['renderCalls']) == 2


def test_code_bindings_include_original_bfxr_inference_dependencies():
    bindings = gallery._code_bindings()
    for name in ('predict.py', 'model.py', 'features_pack.py', 'constants.py'):
        path = ROOT.parent/'invert'/name
        assert bindings['invert/'+name] == file_hash(path)


def test_changed_nested_original_inference_dependency_fails_binding_validation(tmp_path, monkeypatch):
    tools = tmp_path/'tools'
    neural = tools/'neural_invert'; neural.mkdir(parents=True)
    dependency = tools/'invert'/'nested'/'predict.py'
    dependency.parent.mkdir(parents=True)
    dependency.write_text('VERSION = 1\n')
    monkeypatch.setattr(gallery, '__file__', str(neural/'pitch_calibration_gallery.py'))
    # Isolate the imported frozen helper: only the new local augmentation is under test.
    monkeypatch.setattr(gallery, '_shared_code_bindings', lambda: {}, raising=False)
    code_hashes = gallery._code_bindings()
    assert code_hashes['invert/nested/predict.py'] == file_hash(dependency)
    bindings = {}
    for name, digest in code_hashes.items():
        gallery._bind(bindings, tools/name, digest)
    dependency.write_text('VERSION = 2\n')
    assert gallery._code_bindings() != code_hashes
    with pytest.raises(ValueError, match='binding changed'):
        gallery._check_bindings(bindings)
