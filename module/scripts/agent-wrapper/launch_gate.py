import os
import subprocess
import time

from agent_process_tree import terminate_process_tree
from session_watchdog import resume_launch_hit_missing_session

MAXIMUM_TRIGGERED_LAUNCH_RUNTIME_SECONDS = 3600


def run_launch_command_to_completion(
    launch_command: str,
    tmux_target: str | None,
    harness_runtime_profile,
    agent_name: str = "",
    session_argv: str = "",
    register_child_pid=None,
    is_resume_launch: bool = False,
    maximum_runtime_seconds: int = MAXIMUM_TRIGGERED_LAUNCH_RUNTIME_SECONDS,
) -> tuple[float, bool, bool]:
    start_time = time.time()
    launch_environment = dict(os.environ)
    launch_environment["CLAWDE_SESSION_ARGV"] = session_argv
    launch_environment["CLAWDE_AGENT_NAME"] = agent_name
    agent_process = subprocess.Popen(
        ["bash", "-c", launch_command], env=launch_environment
    )
    if register_child_pid is not None:
        register_child_pid(agent_process.pid)
    exceeded_runtime_cap = False
    try:
        try:
            agent_process.wait(timeout=maximum_runtime_seconds)
        except subprocess.TimeoutExpired:
            terminate_process_tree(agent_process.pid)
            agent_process.wait()
            exceeded_runtime_cap = True
    finally:
        if register_child_pid is not None:
            register_child_pid(None)
    resume_session_missing = resume_launch_hit_missing_session(
        harness_runtime_profile, is_resume_launch, exceeded_runtime_cap, tmux_target
    )
    return time.time() - start_time, exceeded_runtime_cap, resume_session_missing
