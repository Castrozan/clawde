import asyncio
import contextlib
import importlib.util
import json
import pathlib
import sys

from discord_stub_test_support import install_discord_stub

install_discord_stub()

DISCORD_SCRIPTS_DIRECTORY = (
    pathlib.Path(__file__).resolve().parents[4]
    / "channel-adapters"
    / "discord"
    / "scripts"
)


def load_bridge_module():
    specification = importlib.util.spec_from_file_location(
        "bridge", DISCORD_SCRIPTS_DIRECTORY / "bridge.py"
    )
    module = importlib.util.module_from_spec(specification)
    sys.modules["bridge"] = module
    specification.loader.exec_module(module)
    return module


bridge = load_bridge_module()


class StubAttachment:
    def __init__(self, filename, content_type, size, payload):
        self.filename = filename
        self.content_type = content_type
        self.size = size
        self.payload = payload
        self.url = "https://cdn.discordapp.example/file"

    async def save(self, destination_path):
        with open(destination_path, "wb") as destination_file:
            destination_file.write(self.payload)


class RecordingChannel:
    def __init__(self):
        self.id = 640612380338028606
        self.sent = []

    @contextlib.asynccontextmanager
    async def typing(self):
        yield

    async def send(self, content, files=None):
        self.sent.append((content, files))


class StubAuthor:
    def __init__(self):
        self.id = 284143065877184512
        self.bot = False


class StubMessage:
    def __init__(self, channel, clean_content="", attachments=(), stickers=()):
        self.id = 991
        self.channel = channel
        self.author = StubAuthor()
        self.clean_content = clean_content
        self.attachments = list(attachments)
        self.stickers = list(stickers)
        self.mentions = []
        self.guild = object()


def write_launch_config(tmp_path, one_shot_turn_command):
    launch_config_path = tmp_path / "launch-config" / "monster.json"
    launch_config_path.parent.mkdir(parents=True, exist_ok=True)
    launch_config_path.write_text(
        json.dumps(
            {
                "declared_harness": "codex",
                "harness_one_shot_turn_commands": {"codex": one_shot_turn_command},
            }
        )
    )
    return launch_config_path


def build_client(tmp_path, one_shot_turn_command):
    launch_config_path = write_launch_config(tmp_path, one_shot_turn_command)
    workspace_directory = tmp_path / "workspace"
    workspace_directory.mkdir()
    state_directory = tmp_path / "state"
    client = bridge.AgentBridgeClient.__new__(bridge.AgentBridgeClient)
    client.agent_name = "monster"
    client.launch_config_path = str(launch_config_path)
    client.workspace_directory = str(workspace_directory)
    client.state_directory = str(state_directory)
    client.daily_session_rotation = False
    client.access_document_reader = lambda: {
        "groups": {"640612380338028606": {"requireMention": False, "allowFrom": []}}
    }
    client.turn_lock = asyncio.Lock()
    client.user = object()
    return client, workspace_directory
