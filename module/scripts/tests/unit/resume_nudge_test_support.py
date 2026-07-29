import importlib.util
import json
import pathlib
import sys

HEARTBEAT_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent / "heartbeat"
)


def load_resume_nudge_module():
    if str(HEARTBEAT_DIRECTORY) not in sys.path:
        sys.path.insert(0, str(HEARTBEAT_DIRECTORY))
    module_path = HEARTBEAT_DIRECTORY / "resume_nudge.py"
    module_spec = importlib.util.spec_from_file_location("resume_nudge", module_path)
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


def write_launch_config(tmp_path, profile_mapping):
    launch_config_path = tmp_path / f"{profile_mapping['harness_name']}.json"
    launch_config_path.write_text(
        json.dumps(
            {
                "launch_command": profile_mapping["harness_name"],
                "harness_runtime_profile": profile_mapping,
            }
        )
    )
    return str(launch_config_path)


def resume_nudge_argv(window_name, launch_config_path):
    return [
        "clawde-resume-nudge",
        "--session",
        "clawde",
        "--window",
        window_name,
        "--launch-config",
        launch_config_path,
    ]


class CompletedProcessStub:
    def __init__(self, stdout):
        self.stdout = stdout


class FakeHeartbeatBackend:
    def __init__(self):
        self.prepared_for = None
        self.dismiss_calls = 0
        self.prompts_sent = []
        self.pane_handle = object()

    def prepare_pane_handle(self, session_name, window_name):
        self.prepared_for = (session_name, window_name)
        return self.pane_handle

    def dismiss_pre_prompt_modal_if_present(self, pane_handle, harness_runtime_profile):
        self.dismiss_calls += 1

    def wait_for_agent_prompt(self, pane_handle, harness_runtime_profile):
        return True

    def send_prompt_to_pane(self, pane_handle, content):
        self.prompts_sent.append(content)
        return True
