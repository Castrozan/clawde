import os
import time

from channel_message import inbox_retention


def write_message_directory(
    state_directory, message_identifier, file_size, age_seconds
):
    message_directory = state_directory / "inbox" / message_identifier
    message_directory.mkdir(parents=True)
    (message_directory / "attachment.bin").write_bytes(b"x" * file_size)
    written_at = time.time() - age_seconds
    os.utime(message_directory, (written_at, written_at))
    return message_directory


def test_message_directories_older_than_the_retention_window_are_pruned(tmp_path):
    expired = write_message_directory(
        tmp_path, "1", 16, inbox_retention.INBOX_RETENTION_SECONDS + 1
    )
    kept = write_message_directory(tmp_path, "2", 16, 0)

    inbox_retention.prune_expired_inbox(str(tmp_path), time.time())

    assert not expired.exists()
    assert kept.exists()


def test_the_inbox_evicts_its_oldest_messages_once_it_outgrows_its_ceiling(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(inbox_retention, "INBOX_TOTAL_SIZE_LIMIT_BYTES", 300)
    oldest = write_message_directory(tmp_path, "1", 200, 300)
    middle = write_message_directory(tmp_path, "2", 200, 200)
    newest = write_message_directory(tmp_path, "3", 200, 100)

    inbox_retention.prune_expired_inbox(str(tmp_path), time.time())

    assert not oldest.exists()
    assert not middle.exists()
    assert newest.exists()


def test_an_inbox_within_its_ceiling_is_left_alone(tmp_path):
    kept = write_message_directory(tmp_path, "1", 16, 0)

    inbox_retention.prune_expired_inbox(str(tmp_path), time.time())

    assert kept.exists()


def test_pruning_a_state_directory_with_no_inbox_is_harmless(tmp_path):
    inbox_retention.prune_expired_inbox(str(tmp_path), time.time())

    assert not (tmp_path / "inbox").exists()


def test_a_message_identifier_cannot_steer_the_inbox_out_of_the_state_directory(
    tmp_path,
):
    destination = inbox_retention.prepare_inbox_for_message(str(tmp_path), "../escaped")

    assert os.path.realpath(destination).startswith(os.path.realpath(str(tmp_path)))
