"""The automatic daily gate (spec Section 1 / Gate A step 1).

Failures are reported by probe ID, never averaged into a median distance.
"""
import pytest

from match.structure_probes import PASS_THRESHOLD, PROBES, STRUCTURE_IDS, evaluate


@pytest.fixture(scope="module")
def results():
    return {r.id: r for r in evaluate()}


def test_every_family_has_a_case():
    families = {p.family for p in PROBES}
    assert families == {
        "notes_2_up", "notes_2_down", "notes_3_arp", "gliss_up", "gliss_down",
        "dir_flip", "mute_tail", "noise_onset",
    }


def test_suite_pass_rate(results):
    failed = sorted(r.id for r in results.values() if not r.passed)
    n_pass = len(results) - len(failed)
    assert n_pass >= PASS_THRESHOLD, (
        f"{n_pass}/{len(results)} probes pass "
        f"(need {PASS_THRESHOLD}); failed: {failed}"
    )


@pytest.mark.parametrize("probe_id", STRUCTURE_IDS)
def test_structure_probe_passes(results, probe_id):
    """The six cases that fail against the pre-structure-term objective."""
    r = results[probe_id]
    assert r.passed, f"{probe_id}: good={r.good:.3f} not < bad={r.bad:.3f}"
