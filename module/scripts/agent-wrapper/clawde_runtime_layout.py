import json
import os

RUNTIME_ROOT_RELATIVE_TO_HOME = "clawde"
LAUNCH_CONFIG_SUBDIRECTORY = "launch-config"


def runtime_root_directory() -> str:
    return os.path.join(os.path.expanduser("~"), RUNTIME_ROOT_RELATIVE_TO_HOME)


def launch_config_directory() -> str:
    return os.path.join(runtime_root_directory(), LAUNCH_CONFIG_SUBDIRECTORY)


def launch_config_path_for_agent(agent_name: str) -> str:
    return os.path.join(launch_config_directory(), f"{agent_name}.json")


def deployed_agent_names() -> list[str]:
    json_suffix = ".json"
    try:
        directory_entries = os.listdir(launch_config_directory())
    except FileNotFoundError:
        return []
    return sorted(
        directory_entry[: -len(json_suffix)]
        for directory_entry in directory_entries
        if directory_entry.endswith(json_suffix)
    )


def read_active_hours_window(launch_config_path: str) -> tuple[int | None, int | None]:
    with open(launch_config_path) as launch_config_file:
        launch_config = json.load(launch_config_file)
    return (
        launch_config.get("active_hours_start"),
        launch_config.get("active_hours_end"),
    )
