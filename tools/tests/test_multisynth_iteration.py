import json

import pytest

from multisynth.iterate import select_batch


def test_frozen_batch_checks_missing_tags_duplicate_paths_and_source_hash(tmp_path):
    import hashlib
    source = tmp_path/'sound.wav'
    source.write_bytes(b'original')
    item = {'tag':'hit','path':str(source),'sha256':hashlib.sha256(b'original').hexdigest()}
    manifest = tmp_path/'targets.json'
    manifest.write_text(json.dumps({'targets':[item]}))
    assert select_batch(manifest,['hit']) == [item]
    with pytest.raises(ValueError,match='Missing tags'):
        select_batch(manifest,['laser'])
    source.write_bytes(b'changed')
    with pytest.raises(ValueError,match='changed'):
        select_batch(manifest,['hit'])
