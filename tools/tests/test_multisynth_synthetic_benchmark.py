import json

import numpy as np
import pytest

from multisynth.synthetic_benchmark import (
    HoldoutIndex, generate_targets, parameter_key, scope_indices, stable_seed, summarize,
)


def row(synth='Bfxr', value=.2, preset='coin', backend='legacy', pcm='bank-pcm', seed=7):
    return dict(synth=synth, params={'value':value}, preset=preset, backend=backend,
                auditionPcmSha256=pcm, seed=seed)


def test_holdout_rejects_parameters_independent_of_render_seed_and_backend():
    bank = [row()]
    index = HoldoutIndex(bank)
    assert index.reason('Bfxr', {'value':.2}, 'different-audio') == 'canonical_parameters_present_ignoring_render_seed'
    assert index.reason('Clonkr', {'value':.9}, 'bank-pcm') == 'normalized_audition_pcm_present'
    assert index.reason('Bfxr', {'value':.9}, 'new-audio') is None
    index.add('Bfxr', {'value':.9}, 'new-audio')
    assert index.reason('Bfxr', {'value':.9}, 'third-audio')
    assert parameter_key('Bfxr', {'a':1,'b':2}) == parameter_key('Bfxr', {'b':2,'a':1})
    with pytest.raises(ValueError, match='PCM hash'):
        HoldoutIndex([{'synth':'Bfxr','params':{}}])


def test_holdout_also_rejects_soundboard_constituent_parameters():
    board = row(synth='Soundboard', backend='board')
    board['params'] = {'sources':json.dumps([{'synth':'Bfxr','params':{'value':.8},'renderSeed':.2}])}
    assert HoldoutIndex([board]).reason('Bfxr', {'value':.8}, 'unique')


def test_scope_conditions_keep_labels_out_of_unrestricted_search_and_avoid_board_aliases():
    target = row(value=.7, pcm='target')
    bank = [row(), row(value=.3,preset='laser'), row(synth='Clonkr'),
            row(synth='Soundboard',backend='board'), row(value=.7,seed=999),
            row(synth='Jinglr',pcm='target')]
    bank[3]['params'] = {'sources':'[]'}
    assert scope_indices(bank,target,'known_engine').tolist() == [0,1]
    assert scope_indices(bank,target,'unrestricted').tolist() == [0,1,2,3]
    assert scope_indices(bank,target,'leave_preset_out').tolist() == [1,2]
    # Engine/preset tags do not filter the automatic condition (aside from exact leakage).
    alternate = {**target,'synth':'Other','preset':'other'}
    assert scope_indices(bank,alternate,'unrestricted').tolist() == [0,1,2,3,4]
    with pytest.raises(ValueError,match='Unknown'):
        scope_indices(bank,target,'unknown')


class FakeRenderer:
    inventory = {'sourceHash':'test-source'}
    specs = {'A':{'collectionCompatible':True,'presets':['one','two','three']},
             'B':{'collectionCompatible':True,'presets':['one','two']},
             'Retired':{'collectionCompatible':False,'presets':['one']}}

    def sample(self,synth,preset,seed):
        return {'value':seed,'preset':preset}

    def render(self,synth,params,seed):
        wave = np.array([params['value'],seed],dtype='float64')
        return params,wave


def test_balanced_targets_are_deterministic_distinct_and_have_separate_seeds(monkeypatch):
    import multisynth.synthetic_benchmark as benchmark
    monkeypatch.setattr(benchmark,'audition_hash',lambda wave: str(tuple(wave)))
    a, rejected, engines = generate_targets(FakeRenderer(),[], 'fixed',recipes=2,samples=2)
    b, _, _ = generate_targets(FakeRenderer(),[], 'fixed',recipes=2,samples=2)
    assert a == b and rejected == [] and engines == ['A','B']
    assert len(a) == 8
    assert all(t['seed'] != t['samplingSeed'] for t in a)
    assert len({t['auditionPcmSha256'] for t in a}) == 8
    for engine in engines:
        group = [t for t in a if t['synth']==engine]
        assert len(group)==4 and len({t['preset'] for t in group})==2
    first = a[0]
    bank = [{'synth':first['synth'],'params':first['params'],'seed':999,
             'auditionPcmSha256':'not-the-target'}]
    replaced, rejected, _ = generate_targets(FakeRenderer(),bank,'fixed',recipes=2,samples=2)
    assert replaced[0]['params'] != first['params']
    assert rejected[0]['reason'] == 'canonical_parameters_present_ignoring_render_seed'
    assert rejected[0]['params'] == first['params']
    smoke, _, _ = generate_targets(FakeRenderer(),[], 'fixed',limit=1)
    assert len(smoke)==1
    assert stable_seed('a','b') == stable_seed('a','b') != stable_seed('b','a')


