from multisynth.big_run import latest_best, candidate_key


def test_baseline_uses_latest_judgment_for_repeated_audio():
    observations=[{'candidate':{'audio':{'pcmSha256':'a'}},'rating':4,'session':0},
                  {'candidate':{'audio':{'pcmSha256':'a'}},'rating':1,'session':2},
                  {'candidate':{'audio':{'pcmSha256':'b'}},'rating':3,'session':1}]
    assert latest_best(observations)['candidate']['audio']['pcmSha256']=='b'


def test_candidate_identity_includes_backend_seed_and_parameters():
    a={'backend':'legacy','synth':'Bfxr','seed':7,'params':{'pitch':.4}}
    assert candidate_key(a)!=candidate_key({**a,'seed':8})
    assert candidate_key(a)!=candidate_key({**a,'backend':'board'})
    assert candidate_key(a)==candidate_key({**a,'score':123})
