import datetime
import json

from agent_wrapper_test_support import load_agent_wrapper_module
from harness_productivity_record import (
    CONSECUTIVE_UNPRODUCTIVE_TURNS_BEFORE_FAILOVER,
    begin_harness_productivity_record,
    harness_productivity_record_path,
    record_observed_heartbeat_turn,
)

harness_failover = load_agent_wrapper_module("harness_failover")

AT_NOON = datetime.datetime(2026, 8, 7, 12, 0, 0)

STEWARD_LAUNCH_CONFIG = {
    "declared_harness": "opencode",
    "harness_fallback_chain": ["codex", "claude"],
    "harness_launch_commands": {
        "claude": "claude",
        "codex": "codex",
        "opencode": "opencode",
    },
}


def deploy_launch_config(tmp_path, launch_config, agent_name="steward"):
    launch_config_directory = tmp_path / "launch-config"
    launch_config_directory.mkdir(parents=True, exist_ok=True)
    launch_config_path = launch_config_directory / f"{agent_name}.json"
    launch_config_path.write_text(json.dumps(launch_config))
    return str(launch_config_path)


def park_agent_on_its_harness(tmp_path, harness_name, agent_name="steward"):
    record_path = harness_productivity_record_path(str(tmp_path), agent_name)
    begin_harness_productivity_record(record_path, harness_name, AT_NOON)
    for _turn in range(CONSECUTIVE_UNPRODUCTIVE_TURNS_BEFORE_FAILOVER):
        record_observed_heartbeat_turn(record_path, False, AT_NOON)
    return record_path
