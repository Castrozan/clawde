import importlib.util
import pathlib
import subprocess
import sys
import types

import harness_turn

OPENCODE_SCRIPTS_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent.parent
    / "harnesses"
    / "opencode"
    / "scripts"
)

DISCORD_SCRIPTS_DIRECTORY = (
    pathlib.Path(__file__).resolve().parent.parent.parent.parent
    / "channel-adapters"
    / "discord"
    / "scripts"
)


def load_module_from_path(module_name, module_path):
    specification = importlib.util.spec_from_file_location(module_name, module_path)
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


extract_reply = load_module_from_path(
    "extract_reply_from_run_output",
    OPENCODE_SCRIPTS_DIRECTORY / "extract-reply-from-run-output.py",
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


def test_a_turn_mints_a_channel_session_identifier_and_a_resume_reuses_it(tmp_path):
    state_directory = str(tmp_path / "state")
    command = 'printf "%s" "$CLAWDE_CHANNEL_SESSION_IDENTIFIER" > "$CLAWDE_CHANNEL_REPLY_FILE"'
    first_identifier, _ = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "hello"
    )
    assert first_identifier
    resumed_identifier, _ = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "again"
    )
    assert resumed_identifier == first_identifier


def test_a_failed_resumed_turn_forgets_the_identifier_so_the_next_turn_starts_fresh(
    tmp_path,
):
    state_directory = str(tmp_path / "state")
    command = 'printf "%s" "$CLAWDE_CHANNEL_SESSION_IDENTIFIER" > "$CLAWDE_CHANNEL_REPLY_FILE"'
    first_identifier, _ = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "hello"
    )
    harness_turn.run_one_turn("exit 1", str(tmp_path), state_directory, "boom")
    next_identifier, _ = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "again"
    )
    assert next_identifier != first_identifier


def test_daily_session_rotation_resets_the_channel_session_across_a_date_boundary(
    tmp_path,
):
    state_directory = str(tmp_path / "state")
    command = 'printf "%s|%s" "$CLAWDE_CHANNEL_SESSION_CONTINUATION" "$CLAWDE_CHANNEL_SESSION_IDENTIFIER" > "$CLAWDE_CHANNEL_REPLY_FILE"'
    first_reply, _ = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "hello", daily_session_rotation=True
    )
    first_continuation, first_identifier = first_reply.split("|")
    assert first_continuation == ""
    harness_turn.write_channel_session_last_turn_date(state_directory, "1970-01-01")
    rotated_reply, _ = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "again", daily_session_rotation=True
    )
    rotated_continuation, rotated_identifier = rotated_reply.split("|")
    assert rotated_continuation == ""
    assert rotated_identifier != first_identifier


def test_daily_session_rotation_keeps_the_session_within_the_same_date(tmp_path):
    state_directory = str(tmp_path / "state")
    command = 'printf "%s|%s" "$CLAWDE_CHANNEL_SESSION_CONTINUATION" "$CLAWDE_CHANNEL_SESSION_IDENTIFIER" > "$CLAWDE_CHANNEL_REPLY_FILE"'
    harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "hello", daily_session_rotation=True
    )
    second_reply, _ = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "again", daily_session_rotation=True
    )
    continuation, _ = second_reply.split("|")
    assert continuation == "1"


def test_without_daily_rotation_a_stale_date_does_not_reset_the_session(tmp_path):
    state_directory = str(tmp_path / "state")
    command = 'printf "%s|%s" "$CLAWDE_CHANNEL_SESSION_CONTINUATION" "$CLAWDE_CHANNEL_SESSION_IDENTIFIER" > "$CLAWDE_CHANNEL_REPLY_FILE"'
    harness_turn.run_one_turn(command, str(tmp_path), state_directory, "hello")
    harness_turn.write_channel_session_last_turn_date(state_directory, "1970-01-01")
    next_reply, _ = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "again"
    )
    continuation, _ = next_reply.split("|")
    assert continuation == "1"


def test_a_timed_out_turn_clears_the_channel_session_and_reports_a_failure(
    tmp_path, monkeypatch
):
    state_directory = str(tmp_path / "state")
    command = 'printf "%s" "$CLAWDE_CHANNEL_SESSION_IDENTIFIER" > "$CLAWDE_CHANNEL_REPLY_FILE"'
    harness_turn.run_one_turn(command, str(tmp_path), state_directory, "hello")
    assert harness_turn.a_previous_turn_is_resumable(state_directory)

    def raise_timeout(*_arguments, **_keyword_arguments):
        raise subprocess.TimeoutExpired("bash", harness_turn.TURN_TIMEOUT_SECONDS)

    monkeypatch.setattr(harness_turn.subprocess, "run", raise_timeout)

    reply, failure = harness_turn.run_one_turn(
        "true", str(tmp_path), state_directory, "again"
    )

    assert reply == ""
    assert "900" in failure
    assert not harness_turn.a_previous_turn_is_resumable(state_directory)
    assert harness_turn.read_channel_session_identifier(state_directory) is None


def load_bridge_module_with_stubbed_discord():
    discord_stub = types.ModuleType("discord")
    discord_stub.Client = type("Client", (), {})
    discord_stub.Message = object
    discord_stub.Intents = type(
        "Intents", (), {"default": staticmethod(lambda: object())}
    )
    sys.modules["discord"] = discord_stub
    return load_module_from_path("bridge", DISCORD_SCRIPTS_DIRECTORY / "bridge.py")


def test_the_bridge_parses_the_daily_session_rotation_flag(monkeypatch):
    bridge = load_bridge_module_with_stubbed_discord()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bridge.py",
            "--agent-name",
            "agent-a",
            "--one-shot-turn-command",
            "true",
            "--workspace-directory",
            "/tmp",
            "--state-directory",
            "/tmp",
            "--daily-session-rotation",
        ],
    )

    arguments = bridge.parse_arguments()

    assert arguments.daily_session_rotation is True


def test_the_bridge_defaults_to_no_daily_session_rotation(monkeypatch):
    bridge = load_bridge_module_with_stubbed_discord()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bridge.py",
            "--agent-name",
            "agent-a",
            "--one-shot-turn-command",
            "true",
            "--workspace-directory",
            "/tmp",
            "--state-directory",
            "/tmp",
        ],
    )

    arguments = bridge.parse_arguments()

    assert arguments.daily_session_rotation is False
