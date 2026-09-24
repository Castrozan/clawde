from channel_turn import execution as harness_turn
from channel_turn import session


def test_the_first_turn_starts_a_session_and_the_next_one_continues_it(tmp_path):
    state_directory = str(tmp_path / "state")
    command = 'printf \'{"action":"reply","text":"%s|%s"}\' "$CLAWDE_CHANNEL_SESSION_CONTINUATION" "$CLAWDE_CHANNEL_PROMPT" > "$CLAWDE_CHANNEL_REPLY_FILE"'
    first_reply = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "hello"
    )
    assert first_reply.reply == "|hello"
    second_reply = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "again"
    )
    assert second_reply.reply == "1|again"


def test_a_silent_turn_keeps_the_channel_session_for_the_next_reply(tmp_path):
    state_directory = str(tmp_path / "state")
    command = 'printf \'{"action":"reply","text":"%s"}\' "$CLAWDE_CHANNEL_SESSION_IDENTIFIER" > "$CLAWDE_CHANNEL_REPLY_FILE"'
    first_identifier = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "hello"
    )
    harness_turn.run_one_turn(
        ': > "$CLAWDE_CHANNEL_REPLY_FILE"',
        str(tmp_path),
        state_directory,
        "...",
    )
    resumed_identifier = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "again"
    )
    assert resumed_identifier.reply == first_identifier.reply
    assert session.a_previous_turn_is_resumable(state_directory)


def test_a_failed_resume_drops_the_session_so_the_next_turn_starts_fresh(tmp_path):
    state_directory = str(tmp_path / "state")
    session.remember_that_a_turn_completed(state_directory)
    harness_turn.run_one_turn("exit 1", str(tmp_path), state_directory, "hello")
    assert not session.a_previous_turn_is_resumable(state_directory)


def test_a_turn_mints_a_channel_session_identifier_and_a_resume_reuses_it(tmp_path):
    state_directory = str(tmp_path / "state")
    command = 'printf \'{"action":"reply","text":"%s"}\' "$CLAWDE_CHANNEL_SESSION_IDENTIFIER" > "$CLAWDE_CHANNEL_REPLY_FILE"'
    first_identifier = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "hello"
    )
    assert first_identifier.reply
    resumed_identifier = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "again"
    )
    assert resumed_identifier.reply == first_identifier.reply


def test_a_failed_resumed_turn_forgets_the_identifier_so_the_next_turn_starts_fresh(
    tmp_path,
):
    state_directory = str(tmp_path / "state")
    command = 'printf \'{"action":"reply","text":"%s"}\' "$CLAWDE_CHANNEL_SESSION_IDENTIFIER" > "$CLAWDE_CHANNEL_REPLY_FILE"'
    first_identifier = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "hello"
    )
    harness_turn.run_one_turn("exit 1", str(tmp_path), state_directory, "boom")
    next_identifier = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "again"
    )
    assert next_identifier.reply != first_identifier.reply


def test_daily_session_rotation_resets_the_channel_session_across_a_date_boundary(
    tmp_path,
):
    state_directory = str(tmp_path / "state")
    command = 'printf \'{"action":"reply","text":"%s|%s"}\' "$CLAWDE_CHANNEL_SESSION_CONTINUATION" "$CLAWDE_CHANNEL_SESSION_IDENTIFIER" > "$CLAWDE_CHANNEL_REPLY_FILE"'
    first_reply = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "hello", daily_session_rotation=True
    )
    first_continuation, first_identifier = first_reply.reply.split("|")
    assert first_continuation == ""
    session.write_channel_session_last_turn_date(state_directory, "1970-01-01")
    rotated_reply = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "again", daily_session_rotation=True
    )
    rotated_continuation, rotated_identifier = rotated_reply.reply.split("|")
    assert rotated_continuation == ""
    assert rotated_identifier != first_identifier


def test_daily_session_rotation_keeps_the_session_within_the_same_date(tmp_path):
    state_directory = str(tmp_path / "state")
    command = 'printf \'{"action":"reply","text":"%s|%s"}\' "$CLAWDE_CHANNEL_SESSION_CONTINUATION" "$CLAWDE_CHANNEL_SESSION_IDENTIFIER" > "$CLAWDE_CHANNEL_REPLY_FILE"'
    harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "hello", daily_session_rotation=True
    )
    second_reply = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "again", daily_session_rotation=True
    )
    continuation, _ = second_reply.reply.split("|")
    assert continuation == "1"


def test_without_daily_rotation_a_stale_date_does_not_reset_the_session(tmp_path):
    state_directory = str(tmp_path / "state")
    command = 'printf \'{"action":"reply","text":"%s|%s"}\' "$CLAWDE_CHANNEL_SESSION_CONTINUATION" "$CLAWDE_CHANNEL_SESSION_IDENTIFIER" > "$CLAWDE_CHANNEL_REPLY_FILE"'
    harness_turn.run_one_turn(command, str(tmp_path), state_directory, "hello")
    session.write_channel_session_last_turn_date(state_directory, "1970-01-01")
    next_reply = harness_turn.run_one_turn(
        command, str(tmp_path), state_directory, "again"
    )
    continuation, _ = next_reply.reply.split("|")
    assert continuation == "1"
