from pathlib import Path

from steward_test_helpers import submodule_status


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


def _fake_git(responses):
    def run_capturing(command, repository, timeout):
        key = " ".join(command)
        for prefix, (code, output) in responses.items():
            if key.startswith(prefix):
                return code, output
        return 1, ""

    return run_capturing


def test_inspect_submodule_populates_the_advance_pin_safety_fields():
    responses = {
        "git rev-parse HEAD:sub": (0, "pinned111"),
        "git rev-parse :sub": (0, "pinned111"),
        "git rev-parse HEAD": (0, "checkout222"),
        "git rev-parse --verify origin/main": (0, "origin333"),
        "git fetch": (0, ""),
        "git status --porcelain": (0, ""),
        "git merge-base": (0, ""),
        "git rev-list --count pinned111..checkout222": (0, "2"),
        "git rev-list --count checkout222..pinned111": (0, "0"),
        "git rev-list --count checkout222..origin/main": (0, "0"),
        "git rev-list --count origin/main..checkout222": (0, "2"),
    }
    report = submodule_status.inspect_submodule(
        _fake_git(responses), Path("/repo"), "sub", "sub", "main"
    )
    assert report["origin_branch_resolved"] is True
    assert report["behind_origin"] == 0
    assert report["action"] == "advance_pin"


def test_inspect_submodule_escalates_when_the_origin_branch_does_not_resolve():
    responses = {
        "git rev-parse HEAD:sub": (0, "pinned111"),
        "git rev-parse :sub": (0, "pinned111"),
        "git rev-parse HEAD": (0, "checkout222"),
        "git rev-parse --verify origin/main": (128, ""),
        "git fetch": (0, ""),
        "git status --porcelain": (0, ""),
        "git merge-base": (1, ""),
        "git rev-list --count pinned111..checkout222": (0, "2"),
        "git rev-list --count checkout222..pinned111": (0, "0"),
    }
    report = submodule_status.inspect_submodule(
        _fake_git(responses), Path("/repo"), "sub", "sub", "main"
    )
    assert report["origin_branch_resolved"] is False
    assert report["action"] == "escalate_stranded"


def test_inspect_submodule_replays_a_checkout_that_diverged_from_its_own_remote():
    responses = {
        "git rev-parse HEAD:sub": (0, "pinned111"),
        "git rev-parse :sub": (0, "pinned111"),
        "git rev-parse HEAD": (0, "checkout222"),
        "git rev-parse --verify origin/main": (0, "origin333"),
        "git fetch": (0, ""),
        "git status --porcelain": (0, ""),
        "git merge-base": (0, ""),
        "git rev-list --count pinned111..checkout222": (0, "17"),
        "git rev-list --count checkout222..pinned111": (0, "1"),
        "git rev-list --count checkout222..origin/main": (0, "1"),
        "git rev-list --count origin/main..checkout222": (0, "17"),
    }
    report = submodule_status.inspect_submodule(
        _fake_git(responses), Path("/repo"), "sub", "sub", "main"
    )
    assert report["nonff_vs_origin"] is True
    assert report["action"] == "rebase_onto_origin"


def test_report_flags_an_advance_pin_action(monkeypatch):
    monkeypatch.setattr(
        submodule_status, "configured_submodules", lambda run, repo: [("a", "a")]
    )
    monkeypatch.setattr(
        submodule_status, "configured_branch", lambda run, repo, name: "main"
    )
    monkeypatch.setattr(
        submodule_status,
        "inspect_submodule",
        lambda run, repo, name, path, branch: {"name": name, "action": "advance_pin"},
    )

    report = submodule_status.submodule_report(lambda *a: (0, ""), Path("/repo"))
    assert report["needs_pin_advance"] is True
    assert report["submodule_divergence"] is False


def test_report_flags_a_rebase_onto_origin_action_without_escalating(monkeypatch):
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
            "action": "rebase_onto_origin",
        },
    )

    report = submodule_status.submodule_report(lambda *a: (0, ""), Path("/repo"))
    assert report["needs_submodule_rebase"] is True
    assert report["submodule_divergence"] is False
    assert report["needs_pin_advance"] is False
