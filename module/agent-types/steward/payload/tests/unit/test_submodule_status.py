from pathlib import Path

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


def test_commits_ahead_of_pinned_escalate_when_they_cannot_fast_forward_origin():
    state = submodule_state(ahead_of_pinned=2, drifted=True, nonff_vs_origin=True)
    assert submodule_status.classify_submodule(state) == "escalate_stranded"


def test_commits_ahead_of_pinned_escalate_when_the_checkout_trails_origin():
    state = submodule_state(ahead_of_pinned=2, drifted=True, behind_origin=3)
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


def test_configured_submodules_parses_gitmodules(monkeypatch):
    listing = "submodule.private-config.path private-config\nsubmodule.vendor.path third/vendor"

    def fake_run(arguments, working_directory, timeout_seconds):
        return 0, listing

    parsed = submodule_status.configured_submodules(fake_run, Path("/repo"))
    assert parsed == [("private-config", "private-config"), ("vendor", "third/vendor")]


def test_report_flags_aggregate_actions(monkeypatch):
    monkeypatch.setattr(
        submodule_status,
        "configured_submodules",
        lambda run, repo: [("a", "a"), ("b", "b")],
    )
    monkeypatch.setattr(
        submodule_status, "configured_branch", lambda run, repo, name: "main"
    )
    actions = {"a": "push", "b": "clean"}
    monkeypatch.setattr(
        submodule_status,
        "inspect_submodule",
        lambda run, repo, name, path, branch: {"name": name, "action": actions[name]},
    )

    report = submodule_status.submodule_report(lambda *a: (0, ""), Path("/repo"))
    assert report["needs_submodule_push"] is True
    assert report["needs_submodule_sync"] is False
    assert report["submodule_divergence"] is False


def test_report_flags_detect_divergence(monkeypatch):
    monkeypatch.setattr(
        submodule_status, "configured_submodules", lambda run, repo: [("a", "a")]
    )
    monkeypatch.setattr(
        submodule_status, "configured_branch", lambda run, repo, name: "main"
    )
    monkeypatch.setattr(
        submodule_status,
        "inspect_submodule",
        lambda run, repo, name, path, branch: {
            "name": name,
            "action": "escalate_stranded",
        },
    )

    report = submodule_status.submodule_report(lambda *a: (0, ""), Path("/repo"))
    assert report["submodule_divergence"] is True
