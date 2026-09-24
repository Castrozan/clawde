import asyncio
import json
import shlex
import sys

from .discord_bridge_test_support import (
    RecordingChannel,
    StubAttachment,
    StubMessage,
    build_client,
    write_launch_config,
)


def test_a_video_only_message_runs_a_turn_whose_prompt_names_the_saved_file(tmp_path):
    channel = RecordingChannel()
    script = "import json, os; print(json.dumps({'action': 'reply', 'text': os.environ['CLAWDE_CHANNEL_PROMPT']}))"
    command = f'{shlex.quote(sys.executable)} -c {shlex.quote(script)} > "$CLAWDE_CHANNEL_REPLY_FILE"'
    client, _ = build_client(tmp_path, command)
    message = StubMessage(
        channel,
        attachments=[StubAttachment("spiderman.mp4", "video/mp4", 7, b"MOOVATOM")],
    )

    asyncio.run(client.on_message(message))

    echoed_prompt = channel.sent[0][0]
    saved_path = tmp_path / "state" / "inbox" / "991" / "0-spiderman.mp4"
    assert str(saved_path) in echoed_prompt
    assert saved_path.read_bytes() == b"MOOVATOM"


def test_a_reply_naming_a_workspace_file_arrives_as_an_attachment(tmp_path):
    channel = RecordingChannel()
    client, workspace_directory = build_client(tmp_path, "")
    gif_path = workspace_directory / "media" / "sneer.gif"
    gif_path.parent.mkdir(parents=True)
    gif_path.write_bytes(b"GIF89a")
    envelope = json.dumps({"action": "reply", "text": f"toma\n{gif_path}"})
    write_launch_config(
        tmp_path, f'printf %s {shlex.quote(envelope)} > "$CLAWDE_CHANNEL_REPLY_FILE"'
    )

    asyncio.run(client.on_message(StubMessage(channel, clean_content="manda um gif")))

    content, files = channel.sent[0]
    assert content == "toma"
    assert [attached.path for attached in files] == [str(gif_path)]


def test_a_message_the_bridge_cannot_render_never_reaches_the_harness(tmp_path):
    channel = RecordingChannel()
    client, _ = build_client(
        tmp_path, 'printf "answered" > "$CLAWDE_CHANNEL_REPLY_FILE"'
    )

    asyncio.run(client.on_message(StubMessage(channel)))

    assert channel.sent == []
