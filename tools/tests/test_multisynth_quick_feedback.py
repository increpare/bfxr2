"""Schema-3 choices retain heard evidence without synthesizing scalar ratings."""
import copy
import json

import numpy as np
import pytest
import soundfile as sf

from multisynth.coverage_feedback import export_coverage
from multisynth.listening import retain_feedback
from multisynth.preference import training_pairs
from multisynth.big_run import history


@pytest.fixture
def quick_report(tmp_path):
    report = tmp_path/'run'
    folder = report/'001'
    folder.mkdir(parents=True)
    waves = {}
    candidates = []
    for index, name in enumerate(('target', 'a', 'b', 'c', 'alias')):
        hz = 440 if name in ('target', 'a', 'alias') else 680 if name == 'b' else 1200
        t = np.arange(5000)/44100
        wave = (10000*np.sin(2*np.pi*hz*t)*np.exp(-15*t)).astype('int16')
        sf.write(folder/(name+'.wav'), wave, 44100, subtype='PCM_16')
        waves[name] = wave
        if name != 'target':
            candidates.append({'label':name, 'role':name, 'synth':'fixture', 'params':{'variant':index},
                               'seed':7, 'score':.2, 'sourceHash':'dsp-v1', 'file':name+'.wav',
                               'provenance':{'renderer':'original'}})
    records = [{'folder':'001', 'source':{'name':'coin.wav','path':'original/coin.wav','sha256':'source'},
                'candidates':candidates}]
    model = export_coverage(report, records, {'purpose':'quick-test'})
    feedback = {'schemaVersion':3, **copy.deepcopy(model)}
    target = feedback['targets'][0]
    for c in target['candidates']:
        c.update(likeness=None, usefulness=None)
    ids = [c['id'] for c in target['candidates']]
    target['choice'] = {'protocol':'feel-choice-v1','kind':'best','presentedCandidateIds':ids[:3],
                        'auditionedCandidateIds':ids[:2], 'preferredCandidateIds':[ids[1]]}
    path = tmp_path/'feedback.json'
    return path, report, feedback, waves


def save_archive(quick_report, tmp_path, name='archive'):
    path, report, feedback, _ = quick_report
    path.write_text(json.dumps(feedback))
    output = tmp_path/name
    summary = retain_feedback(path, report, output)
    return output, summary


def test_choice_only_archive_roundtrip_pcm_and_idempotence(quick_report, tmp_path):
    path, report, feedback, waves = quick_report
    output, summary = save_archive(quick_report, tmp_path)
    manifest = json.loads((output/'manifest.json').read_text())
    assert manifest['schemaVersion'] == 3
    assert manifest['targets'][0]['choice'] == feedback['targets'][0]['choice']
    assert (output/'feedback.json').read_bytes() == path.read_bytes()
    assert summary['choices'] == 1 and summary['choiceKinds'] == {'best':1,'tie':0,'none':0,'skip':0}
    assert summary['likenessRatings'] == summary['usefulnessRatings'] == summary['uniqueRatedCandidates'] == 0
    for candidate in manifest['candidates']:
        assert candidate['likeness'] is None and candidate['usefulness'] is None
        pcm, rate = sf.read(output/candidate['audio']['file'], dtype='int16')
        np.testing.assert_array_equal(pcm, waves[candidate['label']])
        assert rate == 44100
    assert retain_feedback(path, report, output) == summary


@pytest.mark.parametrize('change', [
    {'protocol':'unknown'}, {'kind':'unknown'}, {'presentedCandidateIds':[]},
    {'presentedCandidateIds':['foreign']}, {'auditionedCandidateIds':['foreign']},
    {'preferredCandidateIds':['foreign']}, {'preferredCandidateIds':[]},
    {'kind':'tie'}, {'extra':'unknown'}, {'auditionedCandidateIds':'a'},
    {'presentedCandidateIds':[True]},
])
def test_invalid_choices_fail_before_output(quick_report, tmp_path, change):
    path, report, feedback, _ = quick_report
    feedback['targets'][0]['choice'].update(change)
    path.write_text(json.dumps(feedback))
    output = tmp_path/'new-parent'/'archive'
    with pytest.raises(ValueError):
        retain_feedback(path, report, output)
    assert not output.parent.exists()


