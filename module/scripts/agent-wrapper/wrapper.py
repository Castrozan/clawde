import argparse
import datetime
import json
import time

from active_hours_override import (
    active_hours_gate_allows_run,
    clear_override,
    override_file_path_for_agent,
    override_is_stale,
    read_override_active_until,
    runtime_root_directory_from_launch_config_path,
)
from redeploy_signals import (
    install_exit_signal_handlers,
    install_redeploy_signal_handler,
    register_current_child_process_id,
)
from launch_session import decide_and_persist_launch_session
from session_store import clear_persisted_session_record
from restart_scheduling import (
    INITIAL_RESTART_DELAY_SECONDS,
    MAXIMUM_RESTART_DELAY_SECONDS,
    is_within_active_hours,
    seconds_until_active_hours_start,
    should_reset_backoff,
)
from session_watchdog import (
    heartbeat_driver_log_path_for_agent,
    run_launch_command_once,
)


def build_tmux_target(tmux_session: str | None, agent_name: str) -> str | None:
    if not tmux_session:
        return None
    return f"{tmux_session}:{agent_name}"


def load_agent_launch_config(config_file_path: str) -> dict:
    with open(config_file_path) as config_file:
        return json.load(config_file)


def supervise_agent_forever(agent_name: str, config_file_path: str) -> None:
    restart_delay_seconds = INITIAL_RESTART_DELAY_SECONDS

    while True:
        try:
            config = load_agent_launch_config(config_file_path)
        except (OSError, ValueError) as config_error:
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                f"Agent {agent_name} could not read launch config "
                f"{config_file_path}: {config_error}. Retrying shortly.",
                flush=True,
            )
            time.sleep(INITIAL_RESTART_DELAY_SECONDS)
            continue

        launch_command = config["launch_command"]
        heartbeat_driver_argv = config.get("heartbeat_driver_argv")
        active_hours_start = config.get("active_hours_start")
        active_hours_end = config.get("active_hours_end")
        daily_session_rotation = config.get("daily_session_rotation", False)
        tmux_target = build_tmux_target(config.get("tmux_session"), agent_name)

        runtime_root_directory = runtime_root_directory_from_launch_config_path(
            config_file_path
        )
        override_file = override_file_path_for_agent(
            runtime_root_directory,
            agent_name,
        )
        heartbeat_driver_log_path = heartbeat_driver_log_path_for_agent(
            runtime_root_directory,
            agent_name,
        )
        override_active_until = read_override_active_until(override_file)
        now = datetime.datetime.now()
        within_active_hours = is_within_active_hours(
            active_hours_start, active_hours_end, now
        )

        if override_is_stale(within_active_hours, override_active_until, now):
            clear_override(override_file)

        if not active_hours_gate_allows_run(
            within_active_hours, override_active_until, now
        ):
            sleep_seconds = seconds_until_active_hours_start(active_hours_start)
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                f"Agent {agent_name} outside active hours. "
                f"Sleeping {sleep_seconds} seconds until {active_hours_start}:00...",
                flush=True,
            )
            time.sleep(sleep_seconds)
            continue

        if not within_active_hours:
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                f"Agent {agent_name} active-hours override in effect until "
                f"{override_active_until.isoformat()}. Running outside normal hours.",
                flush=True,
            )

        launch_session = decide_and_persist_launch_session(
            runtime_root_directory,
            agent_name,
            daily_session_rotation,
        )
        if launch_session.rotating_session:
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                f"Agent {agent_name} daily session rotation. Starting fresh.",
                flush=True,
            )

        runtime_seconds, was_stuck_kill, resume_session_missing = (
            run_launch_command_once(
                launch_command,
                heartbeat_driver_argv,
                tmux_target,
                resume_flag=launch_session.resume_flag,
                register_child_pid=register_current_child_process_id,
                daily_session_rotation=daily_session_rotation,
                heartbeat_driver_log_path=heartbeat_driver_log_path,
                is_resume_launch=launch_session.resume_previous_session,
            )
        )

        if resume_session_missing:
            print(
                f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                f"Agent {agent_name} could not resume its pinned session "
                "(no conversation found); dropping the stale session so the next "
                "launch starts a fresh one.",
                flush=True,
            )
            clear_persisted_session_record(launch_session.session_record_file_path)

        now_after_run = datetime.datetime.now()
        if not active_hours_gate_allows_run(
            is_within_active_hours(active_hours_start, active_hours_end, now_after_run),
            read_override_active_until(override_file),
            now_after_run,
        ):
            continue

        if should_reset_backoff(runtime_seconds, was_stuck_kill):
            restart_delay_seconds = INITIAL_RESTART_DELAY_SECONDS

        print(
            f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
            f"Agent {agent_name} exited after {int(runtime_seconds)} seconds. "
            f"Restarting in {restart_delay_seconds} seconds...",
            flush=True,
        )
        time.sleep(restart_delay_seconds)

        restart_delay_seconds = min(
            restart_delay_seconds * 2, MAXIMUM_RESTART_DELAY_SECONDS
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="clawde-agent-wrapper",
        description="Run a clawde agent launch command in a restart loop with "
        "exponential backoff, re-reading the agent's launch config on every restart "
        "so a deployment's warm restart applies config changes without a full respawn",
    )
    parser.add_argument(
        "--agent-name",
        required=True,
        help="Agent name used in restart log messages and as the tmux window name",
    )
    parser.add_argument(
        "--config-file",
        required=True,
        help="Path to the agent's JSON launch config (launch command, heartbeat "
        "driver argv, active hours, rotation, tmux session), re-read on every restart",
    )
    return parser.parse_args()


def main() -> None:
    install_exit_signal_handlers()
    install_redeploy_signal_handler()
    arguments = parse_arguments()
    supervise_agent_forever(arguments.agent_name, arguments.config_file)


if __name__ == "__main__":
    main()
