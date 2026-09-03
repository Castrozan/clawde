import datetime
import time

from active_hours_override import (
    active_hours_gate_allows_run,
    read_override_active_until,
)
from agent_log import emit_timestamped_log
from harness_productivity_record import (
    harness_productivity_record_path,
    judge_pending_delivery,
)
from launch_gate import run_launch_command_to_completion
from launch_session import decide_and_persist_launch_session
from redeploy_signals import register_current_child_process_id
from restart_scheduling import (
    INITIAL_RESTART_DELAY_SECONDS,
    MAXIMUM_RESTART_DELAY_SECONDS,
    is_within_active_hours,
    should_reset_backoff,
)
from session_store import forget_session_identifier_from_record
from transcript_productivity import count_non_api_error_transcript_entries
from session_watchdog import run_launch_command_once


def run_triggered_launch_iteration(
    agent_name: str,
    launch_command: str,
    tmux_target: str | None,
    runtime_root_directory: str,
    daily_session_rotation: bool,
    harness_runtime_profile,
    workspace_directory: str | None = None,
) -> None:
    launch_session = decide_and_persist_launch_session(
        runtime_root_directory,
        agent_name,
        daily_session_rotation,
        harness_runtime_profile,
        workspace_directory,
    )
    triggered_runtime_seconds, _exceeded_runtime_cap, resume_session_missing = (
        run_launch_command_to_completion(
            launch_command,
            tmux_target,
            harness_runtime_profile=harness_runtime_profile,
            agent_name=agent_name,
            session_argv=launch_session.session_argv,
            register_child_pid=register_current_child_process_id,
            is_resume_launch=launch_session.resume_previous_session,
        )
    )
    if resume_session_missing:
        emit_timestamped_log(
            agent_name,
            "could not resume its pinned session (no conversation found); "
            "dropping just that session so the next trigger falls back to "
            "remembered history.",
        )
        forget_session_identifier_from_record(
            launch_session.session_record_file_path,
            launch_session.session_identifier,
        )

    emit_timestamped_log(
        agent_name,
        f"completed a triggered launch after {int(triggered_runtime_seconds)} "
        "seconds. Exiting until the supervisor's launch gate fires again.",
    )


def run_warm_session_iteration(
    agent_name: str,
    launch_command: str,
    heartbeat_driver_argv: list[str] | None,
    tmux_target: str | None,
    runtime_root_directory: str,
    daily_session_rotation: bool,
    override_file: str,
    active_hours_start: int | None,
    active_hours_end: int | None,
    active_weekdays_only: bool,
    heartbeat_driver_log_path: str,
    restart_delay_seconds: int,
    harness_runtime_profile,
    workspace_directory: str | None = None,
    reason_to_replace_session=None,
) -> int:
    launch_session = decide_and_persist_launch_session(
        runtime_root_directory,
        agent_name,
        daily_session_rotation,
        harness_runtime_profile,
        workspace_directory,
    )
    if launch_session.rotating_session:
        emit_timestamped_log(agent_name, "daily session rotation. Starting fresh.")

    runtime_seconds, was_stuck_kill, resume_session_missing = run_launch_command_once(
        launch_command,
        heartbeat_driver_argv,
        tmux_target,
        harness_runtime_profile=harness_runtime_profile,
        agent_name=agent_name,
        session_argv=launch_session.session_argv,
        register_child_pid=register_current_child_process_id,
        daily_session_rotation=daily_session_rotation,
        heartbeat_driver_log_path=heartbeat_driver_log_path,
        is_resume_launch=launch_session.resume_previous_session,
        reason_to_replace_session=reason_to_replace_session,
    )

    transcript_entry_count = None
    if (
        workspace_directory
        and harness_runtime_profile.exposes_session_transcript_store()
    ):
        transcript_entry_count = count_non_api_error_transcript_entries(
            harness_runtime_profile.render_session_transcript_path(
                launch_session.session_identifier, workspace_directory
            )
        )
    judge_pending_delivery(
        harness_productivity_record_path(runtime_root_directory, agent_name),
        launch_session.session_identifier,
        transcript_entry_count,
    )

    if resume_session_missing:
        emit_timestamped_log(
            agent_name,
            "could not resume its pinned session (no conversation found); "
            "dropping just that session so the next launch falls back to "
            "remembered history.",
        )
        forget_session_identifier_from_record(
            launch_session.session_record_file_path,
            launch_session.session_identifier,
        )

    now_after_run = datetime.datetime.now()
    if not active_hours_gate_allows_run(
        is_within_active_hours(
            active_hours_start,
            active_hours_end,
            now_after_run,
            active_weekdays_only,
        ),
        read_override_active_until(override_file),
        now_after_run,
    ):
        return restart_delay_seconds

    if should_reset_backoff(runtime_seconds, was_stuck_kill):
        restart_delay_seconds = INITIAL_RESTART_DELAY_SECONDS

    emit_timestamped_log(
        agent_name,
        f"exited after {int(runtime_seconds)} seconds. "
        f"Restarting in {restart_delay_seconds} seconds...",
    )
    time.sleep(restart_delay_seconds)

    return min(restart_delay_seconds * 2, MAXIMUM_RESTART_DELAY_SECONDS)
