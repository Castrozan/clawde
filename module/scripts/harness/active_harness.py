import json
import os

HARNESS_OVERRIDE_SUBDIRECTORY = "harness-override"
DECLARED_HARNESS_LAUNCH_CONFIG_KEY = "declared_harness"
LAUNCH_COMMANDS_LAUNCH_CONFIG_KEY = "harness_launch_commands"
RUNTIME_PROFILES_LAUNCH_CONFIG_KEY = "harness_runtime_profiles"


def agent_name_from_launch_config_path(launch_config_path: str) -> str:
    return os.path.splitext(os.path.basename(launch_config_path))[0]


def runtime_root_directory_from_launch_config_path(launch_config_path: str) -> str:
    return os.path.dirname(os.path.dirname(launch_config_path))


def override_file_path_for_agent(runtime_root_directory: str, agent_name: str) -> str:
    return os.path.join(
        runtime_root_directory,
        HARNESS_OVERRIDE_SUBDIRECTORY,
        f"{agent_name}.json",
    )


def override_file_path_for_launch_config(launch_config_path: str) -> str:
    return override_file_path_for_agent(
        runtime_root_directory_from_launch_config_path(launch_config_path),
        agent_name_from_launch_config_path(launch_config_path),
    )


def read_overridden_harness_name(override_file_path: str) -> str | None:
    try:
        with open(override_file_path) as override_file:
            stored_harness_name = json.load(override_file)["harness"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    if isinstance(stored_harness_name, str) and stored_harness_name:
        return stored_harness_name
    return None


def write_overridden_harness_name(override_file_path: str, harness_name: str) -> None:
    os.makedirs(os.path.dirname(override_file_path), exist_ok=True)
    with open(override_file_path, "w") as override_file:
        json.dump({"harness": harness_name}, override_file)


def clear_override(override_file_path: str) -> None:
    try:
        os.remove(override_file_path)
    except FileNotFoundError:
        pass


def eligible_harness_names(launch_config: dict) -> list[str]:
    return sorted(launch_config.get(LAUNCH_COMMANDS_LAUNCH_CONFIG_KEY, {}))


def declared_harness_name(launch_config: dict) -> str:
    return launch_config[DECLARED_HARNESS_LAUNCH_CONFIG_KEY]


def resolve_active_harness_name(
    launch_config: dict, overridden_harness_name: str | None
) -> str:
    if overridden_harness_name in eligible_harness_names(launch_config):
        return overridden_harness_name
    return declared_harness_name(launch_config)


def active_harness_name_for_launch_config(
    launch_config: dict, launch_config_path: str
) -> str:
    return resolve_active_harness_name(
        launch_config,
        read_overridden_harness_name(
            override_file_path_for_launch_config(launch_config_path)
        ),
    )


def active_launch_command(launch_config: dict, active_harness: str) -> str:
    return launch_config[LAUNCH_COMMANDS_LAUNCH_CONFIG_KEY][active_harness]


def active_runtime_profile_mapping(launch_config: dict, active_harness: str) -> dict:
    return launch_config[RUNTIME_PROFILES_LAUNCH_CONFIG_KEY][active_harness]
