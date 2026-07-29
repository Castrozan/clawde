import os
import subprocess

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


def start_heartbeat_driver_process(
    heartbeat_driver_argv: list[str] | None, heartbeat_driver_log_path: str | None
) -> subprocess.Popen | None:
    if not heartbeat_driver_argv:
        return None
    driver_log_sink = open_heartbeat_driver_log_sink(heartbeat_driver_log_path)
    driver_process = subprocess.Popen(
        heartbeat_driver_argv,
        stdin=subprocess.DEVNULL,
        stdout=driver_log_sink,
        stderr=subprocess.STDOUT,
    )
    if hasattr(driver_log_sink, "close"):
        driver_log_sink.close()
    return driver_process


def heartbeat_driver_has_given_up(
    driver_process: subprocess.Popen | None,
) -> bool:
    return driver_process is not None and driver_process.poll() is not None


def stop_heartbeat_driver_process(driver_process: subprocess.Popen | None) -> None:
    if driver_process is None:
        return
    driver_process.terminate()
    try:
        driver_process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        driver_process.kill()
