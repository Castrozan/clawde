from clawde_service_test_helpers import FakeCompletedProcess, load_service_module

service_module = load_service_module()


def _process_listing(command_lines_by_process_id, noise_lines=()):
    lines = [
        f"  {process_id} {command_line}"
        for process_id, command_line in command_lines_by_process_id.items()
    ]
    lines.extend(noise_lines)
    return "\n".join(lines) + "\n"


def test_find_wrapper_processes_filters_by_session_and_parses_agent_name(monkeypatch):
    command_lines_by_process_id = {
        111: "python3 /n/agent-wrapper/wrapper.py --agent-name steward "
        "--config-file /c/steward.json",
        222: "python3 /n/agent-wrapper/wrapper.py --agent-name copper "
        "--config-file /c/copper.json",
        333: "python3 /n/agent-wrapper/wrapper.py --agent-name bronze "
        "--config-file /c/bronze.json",
    }
    tmux_session_by_config_file_path = {
        "/c/steward.json": "clawde",
        "/c/copper.json": "copper",
        "/c/bronze.json": "clawde",
    }

    def fake_subprocess_run(arguments, capture_output, text):
        assert arguments[0] == "ps"
        return FakeCompletedProcess(
            0,
            stdout=_process_listing(
                command_lines_by_process_id,
                noise_lines=["  999 vim /n/agent-wrapper/wrapper.py"],
            ),
        )

    monkeypatch.setattr(
        service_module.agent_wrapper_reconcile.subprocess, "run", fake_subprocess_run
    )
    monkeypatch.setattr(
        service_module.agent_wrapper_reconcile,
        "read_tmux_session_from_launch_config",
        lambda config_file_path: tmux_session_by_config_file_path[config_file_path],
    )

    discovered = (
        service_module.agent_wrapper_reconcile.find_session_agent_wrapper_processes(
            "clawde"
        )
    )

    assert discovered == [
        {"process_id": 111, "agent_name": "steward"},
        {"process_id": 333, "agent_name": "bronze"},
    ], (
        "discovery must return only wrappers whose --config-file declares tmux_session "
        "'clawde', so reconciling one session never terminates another session's agents"
    )


def test_find_wrapper_processes_issues_a_single_process_scan_regardless_of_count(
    monkeypatch,
):
    command_lines_by_process_id = {
        111: "python3 /n/agent-wrapper/wrapper.py --agent-name steward "
        "--config-file /c/steward.json",
        222: "python3 /n/agent-wrapper/wrapper.py --agent-name cobalt "
        "--config-file /c/cobalt.json",
        333: "python3 /n/agent-wrapper/wrapper.py --agent-name bronze "
        "--config-file /c/bronze.json",
    }
    subprocess_run_call_count = {"count": 0}

    def fake_subprocess_run(arguments, capture_output, text):
        subprocess_run_call_count["count"] += 1
        return FakeCompletedProcess(
            0, stdout=_process_listing(command_lines_by_process_id)
        )

    monkeypatch.setattr(
        service_module.agent_wrapper_reconcile.subprocess, "run", fake_subprocess_run
    )
    monkeypatch.setattr(
        service_module.agent_wrapper_reconcile,
        "read_tmux_session_from_launch_config",
        lambda _config_file_path: "clawde",
    )

    service_module.agent_wrapper_reconcile.find_session_agent_wrapper_processes(
        "clawde"
    )

    assert subprocess_run_call_count["count"] == 1, (
        "discovery must scan all processes in a single ps call instead of one pgrep "
        "plus one ps per matched pid, so per-cycle subprocess forks stay constant in "
        "the number of running wrappers"
    )
