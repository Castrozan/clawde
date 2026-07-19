from pathlib import Path

SUBMODULE_FETCH_TIMEOUT_SECONDS = 45


def git_output(run_capturing, repository: Path, *git_arguments: str) -> str:
    return_code, output = run_capturing(["git", *git_arguments], repository, 20)
    return output if return_code == 0 else ""


def git_command_succeeds(run_capturing, repository: Path, *git_arguments: str) -> bool:
    return_code, _ = run_capturing(["git", *git_arguments], repository, 20)
    return return_code == 0


def commit_count_in_range(run_capturing, repository: Path, revision_range: str) -> int:
    text = git_output(run_capturing, repository, "rev-list", "--count", revision_range)
    return int(text) if text.isdigit() else 0


def configured_submodules(run_capturing, repository: Path) -> list[tuple[str, str]]:
    listing = git_output(
        run_capturing,
        repository,
        "config",
        "--file",
        ".gitmodules",
        "--get-regexp",
        r"^submodule\..*\.path$",
    )
    submodules = []
    for line in listing.splitlines():
        key, _, path = line.partition(" ")
        name = key[len("submodule.") : -len(".path")]
        if name and path:
            submodules.append((name, path))
    return submodules


def configured_branch(run_capturing, repository: Path, name: str) -> str:
    branch = git_output(
        run_capturing,
        repository,
        "config",
        "--file",
        ".gitmodules",
        f"submodule.{name}.branch",
    )
    return branch or "main"


def pin_can_be_advanced_safely(report: dict) -> bool:
    return (
        report["ahead_of_pinned"] > 0
        and report["behind_pinned"] == 0
        and report["origin_branch_resolved"]
        and not report["nonff_vs_origin"]
    )


def classify_submodule(report: dict) -> str:
    if not report["initialized"]:
        return "init"
    if report["dirty"]:
        return "escalate_dirty"
    if report["ahead_of_pinned"] > 0:
        if pin_can_be_advanced_safely(report):
            return "advance_pin"
        return "escalate_stranded"
    if report["drifted"]:
        return "sync"
    if report["pinned_unpushed"]:
        return "push"
    return "clean"


def inspect_submodule(
    run_capturing, repository: Path, name: str, path: str, branch: str
) -> dict:
    submodule_directory = repository / path
    pinned = git_output(run_capturing, repository, "rev-parse", f"HEAD:{path}")
    index_pin = git_output(run_capturing, repository, "rev-parse", f":{path}")
    checked_out = git_output(run_capturing, submodule_directory, "rev-parse", "HEAD")

    base = {
        "name": name,
        "path": path,
        "branch": branch,
        "pinned": pinned,
        "index_pin": index_pin,
        "checked_out": checked_out,
    }

    if not checked_out:
        base.update(
            initialized=False,
            dirty=False,
            pinned_unpushed=False,
            drifted=True,
            ahead_of_pinned=0,
            behind_pinned=0,
            nonff_vs_origin=False,
            behind_origin=0,
            origin_branch_resolved=False,
            pointer_uncommitted=index_pin != pinned,
        )
        base["action"] = classify_submodule(base)
        return base

    run_capturing(
        ["git", "fetch", "--quiet", "origin"],
        submodule_directory,
        SUBMODULE_FETCH_TIMEOUT_SECONDS,
    )
    origin_branch = f"origin/{branch}"
    origin_branch_resolved = git_command_succeeds(
        run_capturing, submodule_directory, "rev-parse", "--verify", origin_branch
    )
    dirty = bool(
        git_output(run_capturing, submodule_directory, "status", "--porcelain")
    )
    pinned_on_origin = bool(pinned) and git_command_succeeds(
        run_capturing,
        submodule_directory,
        "merge-base",
        "--is-ancestor",
        pinned,
        origin_branch,
    )
    ahead_of_pinned = (
        commit_count_in_range(
            run_capturing, submodule_directory, f"{pinned}..{checked_out}"
        )
        if pinned
        else 0
    )
    behind_pinned = (
        commit_count_in_range(
            run_capturing, submodule_directory, f"{checked_out}..{pinned}"
        )
        if pinned
        else 0
    )
    behind_origin = commit_count_in_range(
        run_capturing, submodule_directory, f"{checked_out}..{origin_branch}"
    )
    ahead_origin = commit_count_in_range(
        run_capturing, submodule_directory, f"{origin_branch}..{checked_out}"
    )

    base.update(
        initialized=True,
        dirty=dirty,
        pinned_unpushed=bool(pinned) and not pinned_on_origin,
        drifted=checked_out != pinned,
        ahead_of_pinned=ahead_of_pinned,
        behind_pinned=behind_pinned,
        nonff_vs_origin=behind_origin > 0 and ahead_origin > 0,
        behind_origin=behind_origin,
        origin_branch_resolved=origin_branch_resolved,
        pointer_uncommitted=index_pin != pinned,
    )
    base["action"] = classify_submodule(base)
    return base


def submodule_report(run_capturing, repository: Path) -> dict:
    submodules = [
        inspect_submodule(
            run_capturing,
            repository,
            name,
            path,
            configured_branch(run_capturing, repository, name),
        )
        for name, path in configured_submodules(run_capturing, repository)
    ]
    actions = {submodule["action"] for submodule in submodules}
    return {
        "submodules": submodules,
        "needs_submodule_sync": bool(actions & {"init", "sync"}),
        "needs_submodule_push": "push" in actions,
        "needs_pin_advance": "advance_pin" in actions,
        "submodule_divergence": bool(actions & {"escalate_dirty", "escalate_stranded"}),
    }
