from active_harness import (
    active_harness_name_for_launch_config,
    read_launch_config,
    runtime_root_directory_from_launch_config_path,
)
from harness_productivity_record import (
    begin_harness_productivity_record,
    harness_productivity_record_path,
    read_harness_productivity_record,
    record_observed_heartbeat_turn,
)

ONE_SHOT_TURN_COMMANDS_LAUNCH_CONFIG_KEY = "harness_one_shot_turn_commands"


def resolve_active_one_shot_turn_command(
    launch_config_path: str,
) -> tuple[str, str | None]:
    launch_config = read_launch_config(launch_config_path)
    active_harness_name = active_harness_name_for_launch_config(
        launch_config, launch_config_path
    )
    commands = launch_config.get(ONE_SHOT_TURN_COMMANDS_LAUNCH_CONFIG_KEY)
    if not isinstance(commands, dict):
        return active_harness_name, None
    command = commands.get(active_harness_name)
    return active_harness_name, command if isinstance(command, str) else None


def record_channel_turn_productivity(
    launch_config_path: str,
    agent_name: str,
    active_harness_name: str,
    turn_was_productive: bool,
) -> None:
    record_path = harness_productivity_record_path(
        runtime_root_directory_from_launch_config_path(launch_config_path), agent_name
    )
    record = read_harness_productivity_record(record_path)
    if record.get("harness") != active_harness_name:
        begin_harness_productivity_record(record_path, active_harness_name)
    record_observed_heartbeat_turn(record_path, turn_was_productive)
