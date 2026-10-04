"""Validation for explicit ordinal listening choices; no scalar labels inferred."""

CHOICE_KINDS = ('best', 'tie', 'none', 'skip')
CHOICE_FIELDS = {'protocol', 'kind', 'presentedCandidateIds', 'auditionedCandidateIds',
                 'preferredCandidateIds'}


def validate_choice(choice, candidate_ids):
    """Validate target-local evidence and return the original choice unchanged."""
    if choice is None:
        return None
    if (not isinstance(choice, dict) or set(choice) != CHOICE_FIELDS
            or choice.get('protocol') != 'feel-choice-v1'
            or choice.get('kind') not in CHOICE_KINDS):
        raise ValueError('Invalid listening choice protocol, kind or fields')
    for field in ('presentedCandidateIds', 'auditionedCandidateIds', 'preferredCandidateIds'):
        ids = choice[field]
        if (not isinstance(ids, list) or any(not isinstance(cid, str) for cid in ids)
                or len(ids) != len(set(ids))):
            raise ValueError('Listening choice IDs must be distinct strings')
    presented = set(choice['presentedCandidateIds'])
    if not 1 <= len(presented) <= 5 or not presented <= set(candidate_ids):
        raise ValueError('Listening choice presented IDs differ from target candidates')
    if not set(choice['auditionedCandidateIds']) <= presented:
        raise ValueError('Listening choice auditioned IDs were not presented')
    preferred = choice['preferredCandidateIds']
    if (len(preferred) != (1 if choice['kind'] == 'best' else 0)
            or not set(preferred) <= presented):
        raise ValueError('Listening choice preferred IDs do not match its kind or presented set')
    return choice


def choice_counts(choices):
    counts = dict.fromkeys(CHOICE_KINDS, 0)
    for choice in choices:
        if choice is not None:
            counts[choice['kind']] += 1
    return {'choices':sum(counts.values()), 'choiceKinds':counts}
