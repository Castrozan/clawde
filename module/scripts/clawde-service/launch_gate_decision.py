import json
import subprocess
import threading
import time

from clawde_runtime_layout import launch_config_path_for_agent

LAUNCH_GATE_PROBE_TIMEOUT_SECONDS = 300


def read_launch_gate_configuration(
    launch_config_path: str,
) -> tuple[str | None, int | None]:
    with open(launch_config_path) as launch_config_file:
        launch_config = json.load(launch_config_file)
    return (
        launch_config.get("launch_gate_command"),
        launch_config.get("launch_gate_interval_seconds"),
    )


def launch_gate_configuration_for_agent(
    agent_name: str,
) -> tuple[str | None, int | None]:
    try:
        return read_launch_gate_configuration(launch_config_path_for_agent(agent_name))
    except (OSError, ValueError):
        return (None, None)


def agent_launches_on_trigger(agent_name: str) -> bool:
    _launch_gate_command, launch_gate_interval_seconds = (
        launch_gate_configuration_for_agent(agent_name)
    )
    return launch_gate_interval_seconds is not None


def run_launch_gate_probe(launch_gate_command: str) -> bool:
    try:
        completed_process = subprocess.run(
            ["bash", "-c", launch_gate_command],
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=LAUNCH_GATE_PROBE_TIMEOUT_SECONDS,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False
    return completed_process.returncode == 0


class LaunchGateScheduler:
    def __init__(self) -> None:
        self.state_lock = threading.Lock()
        self.agents_with_a_pending_launch: set = set()
        self.agents_with_a_probe_in_flight: set = set()
        self.earliest_next_probe_time_by_agent: dict = {}

    def record_probe_result(
        self, agent_name: str, gate_fired: bool, launch_gate_interval_seconds: int
    ) -> None:
        with self.state_lock:
            self.agents_with_a_probe_in_flight.discard(agent_name)
            self.earliest_next_probe_time_by_agent[agent_name] = (
                time.monotonic() + launch_gate_interval_seconds
            )
            if gate_fired:
                self.agents_with_a_pending_launch.add(agent_name)

    def start_probe_in_background(
        self,
        agent_name: str,
        launch_gate_command: str,
        launch_gate_interval_seconds: int,
    ) -> None:
        with self.state_lock:
            if agent_name in self.agents_with_a_probe_in_flight:
                return
            self.agents_with_a_probe_in_flight.add(agent_name)

        def probe_and_record_result() -> None:
            self.record_probe_result(
                agent_name,
                run_launch_gate_probe(launch_gate_command),
                launch_gate_interval_seconds,
            )

        threading.Thread(target=probe_and_record_result, daemon=True).start()

    def probe_is_due(self, agent_name: str) -> bool:
        with self.state_lock:
            if agent_name in self.agents_with_a_probe_in_flight:
                return False
            earliest_next_probe_time = self.earliest_next_probe_time_by_agent.get(
                agent_name
            )
            return (
                earliest_next_probe_time is None
                or time.monotonic() >= earliest_next_probe_time
            )

    def launch_is_pending(self, agent_name: str) -> bool:
        launch_gate_command, launch_gate_interval_seconds = (
            launch_gate_configuration_for_agent(agent_name)
        )
        if launch_gate_interval_seconds is None:
            return False
        with self.state_lock:
            if agent_name in self.agents_with_a_pending_launch:
                return True
        if not self.probe_is_due(agent_name):
            return False
        if launch_gate_command is None:
            self.record_probe_result(agent_name, True, launch_gate_interval_seconds)
            return True
        self.start_probe_in_background(
            agent_name, launch_gate_command, launch_gate_interval_seconds
        )
        return False

    def consume_pending_launch(self, agent_name: str) -> None:
        with self.state_lock:
            self.agents_with_a_pending_launch.discard(agent_name)
