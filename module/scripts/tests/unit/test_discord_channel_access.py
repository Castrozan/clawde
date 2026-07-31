import channel_access
import pytest

ALLOWED_CHANNEL = "123"
DIRECT_MESSAGE_CHANNEL = "a-direct-message-channel"
AUTHOR = "999"


def guild_access_document(**group_settings):
    return {"groups": {ALLOWED_CHANNEL: dict(group_settings)}}


def direct_message_access_document(**document_settings):
    return {"groups": {}, **document_settings}


def test_a_message_in_an_allowed_channel_reaches_the_agent():
    assert channel_access.message_is_for_this_agent(
        guild_access_document(), ALLOWED_CHANNEL, AUTHOR, False, False, False
    )


def test_a_message_in_an_unlisted_channel_is_ignored():
    assert not channel_access.message_is_for_this_agent(
        guild_access_document(), "other-channel", AUTHOR, False, False, False
    )


def test_a_message_from_another_bot_is_ignored():
    assert not channel_access.message_is_for_this_agent(
        guild_access_document(), ALLOWED_CHANNEL, AUTHOR, True, False, False
    )


def test_an_author_outside_the_allowlist_is_ignored():
    assert not channel_access.message_is_for_this_agent(
        guild_access_document(allowFrom=["someone-else"]),
        ALLOWED_CHANNEL,
        AUTHOR,
        False,
        False,
        False,
    )


@pytest.mark.parametrize(
    "agent_was_mentioned, expected", [(True, True), (False, False)]
)
def test_a_mention_only_channel_answers_only_when_mentioned(
    agent_was_mentioned, expected
):
    assert (
        channel_access.message_is_for_this_agent(
            guild_access_document(requireMention=True),
            ALLOWED_CHANNEL,
            AUTHOR,
            False,
            agent_was_mentioned,
            False,
        )
        is expected
    )


def test_a_missing_access_file_denies_every_channel(tmp_path):
    assert not channel_access.message_is_for_this_agent(
        channel_access.load_access_document(str(tmp_path)),
        ALLOWED_CHANNEL,
        AUTHOR,
        False,
        False,
        False,
    )


def test_a_direct_message_from_an_allowed_author_reaches_the_agent():
    assert channel_access.message_is_for_this_agent(
        direct_message_access_document(dmPolicy="allowlist", allowFrom=[AUTHOR]),
        DIRECT_MESSAGE_CHANNEL,
        AUTHOR,
        False,
        False,
        True,
    )


def test_a_direct_message_from_an_unlisted_author_is_ignored():
    assert not channel_access.message_is_for_this_agent(
        direct_message_access_document(
            dmPolicy="allowlist", allowFrom=["someone-else"]
        ),
        DIRECT_MESSAGE_CHANNEL,
        AUTHOR,
        False,
        False,
        True,
    )


def test_a_direct_message_is_ignored_when_the_policy_disables_them():
    assert not channel_access.message_is_for_this_agent(
        direct_message_access_document(dmPolicy="disabled", allowFrom=[AUTHOR]),
        DIRECT_MESSAGE_CHANNEL,
        AUTHOR,
        False,
        False,
        True,
    )


def test_an_agent_with_no_direct_message_allowlist_answers_no_direct_message():
    assert not channel_access.message_is_for_this_agent(
        direct_message_access_document(dmPolicy="pairing"),
        DIRECT_MESSAGE_CHANNEL,
        AUTHOR,
        False,
        False,
        True,
    )


def test_a_direct_message_needs_no_mention_and_no_channel_opt_in():
    assert channel_access.message_is_for_this_agent(
        {
            "dmPolicy": "pairing",
            "allowFrom": [AUTHOR],
            "groups": {ALLOWED_CHANNEL: {"requireMention": True}},
        },
        DIRECT_MESSAGE_CHANNEL,
        AUTHOR,
        False,
        False,
        True,
    )
