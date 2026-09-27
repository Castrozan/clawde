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
        "content": message.clean_content,
    }
