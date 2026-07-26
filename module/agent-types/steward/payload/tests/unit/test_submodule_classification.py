from steward_test_helpers import submodule_status


def submodule_state(**overrides) -> dict:
    base = {
        "initialized": True,
        "dirty": False,
        "ahead_of_pinned": 0,
        "behind_pinned": 0,
        "drifted": False,
        "pinned_unpushed": False,
        "nonff_vs_origin": False,
        "behind_origin": 0,
        "origin_branch_resolved": True,
    }
    base.update(overrides)
    return base


def test_uninitialized_submodule_needs_init():
    assert (
        submodule_status.classify_submodule(submodule_state(initialized=False))
        == "init"
    )


def test_dirty_submodule_escalates():
    assert (
        submodule_status.classify_submodule(submodule_state(dirty=True))
        == "escalate_dirty"
    )


def test_clean_fast_forward_commits_ahead_of_pinned_advance_the_pin():
    state = submodule_state(ahead_of_pinned=2, drifted=True)
    assert submodule_status.classify_submodule(state) == "advance_pin"


def test_commits_ahead_of_pinned_replay_onto_origin_when_they_cannot_fast_forward_it():
    state = submodule_state(
        ahead_of_pinned=2, drifted=True, nonff_vs_origin=True, behind_origin=1
    )
    assert submodule_status.classify_submodule(state) == "rebase_onto_origin"


def test_a_checkout_both_ahead_of_and_behind_its_pin_still_replays_onto_origin():
    state = submodule_state(
        ahead_of_pinned=17,
        behind_pinned=1,
        drifted=True,
        nonff_vs_origin=True,
        behind_origin=1,
    )
    assert submodule_status.classify_submodule(state) == "rebase_onto_origin"


def test_a_dirty_submodule_escalates_instead_of_replaying_onto_origin():
    state = submodule_state(
        ahead_of_pinned=2,
        drifted=True,
        nonff_vs_origin=True,
        behind_origin=1,
        dirty=True,
    )
    assert submodule_status.classify_submodule(state) == "escalate_dirty"


def test_an_unresolvable_origin_branch_escalates_instead_of_replaying():
    state = submodule_state(
        ahead_of_pinned=2,
        drifted=True,
        nonff_vs_origin=True,
        behind_origin=1,
        origin_branch_resolved=False,
    )
    assert submodule_status.classify_submodule(state) == "escalate_stranded"


def test_a_checkout_already_contained_in_origin_still_advances_the_pin():
    state = submodule_state(ahead_of_pinned=2, drifted=True, behind_origin=3)
    assert submodule_status.classify_submodule(state) == "advance_pin"


def test_an_unresolvable_origin_branch_escalates_instead_of_advancing():
    state = submodule_state(
        ahead_of_pinned=2, drifted=True, origin_branch_resolved=False
    )
    assert submodule_status.classify_submodule(state) == "escalate_stranded"


def test_commits_ahead_of_pinned_escalate_when_the_checkout_also_trails_the_pin():
    state = submodule_state(ahead_of_pinned=2, behind_pinned=1, drifted=True)
    assert submodule_status.classify_submodule(state) == "escalate_stranded"


def test_a_dirty_submodule_still_escalates_over_advancing_the_pin():
    state = submodule_state(ahead_of_pinned=2, drifted=True, dirty=True)
    assert submodule_status.classify_submodule(state) == "escalate_dirty"


def test_checked_out_behind_pinned_is_a_safe_sync():
    state = submodule_state(drifted=True, behind_pinned=1)
    assert submodule_status.classify_submodule(state) == "sync"


def test_pinned_commit_absent_from_origin_needs_push():
    assert (
        submodule_status.classify_submodule(submodule_state(pinned_unpushed=True))
        == "push"
    )


def test_consistent_submodule_is_clean():
    assert submodule_status.classify_submodule(submodule_state()) == "clean"


def test_dirty_outranks_stranded_and_push():
    state = submodule_state(dirty=True, ahead_of_pinned=3, pinned_unpushed=True)
    assert submodule_status.classify_submodule(state) == "escalate_dirty"
