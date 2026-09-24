import subprocess

from channel_turn import execution as harness_turn
from channel_turn import session


def test_a_turn_that_writes_no_reply_reports_the_failure(tmp_path):
    result = harness_turn.run_one_turn(
        "echo 'harness exploded' >&2; exit 3",
        str(tmp_path),
        str(tmp_path / "state"),
        "hello",
    )
    assert result.reply == ""
    assert "harness exploded" in result.failure


def test_a_successful_turn_that_sends_nothing_is_reported_as_deliberate_silence(
    tmp_path,
):
    result = harness_turn.run_one_turn(
        ': > "$CLAWDE_CHANNEL_REPLY_FILE"',
        str(tmp_path),
        str(tmp_path / "state"),
        "hello",
    )
    assert result.reply == ""
    assert result.failure is None


def test_a_timed_out_turn_clears_the_channel_session_and_reports_a_failure(
    tmp_path, monkeypatch
):
    state_directory = str(tmp_path / "state")
    command = 'printf "%s" "$CLAWDE_CHANNEL_SESSION_IDENTIFIER" > "$CLAWDE_CHANNEL_REPLY_FILE"'
    harness_turn.run_one_turn(command, str(tmp_path), state_directory, "hello")
    assert session.a_previous_turn_is_resumable(state_directory)

    def raise_timeout(*_arguments, **_keyword_arguments):
        raise subprocess.TimeoutExpired("bash", harness_turn.TURN_TIMEOUT_SECONDS)

    monkeypatch.setattr(harness_turn.subprocess, "run", raise_timeout)

    result = harness_turn.run_one_turn(
        ': > "$CLAWDE_CHANNEL_REPLY_FILE"', str(tmp_path), state_directory, "again"
    )

    assert result.reply == ""
    assert "900" in result.failure
    assert not session.a_previous_turn_is_resumable(state_directory)
    assert session.read_channel_session_identifier(state_directory) is None


def test_a_missing_result_cannot_be_mistaken_for_intentional_silence(tmp_path):
    result = harness_turn.run_one_turn(
        "true", str(tmp_path), str(tmp_path / "state"), "hello"
    )

    assert not result.succeeded
    assert result.reply == ""
    assert "did not publish" in result.failure
