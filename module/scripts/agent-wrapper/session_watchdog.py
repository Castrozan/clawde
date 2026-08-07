import os
import subprocess
import time

from agent_process_tree import terminate_process_tree
from heartbeat_driver_process import (
    heartbeat_driver_has_given_up,
    start_heartbeat_driver_process,
    stop_heartbeat_driver_process,
)
from multiplexer_pane_capture import capture_pane_content, send_key_to_pane
from restart_scheduling import should_rotate_session
from stuck_indicators import pane_poll_is_stuck_evidence

WATCHDOG_POLL_INTERVAL_SECONDS = 30
WATCHDOG_CONSECUTIVE_STUCK_THRESHOLD = 2
RESUME_MODAL_WATCH_MAX_POLLS = 5
PANE_END_STATE_TAIL_LINE_COUNT = 15


def pane_tail(pane_content: str) -> str:
    return "\n".join(pane_content.splitlines()[-PANE_END_STATE_TAIL_LINE_COUNT:])


def pre_prompt_modal_in_pane_tail(harness_runtime_profile, pane_content: str):
    return harness_runtime_profile.matching_pre_prompt_modal(pane_tail(pane_content))


def resume_launch_hit_missing_session(
    harness_runtime_profile,
    is_resume_launch: bool,
    was_stuck_kill: bool,
    tmux_target: str | None,
) -> bool:
    if not is_resume_launch or was_stuck_kill or tmux_target is None:
        return False
    final_pane_content = capture_pane_content(tmux_target)
    if final_pane_content is None:
        return False
    return harness_runtime_profile.pane_indicates_missing_resume_session(
        pane_tail(final_pane_content)
    )


def run_launch_command_once(
    launch_command: str,
    heartbeat_driver_argv: list[str] | None,
    tmux_target: str | None,
    harness_runtime_profile,
    agent_name: str = "",
    session_argv: str = "",
    register_child_pid=None,
    daily_session_rotation: bool = False,
    heartbeat_driver_log_path: str | None = None,
    is_resume_launch: bool = False,
    reason_to_replace_session=None,
) -> tuple[float, bool, bool]:
    start_time = time.time()
    session_start_date = time.strftime("%Y-%m-%d")
    launch_environment = dict(os.environ)
    launch_environment["CLAWDE_SESSION_ARGV"] = session_argv
    launch_environment["CLAWDE_AGENT_NAME"] = agent_name
    agent_process = subprocess.Popen(
        ["bash", "-c", launch_command], env=launch_environment
    )
    if register_child_pid is not None:
        register_child_pid(agent_process.pid)
    driver_process = start_heartbeat_driver_process(
        heartbeat_driver_argv, heartbeat_driver_log_path
    )
    consecutive_stuck_polls = 0
    previous_pane_content: str | None = None
    was_stuck_kill = False
    resume_modal_watch_active = is_resume_launch
    resume_modal_watch_polls = 0
    try:
        while True:
            try:
                agent_process.wait(timeout=WATCHDOG_POLL_INTERVAL_SECONDS)
                break
            except subprocess.TimeoutExpired:
                if should_rotate_session(daily_session_rotation, session_start_date):
                    print(
                        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                        f"Daily session rotation boundary crossed since the session "
                        f"started on {session_start_date}. Terminating the session so "
                        f"the supervisor loop relaunches it fresh and releases the "
                        f"context memory accumulated over the day.",
                        flush=True,
                    )
                    terminate_process_tree(agent_process.pid)
                    agent_process.wait()
                    break
                session_replacement_reason = (
                    None
                    if reason_to_replace_session is None
                    else reason_to_replace_session()
                )
                if session_replacement_reason is not None:
                    print(
                        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                        f"{session_replacement_reason}. "
                        "Terminating session so the supervisor relaunches it.",
                        flush=True,
                    )
                    terminate_process_tree(agent_process.pid)
                    agent_process.wait()
                    was_stuck_kill = True
                    break
                if heartbeat_driver_has_given_up(driver_process):
                    print(
                        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                        "Heartbeat driver exited without reaching the agent REPL; "
                        "the session is wedged at a pre-prompt modal. "
                        "Terminating session to trigger a fresh restart.",
                        flush=True,
                    )
                    terminate_process_tree(agent_process.pid)
                    agent_process.wait()
                    was_stuck_kill = True
                    break
                if tmux_target is None:
                    continue
                pane_content = capture_pane_content(tmux_target)
                if pane_content is None:
                    consecutive_stuck_polls = 0
                    continue
                if resume_modal_watch_active:
                    resume_modal_watch_polls += 1
                    pending_modal = pre_prompt_modal_in_pane_tail(
                        harness_runtime_profile, pane_content
                    )
                    if (
                        harness_runtime_profile.pane_is_at_idle_prompt(pane_content)
                        or resume_modal_watch_polls > RESUME_MODAL_WATCH_MAX_POLLS
                    ):
                        resume_modal_watch_active = False
                    elif pending_modal is not None:
                        send_key_to_pane(tmux_target, pending_modal["dismiss_key"])
                        consecutive_stuck_polls = 0
                        previous_pane_content = None
                        continue
                if pane_poll_is_stuck_evidence(
                    harness_runtime_profile, pane_content, previous_pane_content
                ):
                    consecutive_stuck_polls += 1
                else:
                    consecutive_stuck_polls = 0
                previous_pane_content = pane_content
                if consecutive_stuck_polls >= WATCHDOG_CONSECUTIVE_STUCK_THRESHOLD:
                    print(
                        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                        "Agent pane unresponsive "
                        "(frozen and not at the idle prompt, or usage-limit modal). "
                        "Terminating session to trigger a restart.",
                        flush=True,
                    )
                    terminate_process_tree(agent_process.pid)
                    agent_process.wait()
                    was_stuck_kill = True
                    break
    finally:
        if register_child_pid is not None:
            register_child_pid(None)
        stop_heartbeat_driver_process(driver_process)
    resume_session_missing = resume_launch_hit_missing_session(
        harness_runtime_profile, is_resume_launch, was_stuck_kill, tmux_target
    )
    return time.time() - start_time, was_stuck_kill, resume_session_missing
