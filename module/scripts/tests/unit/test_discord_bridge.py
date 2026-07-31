import importlib.util
import pathlib
import sys

import pytest

DISCORD_SCRIPTS_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent.parent
    / "channel-adapters"
    / "discord"
    / "scripts"
)
OPENCODE_SCRIPTS_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent.parent
    / "harnesses"
    / "opencode"
    / "scripts"
)


def load_module_from_path(module_name, module_path):
    specification = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


channel_access = load_module_from_path(
    "channel_access", DISCORD_SCRIPTS_DIRECTORY / "channel_access.py"
)
harness_turn = load_module_from_path(
    "harness_turn", DISCORD_SCRIPTS_DIRECTORY / "harness_turn.py"
)
extract_reply = load_module_from_path(
    "extract_reply_from_run_output",
    OPENCODE_SCRIPTS_DIRECTORY / "extract-reply-from-run-output.py",
)

ALLOWED_CHANNEL = "123"
AUTHOR = "999"


def access_document(**group_settings):
    return {"groups": {ALLOWED_CHANNEL: dict(group_settings)}}


def test_a_message_in_an_allowed_channel_reaches_the_agent():
    assert channel_access.message_is_for_this_agent(
        access_document(), ALLOWED_CHANNEL, AUTHOR, False, False
    )


def test_a_message_in_an_unlisted_channel_is_ignored():
    assert not channel_access.message_is_for_this_agent(
        access_document(), "other-channel", AUTHOR, False, False
    )


def test_a_message_from_another_bot_is_ignored():
    assert not channel_access.message_is_for_this_agent(
        access_document(), ALLOWED_CHANNEL, AUTHOR, True, False
    )


def test_an_author_outside_the_allowlist_is_ignored():
    assert not channel_access.message_is_for_this_agent(
        access_document(allowFrom=["someone-else"]),
        ALLOWED_CHANNEL,
        AUTHOR,
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
            access_document(requireMention=True),
            ALLOWED_CHANNEL,
            AUTHOR,
            False,
            agent_was_mentioned,
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
    )


def test_the_first_turn_starts_a_session_and_the_next_one_continues_it(tmp_path):
    state_directory = str(tmp_path / "state")
    command = 'printf "%s|%s" "$CLAWDE_CHANNEL_SESSION_CONTINUATION" "$CLAWDE_CHANNEL_PROMPT" > "$CLAWDE_CHANNEL_REPLY_FILE"'
    first_reply, _ = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "hello"
    )
    assert first_reply == "|hello"
    second_reply, _ = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "again"
    )
    assert second_reply == "1|again"


def test_a_turn_that_writes_no_reply_reports_the_failure(tmp_path):
    reply, failure = harness_turn.run_one_turn(
        "echo 'harness exploded' >&2", str(tmp_path), str(tmp_path / "state"), "hello"
    )
    assert reply == ""
    assert "harness exploded" in failure


def test_a_failed_resume_drops_the_session_so_the_next_turn_starts_fresh(tmp_path):
    state_directory = str(tmp_path / "state")
    harness_turn.remember_that_a_turn_completed(state_directory)
    harness_turn.run_one_turn("exit 1", str(tmp_path), state_directory, "hello")
    assert not harness_turn.a_previous_turn_is_resumable(state_directory)


def test_the_opencode_run_header_and_colour_codes_are_stripped_from_the_reply():
    assert (
        extract_reply.extract_assistant_reply(
            "\x1b[0m\n> build · deepseek-v4-flash-free\n\x1b[0m\nHARNESS OK\n"
        )
        == "HARNESS OK"
    )


def test_a_reply_without_a_header_survives_intact():
    assert (
        extract_reply.extract_assistant_reply("just the answer\n") == "just the answer"
    )
