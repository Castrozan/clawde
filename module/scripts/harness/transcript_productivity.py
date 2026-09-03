import json


def transcript_entry_represents_assistant_work(serialized_entry: bytes) -> bool:
    try:
        entry = json.loads(serialized_entry)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    if not isinstance(entry, dict) or entry.get("isApiErrorMessage") is True:
        return False
    message = entry.get("message")
    return entry.get("type") == "assistant" or (
        isinstance(message, dict) and message.get("role") == "assistant"
    )


def count_transcript_assistant_work_entries(file_path: str) -> int | None:
    try:
        with open(file_path, "rb") as open_file:
            return sum(
                1
                for serialized_entry in open_file
                if serialized_entry.endswith(b"\n")
                and transcript_entry_represents_assistant_work(serialized_entry)
            )
    except OSError:
        return None