def test_summary_reports_per_engine_auditory_before_after_and_selector_ties():
    def selector(before,after,same):
        return {'before':{'auditoryV1':before},'after':{'auditoryV1':after},'sameSourceEngine':same}
    records = [{'target':{'synth':'A'},'conditions':{'unrestricted':{
        'selectors':{'v4':selector(2,1,True),'v5':selector(3,.5,False)}}}},
        {'target':{'synth':'B'},'conditions':{'unrestricted':{
        'selectors':{'v4':selector(2,1,False),'v5':selector(2,1,True)}}}}]
    summary = summarize(records)
    aggregate = summary['aggregate']['unrestricted']
    assert aggregate['v5']['meanAuditoryV1After'] == .75
    assert aggregate['v5']['sameSourceEngine'] == 1
    assert aggregate['auditoryV1Comparison'] == {'v5Lower':1,'ties':1,'v4Lower':0}
    assert set(summary['perEngine']) == {'A','B'}
    assert summarize([]) == {'aggregate':{},'perEngine':{}}


def test_single_generator_engine_keeps_equal_target_count_and_exhaustion_is_diagnostic(monkeypatch):
    import multisynth.synthetic_benchmark as benchmark
    monkeypatch.setattr(benchmark,'audition_hash',lambda wave: str(tuple(wave)))
    renderer = FakeRenderer()
    renderer.specs = {'Footsteppr':{'collectionCompatible':True,'presets':['randomize_params']}}
    targets, _, _ = generate_targets(renderer,[],'single',recipes=2,samples=2)
    assert len(targets)==4
    assert {t['preset'] for t in targets} == {'randomize_params'}
    monkeypatch.setattr(benchmark,'audition_hash',lambda wave: 'identical-audio')
    with pytest.raises(benchmark.TargetGenerationError) as caught:
        generate_targets(renderer,[],'single',recipes=2,samples=2,attempts=2)
    assert any(r['reason']=='attempt_limit_exhausted' for r in caught.value.rejected)
    assert caught.value.targets == []


def test_metric_factory_isolates_mutable_target_caches_between_threads(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier
    import multisynth.synthetic_benchmark as benchmark

    class CachingMetric:
        def __init__(self, path):
            self.path = path
            self._target = None

        @classmethod
        def load(cls, path):
            return cls(path)

    monkeypatch.setattr(benchmark, 'PerceptualMetric', CachingMetric)
    monkeypatch.setattr(benchmark, 'V4Metric', CachingMetric)
    barrier = Barrier(2)

    def worker(target):
        metrics = benchmark.load_metrics('frozen-v5.json', 'frozen-v4.json')
        for metric in metrics:
            metric._target = target
        barrier.wait(timeout=5)
        # Shared scorers would now expose the other reference in one worker.
        assert [m._target for m in metrics] == [target, target]
        return metrics

    with ThreadPoolExecutor(max_workers=2) as executor:
        first, second = list(executor.map(worker, ['reference-a', 'reference-b']))
    assert first[0] is not second[0] and first[1] is not second[1]
    assert [m.path for m in first] == ['frozen-v5.json', 'frozen-v4.json']


def test_replayed_candidate_replaces_ancestral_pcm_hash_without_changing_library():
    from multisynth.synthetic_benchmark import replayed_candidate
    original = row(pcm='cached-ancestor')
    canonical = {'value':.9}
    result = replayed_candidate(original,canonical,'actual-replay')
    assert result['auditionPcmSha256'] == 'actual-replay'
    assert result['params'] == canonical
    assert original['auditionPcmSha256'] == 'cached-ancestor'
    assert original['params'] == {'value':.2}
    canonical['value'] = 0
    assert result['params'] == {'value':.9}
