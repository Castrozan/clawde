import json


def transcript_entry_is_an_api_error(serialized_entry: bytes) -> bool:
    try:
        entry = json.loads(serialized_entry)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return False
    return isinstance(entry, dict) and entry.get("isApiErrorMessage") is True


def count_non_api_error_transcript_entries(file_path: str) -> int | None:
    try:
        with open(file_path, "rb") as open_file:
            return sum(
                1
                for serialized_entry in open_file
                if serialized_entry.endswith(b"\n")
                and not transcript_entry_is_an_api_error(serialized_entry)
            )
    except OSError:
        return None
