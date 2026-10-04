from pathlib import Path


def test_recent_direct_winners_become_exact_previous_baselines():
    from neural_invert.experiment import listening_history, previous_best
    root=Path(__file__).resolve().parents[1]/'multisynth/listening_data'
    archive=root/'2026-10-04-neural-v1-quick-01'
    rows=listening_history([archive])
    sources=[r for key, r in rows.items() if not key.startswith('pcm:')]
    assert len(sources)==4  # The none-close reference has no fabricated winner.
    for observations in sources:
        winner=previous_best(observations)
        assert winner['labelSource']=='direct-choice'
        assert winner['rating'] is None
        assert winner['candidate']['id'] in winner['target']['choice']['preferredCandidateIds']
        assert winner['candidate']['id'] in winner['target']['choice']['auditionedCandidateIds']
        assert winner['candidate']['audio']['pcmSha256']


def test_direct_preference_is_not_converted_to_a_scalar_rating():
    from neural_invert.experiment import previous_best
    scalar={'session':0,'rating':5,'candidate':{'audio':{'pcmSha256':'a'}}}
    choice={'session':1,'rating':None,'labelSource':'direct-choice','candidate':{'audio':{'pcmSha256':'b'}}}
    assert previous_best([scalar,choice]) is choice
    assert previous_best([scalar]) is scalar
    newer={**scalar,'session':2,'rating':3}
    assert previous_best([scalar,choice,newer]) is newer
    newer_distinct={**newer,'candidate':{'audio':{'pcmSha256':'c'}}}
    assert previous_best([scalar,choice,newer_distinct]) is scalar
