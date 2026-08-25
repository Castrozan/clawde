import sidecar_process_reconcile

AGENT_NAME = "bridged-agent"
SIDECAR_NAME = "bridged-agent-discord"


def make_sidecar_specification(tmp_path, command="true"):
    return {
        "name": SIDECAR_NAME,
        "command": command,
        "process_match_pattern": (
            f"bridge.py --agent-name {AGENT_NAME} --one-shot-turn-command"
        ),
        "log_file": str(tmp_path / "sidecar-logs" / f"{SIDECAR_NAME}.log"),
    }


def make_sidecar_specification_with_lifetime(tmp_path, lifetime, enabled=True):
    return {
        **make_sidecar_specification(tmp_path),
        "enabled": enabled,
        "lifetime": lifetime,
    }


def record_the_sidecar_as_launched_from_its_current_command(specification):
    sidecar_process_reconcile.record_spawned_command(specification)
    return specification


def make_session_specification(tmp_path):
    return {
        "name": "clawde",
        "agents": [
            {
                "name": AGENT_NAME,
                "wrapper_command": "exec true",
                "sidecar_processes": [make_sidecar_specification(tmp_path)],
            }
        ],
    }


def record_process_lookups(monkeypatch, live_process_ids):
    spawned_specifications = []
    terminated_process_ids = []
    monkeypatch.setattr(
        sidecar_process_reconcile,
        "find_sidecar_process_ids",
        lambda _pattern: list(live_process_ids),
    )
    monkeypatch.setattr(
        sidecar_process_reconcile,
        "spawn_sidecar_process",
        spawned_specifications.append,
    )
    monkeypatch.setattr(
        sidecar_process_reconcile,
        "terminate_sidecar_process",
        terminated_process_ids.append,
    )
    monkeypatch.setattr(
        sidecar_process_reconcile,
        "wait_for_process_to_exit",
        lambda _process_id: None,
    )
    return spawned_specifications, terminated_process_ids