@pytest.mark.parametrize('field', ['presentedCandidateIds','auditionedCandidateIds','preferredCandidateIds'])
def test_duplicate_choice_ids_fail_before_output(quick_report, tmp_path, field):
    path, report, feedback, _ = quick_report
    choice = feedback['targets'][0]['choice']
    choice[field] = [choice[field][0]]*2
    path.write_text(json.dumps(feedback))
    output = tmp_path/'new-parent'/'archive'
    with pytest.raises(ValueError):
        retain_feedback(path, report, output)
    assert not output.parent.exists()


def test_heard_only_strict_pairs_and_null_scalar_provenance(quick_report, tmp_path):
    output, _ = save_archive(quick_report, tmp_path)
    data = training_pairs([output])
    assert data.x.shape == (1,20) and data.y.tolist() == [1]
    observation = data.observations[0]
    choice = quick_report[2]['targets'][0]['choice']
    assert observation['candidateA'] == choice['preferredCandidateIds'][0]
    assert observation['candidateB'] == choice['auditionedCandidateIds'][0]
    assert observation['labelSource'] == 'direct-choice'
    assert observation['likenessA'] is None and observation['likenessB'] is None
    assert data.summary['directChoicePairs'] == 1


def test_two_heard_alternatives_dedup_identical_pcm(quick_report, tmp_path):
    target = quick_report[2]['targets'][0]
    ids = [c['id'] for c in target['candidates']]
    target['choice']['presentedCandidateIds'] = ids
    target['choice']['auditionedCandidateIds'] = ids
    output, _ = save_archive(quick_report, tmp_path)
    data = training_pairs([output, output])
    assert data.y.tolist() == [1,1]
    assert data.summary['directChoicePairs'] == 2
    assert data.summary['duplicateSessionPairs'] == 2


@pytest.mark.parametrize('kind', ['tie','none','skip'])
def test_non_strict_choices_remain_distinct_and_unlabeled(quick_report, tmp_path, kind):
    target = quick_report[2]['targets'][0]
    target['choice'].update(kind=kind, preferredCandidateIds=[])
    output, summary = save_archive(quick_report, tmp_path)
    data = training_pairs([output])
    assert data.x.shape == (0,20) and data.y.size == 0
    assert data.summary['choices'] == 1 and data.summary['choiceKinds'][kind] == 1
    assert summary['choiceKinds'][kind] == 1


def test_unheard_winner_cannot_generate_preferences(quick_report, tmp_path):
    choice = quick_report[2]['targets'][0]['choice']
    choice['auditionedCandidateIds'] = choice['auditionedCandidateIds'][:1]
    output, _ = save_archive(quick_report, tmp_path)
    assert training_pairs([output]).y.size == 0


def test_explicit_choice_overrides_conflicting_scalar_pair(quick_report, tmp_path):
    target = quick_report[2]['targets'][0]
    target['candidates'][0]['likeness'] = 5
    target['candidates'][1]['likeness'] = 1
    target['candidates'][2]['likeness'] = 3
    output, _ = save_archive(quick_report, tmp_path)
    data = training_pairs([output])
    assert len(data.y) == 3
    assert data.observations[0]['labelSource'] == 'direct-choice'
    assert data.y[0] == 1
    ids = target['choice']['auditionedCandidateIds']
    assert sum(set((o['candidateA'],o['candidateB'])) == set(ids) for o in data.observations) == 1
    assert data.summary['likenessRatings'] == 3


def test_retained_choice_must_exactly_match_raw_feedback(quick_report, tmp_path):
    output, _ = save_archive(quick_report, tmp_path)
    manifest = json.loads((output/'manifest.json').read_text())
    manifest['targets'][0]['choice']['auditionedCandidateIds'].pop()
    (output/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='choice'):
        training_pairs([output])


