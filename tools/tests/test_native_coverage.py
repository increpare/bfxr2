def test_group_assignment_preserves_holdouts_and_duplicate_membership():
    from neural_invert.coverage_data import assign_new_groups
    hashes=['old-train','old-val','probe','new-a','new-a','new-b']
    a=assign_new_groups(hashes,{'old-train'},{'old-val'},{'probe'})
    assert a[0]=='train' and a[1]=='reserved' and a[2]=='reserved'
    assert a[3]==a[4] and a[3] in ('train','val')
    b=assign_new_groups(list(reversed(hashes)),{'old-train'},{'old-val'},{'probe'})
    assert a==list(reversed(b))


def test_overlapping_original_splits_are_rejected():
    import pytest
    from neural_invert.coverage_data import assign_new_groups
    with pytest.raises(ValueError):assign_new_groups(['x'],{'x'},{'x'},set())


def test_balanced_sampling_keeps_structured_sequence_when_native_pool_changes():
    import torch
    from neural_invert.coverage_train import balanced_batch
    def generators():return [torch.Generator().manual_seed(s) for s in (12,13)]
    a=balanced_batch(torch.arange(10),torch.arange(100,110),8,generators())
    b=balanced_batch(torch.arange(40),torch.arange(100,110),8,generators())
    assert (a[:4]<10).all() and (b[:4]<40).all()
    torch.testing.assert_close(a[4:],b[4:]);assert (a[4:]>=100).all()
