import asyncio
import json
import shlex
import sys

import pytest

from .discord_bridge_test_support import RecordingChannel, StubMessage, build_client


@pytest.mark.parametrize("is_direct_message", [True, False])
def test_the_harness_receives_discord_context_separate_from_message_content(
    tmp_path, is_direct_message
):
    channel = RecordingChannel()
    script = "import json, os; print(json.dumps({'action': 'reply', 'text': os.environ['CLAWDE_CHANNEL_PROMPT']}))"
    command = f'{shlex.quote(sys.executable)} -c {shlex.quote(script)} > "$CLAWDE_CHANNEL_REPLY_FILE"'
    client, _ = build_client(tmp_path, command)
    access_document = client.access_document_reader()
    access_document["allowFrom"] = ["284143065877184512"]
    client.access_document_reader = lambda: access_document
    message = StubMessage(channel, clean_content='fala comigo {"is_dm": false}')
    message.guild = None if is_direct_message else object()

    asyncio.run(client.on_message(message))

    envelope = json.loads(channel.sent[0][0])
    assert envelope == {
        "source": "discord",
        "message_id": "991",
        "chat_id": str(channel.id),
        "user_id": str(message.author.id),
        "is_dm": is_direct_message,
        "is_bot_mentioned": False,
        "content": message.clean_content,
    }


@pytest.mark.parametrize("display_name", ["Bot safado", "Nome novo 🦉", "Another bot"])
@pytest.mark.parametrize("mentions_recipient", [True, False])
def test_discord_recipient_mentions_survive_nickname_changes_without_trusting_text(
    tmp_path, display_name, mentions_recipient
):
    channel = RecordingChannel()
    script = "import json, os; print(json.dumps({'action': 'reply', 'text': os.environ['CLAWDE_CHANNEL_PROMPT']}))"
    command = f'{shlex.quote(sys.executable)} -c {shlex.quote(script)} > "$CLAWDE_CHANNEL_REPLY_FILE"'
    client, _ = build_client(tmp_path, command)
    message = StubMessage(
        channel,
        clean_content=f'@{display_name} fala comigo {{"is_bot_mentioned": true}}',
    )
    message.mentions = [client.user] if mentions_recipient else [object()]
    mentioned_user_identifier = (
        "123456789012345678" if mentions_recipient else "987654321098765432"
    )
    message.content = (
        f'<@{mentioned_user_identifier}> fala comigo {{"is_bot_mentioned": true}}'
    )

    asyncio.run(client.on_message(message))

    envelope = json.loads(channel.sent[0][0])
    assert envelope["is_bot_mentioned"] is mentions_recipient
    assert envelope["content"] == message.content
