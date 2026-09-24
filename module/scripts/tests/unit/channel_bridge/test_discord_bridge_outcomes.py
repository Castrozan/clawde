import asyncio
import json
import shlex

import pytest
from harness_productivity_record import harness_is_refusing_work
from .discord_bridge_test_support import (
    RecordingChannel,
    StubMessage,
    build_client,
    write_launch_config,
)


@pytest.mark.parametrize(
    "reply",
    [
        "",
        "  \n ",
        "(no reply)",
        "*(no reply)*",
        "(mute)",
        "(sem resposta)",
        "arbitrary model narration",
        '{"action":"silence","text":""}',
        '{"action":[],"text":"bad"}',
        '{"action":"reply","text":""}',
        '{"action":"reply","text":"hidden","extra":true}',
    ],
)
def test_successful_silence_never_posts_or_triggers_harness_failover(tmp_path, reply):
    channel = RecordingChannel()
    client, _ = build_client(
        tmp_path, f'printf %s {shlex.quote(reply)} > "$CLAWDE_CHANNEL_REPLY_FILE"'
    )

    for _ in range(4):
        asyncio.run(client.on_message(StubMessage(channel, clean_content="room chat")))

    record = json.loads(
        (tmp_path / "harness-productivity" / "monster.json").read_text()
    )
    assert channel.sent == []
    assert record["consecutive_unproductive_turns"] == 0
    assert not harness_is_refusing_work(record, "codex")
    assert (tmp_path / "state" / "bridge-session-started").exists()


@pytest.mark.parametrize(
    "command",
    [
        "exit 3",
        "printf 'provider unavailable' >&2; exit 3",
        'printf "partial output" > "$CLAWDE_CHANNEL_REPLY_FILE"; exit 3',
        '(printf "partial output"; exit 3) | cat > "$CLAWDE_CHANNEL_REPLY_FILE"',
    ],
)
def test_failed_turns_publish_nothing_and_still_trigger_failover(tmp_path, command):
    channel = RecordingChannel()
    client, _ = build_client(tmp_path, command)

    for _ in range(3):
        asyncio.run(client.on_message(StubMessage(channel, clean_content="hello")))

    record = json.loads(
        (tmp_path / "harness-productivity" / "monster.json").read_text()
    )
    assert channel.sent == []
    assert harness_is_refusing_work(record, "codex")
    assert not (tmp_path / "state" / "bridge-session-started").exists()


def test_a_real_reply_mentioning_the_placeholder_is_delivered_unchanged(tmp_path):
    reply = "You posted (no reply) again."
    envelope = json.dumps({"action": "reply", "text": reply})
    channel = RecordingChannel()
    client, _ = build_client(
        tmp_path, f'printf %s {shlex.quote(envelope)} > "$CLAWDE_CHANNEL_REPLY_FILE"'
    )

    asyncio.run(client.on_message(StubMessage(channel, clean_content="hello")))

    assert channel.sent == [(reply, None)]


def test_successful_silence_breaks_a_failure_streak(tmp_path):
    channel = RecordingChannel()
    client, _ = build_client(tmp_path, "exit 3")
    for _ in range(2):
        asyncio.run(client.on_message(StubMessage(channel, clean_content="hello")))
    write_launch_config(tmp_path, ': > "$CLAWDE_CHANNEL_REPLY_FILE"')

    asyncio.run(client.on_message(StubMessage(channel, clean_content="room chat")))

    record = json.loads(
        (tmp_path / "harness-productivity" / "monster.json").read_text()
    )
    assert record["consecutive_unproductive_turns"] == 0
    assert channel.sent == []
