import os
import signal
import subprocess
import time

from multiplexer_pane_capture import capture_pane_content, send_enter_key_to_pane
from restart_scheduling import should_rotate_session
from stuck_indicators import (
    pane_indicates_missing_resume_session,
    pane_indicates_resume_confirmation_modal,
    pane_is_at_idle_repl_prompt,
    pane_poll_is_stuck_evidence,
)

WATCHDOG_POLL_INTERVAL_SECONDS = 30
WATCHDOG_CONSECUTIVE_STUCK_THRESHOLD = 2
RESUME_MODAL_WATCH_MAX_POLLS = 5
PANE_END_STATE_TAIL_LINE_COUNT = 15
HEARTBEAT_DRIVER_LOG_SUBDIRECTORY = "heartbeat-driver-logs"


def heartbeat_driver_log_path_for_agent(
    runtime_root_directory: str, agent_name: str
) -> str:
    return os.path.join(
        runtime_root_directory,
        HEARTBEAT_DRIVER_LOG_SUBDIRECTORY,
        f"{agent_name}.log",
    )


def open_heartbeat_driver_log_sink(heartbeat_driver_log_path: str | None):
    if heartbeat_driver_log_path is None:
        return subprocess.DEVNULL
    os.makedirs(os.path.dirname(heartbeat_driver_log_path), exist_ok=True)
    return open(heartbeat_driver_log_path, "a")


def collect_descendant_process_ids(parent_process_id: int) -> list[int]:
    result = subprocess.run(
        ["pgrep", "-P", str(parent_process_id)],
        capture_output=True,
        text=True,
    )
    descendant_process_ids: list[int] = []
    for line in result.stdout.split():
        child_process_id = int(line)
        descendant_process_ids.extend(collect_descendant_process_ids(child_process_id))
        descendant_process_ids.append(child_process_id)
    return descendant_process_ids


def terminate_process_tree(root_process_id: int) -> None:
    for process_id in collect_descendant_process_ids(root_process_id) + [
        root_process_id
    ]:
        try:
            os.kill(process_id, signal.SIGTERM)
        except ProcessLookupError:
            pass


def heartbeat_driver_has_given_up(
    driver_process: subprocess.Popen | None,
) -> bool:
    return driver_process is not None and driver_process.poll() is not None


def pane_tail_shows_resume_confirmation_modal(pane_content: str) -> bool:
    pane_tail = "\n".join(pane_content.splitlines()[-PANE_END_STATE_TAIL_LINE_COUNT:])
    return pane_indicates_resume_confirmation_modal(pane_tail)


def resume_launch_hit_missing_session(
    is_resume_launch: bool, was_stuck_kill: bool, tmux_target: str | None
) -> bool:
    if not is_resume_launch or was_stuck_kill or tmux_target is None:
        return False
    final_pane_content = capture_pane_content(tmux_target)
    if final_pane_content is None:
        return False
    final_pane_tail = "\n".join(
        final_pane_content.splitlines()[-PANE_END_STATE_TAIL_LINE_COUNT:]
    )
    return pane_indicates_missing_resume_session(final_pane_tail)


def run_launch_command_once(
    launch_command: str,
    heartbeat_driver_argv: list[str] | None,
    tmux_target: str | None,
    resume_flag: str = "",
    register_child_pid=None,
    daily_session_rotation: bool = False,
    heartbeat_driver_log_path: str | None = None,
    is_resume_launch: bool = False,
) -> tuple[float, bool, bool]:
    start_time = time.time()
    session_start_date = time.strftime("%Y-%m-%d")
    launch_environment = dict(os.environ)
    launch_environment["CLAWDE_RESUME_FLAG"] = resume_flag
    agent_process = subprocess.Popen(
        ["bash", "-c", launch_command], env=launch_environment
    )
    if register_child_pid is not None:
        register_child_pid(agent_process.pid)
    driver_process = None
    if heartbeat_driver_argv:
        driver_log_sink = open_heartbeat_driver_log_sink(heartbeat_driver_log_path)
        driver_process = subprocess.Popen(
            heartbeat_driver_argv,
            stdin=subprocess.DEVNULL,
            stdout=driver_log_sink,
            stderr=subprocess.STDOUT,
        )
        if hasattr(driver_log_sink, "close"):
            driver_log_sink.close()
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
                if heartbeat_driver_has_given_up(driver_process):
                    print(
                        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] "
                        "Heartbeat driver exited without reaching the claude REPL; "
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
                    if (
                        pane_is_at_idle_repl_prompt(pane_content)
                        or resume_modal_watch_polls > RESUME_MODAL_WATCH_MAX_POLLS
                    ):
                        resume_modal_watch_active = False
                    elif pane_tail_shows_resume_confirmation_modal(pane_content):
                        send_enter_key_to_pane(tmux_target)
                        consecutive_stuck_polls = 0
                        previous_pane_content = None
                        continue
                if pane_poll_is_stuck_evidence(pane_content, previous_pane_content):
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
        if driver_process is not None:
            driver_process.terminate()
            try:
                driver_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                driver_process.kill()
    resume_session_missing = resume_launch_hit_missing_session(
        is_resume_launch, was_stuck_kill, tmux_target
    )
    return time.time() - start_time, was_stuck_kill, resume_session_missing