def test_schema3_null_choice_and_scalar_history_preserved(quick_report, tmp_path):
    target = quick_report[2]['targets'][0]
    target['choice'] = None
    target['candidates'][0]['likeness'] = 4
    output, summary = save_archive(quick_report, tmp_path)
    assert summary['choices'] == 0
    observations = history([output])
    assert [o['rating'] for o in observations['source']] == [4]
    assert observations['source'][0]['candidate']['id'] == target['candidates'][0]['id']


def test_identical_pcm_never_generates_a_strict_choice_pair(quick_report, tmp_path):
    target = quick_report[2]['targets'][0]
    ids = [target['candidates'][i]['id'] for i in (0,3)]
    target['choice'].update(presentedCandidateIds=ids, auditionedCandidateIds=ids,
                            preferredCandidateIds=[ids[0]])
    output, _ = save_archive(quick_report, tmp_path)
    assert training_pairs([output]).y.size == 0


def test_schema3_identity_tamper_rejected_before_output(quick_report, tmp_path):
    path, report, feedback, _ = quick_report
    feedback['targets'][0]['candidates'][0]['id'] = 'foreign'
    path.write_text(json.dumps(feedback))
    output = tmp_path/'new-parent'/'archive'
    with pytest.raises(ValueError, match='identity'):
        retain_feedback(path, report, output)
    assert not output.parent.exists()


def test_schema3_missing_choice_is_valid(quick_report, tmp_path):
    del quick_report[2]['targets'][0]['choice']
    output, summary = save_archive(quick_report, tmp_path)
    assert summary['choices'] == 0
    assert training_pairs([output]).y.size == 0


@pytest.mark.parametrize('tamper', ['usefulness','schemaVersion'])
def test_schema3_manifest_scalar_and_schema_match_raw(quick_report, tmp_path, tamper):
    output, _ = save_archive(quick_report, tmp_path)
    manifest = json.loads((output/'manifest.json').read_text())
    if tamper == 'schemaVersion':
        manifest['schemaVersion'] = 2
    else:
        manifest['candidates'][0]['usefulness'] = 5
    (output/'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match='schema|usefulness'):
        training_pairs([output])


@pytest.mark.parametrize('level', ['very-close','similar','least-bad','not-sure',None])
def test_v2_adequacy_roundtrip_without_scalar_labels(quick_report,tmp_path,level):
    choice=quick_report[2]['targets'][0]['choice']
    choice.update(protocol='feel-choice-v2',adequacy=None if level is None else
                  {'level':level,'candidateIds':choice['preferredCandidateIds'][:]})
    output,summary=save_archive(quick_report,tmp_path)
    manifest=json.loads((output/'manifest.json').read_text())
    assert manifest['targets'][0]['choice']==choice
    assert summary['likenessRatings']==0
    data=training_pairs([output]);assert len(data.y)==1
    assert data.observations[0]['likenessA'] is None


@pytest.mark.parametrize('kind', ['best','tie','none','skip'])
def test_v2_adequacy_scope_is_explicit(quick_report,tmp_path,kind):
    from multisynth.quick_feedback import validate_choice
    choice=quick_report[2]['targets'][0]['choice']
    ids=choice['presentedCandidateIds']
    choice.update(protocol='feel-choice-v2',kind=kind,
                  preferredCandidateIds=[ids[0]] if kind=='best' else [],adequacy=None)
    assessed=[ids[0]] if kind=='best' else ids[:]
    choice['adequacy']={'level':'similar','candidateIds':assessed}
    if kind in ('none','skip'):
        with pytest.raises(ValueError):validate_choice(choice,ids)
    else:
        assert validate_choice(choice,ids)==choice
        choice['adequacy']['candidateIds']=['foreign']
        with pytest.raises(ValueError):validate_choice(choice,ids)


@pytest.mark.parametrize('bad', [{'level':'5','candidateIds':[]},{'level':'similar'},
                               {'level':'similar','candidateIds':[]},{'level':'similar','candidateIds':'x'},
                               {'level':'similar','candidateIds':['x','x']},'very close'])
def test_v2_bad_adequacy_rejected(quick_report,tmp_path,bad):
    choice=quick_report[2]['targets'][0]['choice']
    choice.update(protocol='feel-choice-v2',adequacy=bad)
    with pytest.raises(ValueError):save_archive(quick_report,tmp_path)
