import os
import re
import shutil
import time

INBOX_DIRECTORY_NAME = "inbox"
INBOX_RETENTION_SECONDS = 2 * 24 * 60 * 60
INBOX_TOTAL_SIZE_LIMIT_BYTES = 1024 * 1024 * 1024
UNSAFE_FILE_NAME_CHARACTERS = re.compile(r"[^A-Za-z0-9._-]")
LONGEST_KEPT_FILE_NAME = 96
FALLBACK_FILE_NAME = "attachment"


def inbox_directory(state_directory: str) -> str:
    return os.path.join(state_directory, INBOX_DIRECTORY_NAME)


def message_inbox_directory(state_directory: str, message_identifier: str) -> str:
    return os.path.join(
        inbox_directory(state_directory), safe_file_name(message_identifier)
    )


def safe_file_name(file_name: str) -> str:
    sanitized = UNSAFE_FILE_NAME_CHARACTERS.sub("_", file_name).lstrip(".")
    if len(sanitized) > LONGEST_KEPT_FILE_NAME:
        stem, extension = os.path.splitext(sanitized)
        sanitized = stem[: LONGEST_KEPT_FILE_NAME - len(extension)] + extension
    return sanitized or FALLBACK_FILE_NAME


def message_directory_size(directory_path: str) -> int:
    total_size = 0
    for visited_directory, _, file_names in os.walk(directory_path):
        for file_name in file_names:
            try:
                total_size += os.path.getsize(
                    os.path.join(visited_directory, file_name)
                )
            except OSError:
                continue
    return total_size


def message_directories_oldest_first(state_directory: str) -> list:
    try:
        with os.scandir(inbox_directory(state_directory)) as entries:
            message_directories = [entry for entry in entries if entry.is_dir()]
    except OSError:
        return []
    return sorted(message_directories, key=lambda entry: entry.stat().st_mtime)


def evict_until_the_inbox_fits(message_directories) -> None:
    measured = [
        (entry, message_directory_size(entry.path)) for entry in message_directories
    ]
    kept_size = sum(size for _, size in measured)
    for entry, size in measured:
        if kept_size <= INBOX_TOTAL_SIZE_LIMIT_BYTES:
            return
        shutil.rmtree(entry.path, ignore_errors=True)
        kept_size -= size


def prune_expired_inbox(state_directory: str, now: float) -> None:
    cutoff = now - INBOX_RETENTION_SECONDS
    surviving_directories = []
    for entry in message_directories_oldest_first(state_directory):
        if entry.stat().st_mtime < cutoff:
            shutil.rmtree(entry.path, ignore_errors=True)
        else:
            surviving_directories.append(entry)
    evict_until_the_inbox_fits(surviving_directories)


def prepare_inbox_for_message(state_directory: str, message_identifier: str) -> str:
    prune_expired_inbox(state_directory, time.time())
    destination_directory = message_inbox_directory(state_directory, message_identifier)
    os.makedirs(destination_directory, exist_ok=True)
    return destination_directory
