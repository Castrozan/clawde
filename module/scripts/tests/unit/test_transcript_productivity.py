import json

from transcript_productivity import count_transcript_assistant_work_entries


def write_transcript_entries(transcript_file, entries):
    transcript_file.write_text("".join(f"{json.dumps(entry)}\n" for entry in entries))


def test_metadata_and_an_api_error_contain_no_assistant_work(tmp_path):
    transcript_file = tmp_path / "session.jsonl"
    write_transcript_entries(
        transcript_file,
        [
            {"type": "file-history-snapshot"},
            {"type": "user"},
            {"type": "attachment"},
            {"type": "assistant", "isApiErrorMessage": True},
        ],
    )

    assert count_transcript_assistant_work_entries(str(transcript_file)) == 0


def test_a_normal_assistant_response_is_work(tmp_path):
    transcript_file = tmp_path / "session.jsonl"
    write_transcript_entries(
        transcript_file,
        [{"type": "assistant", "isApiErrorMessage": False}],
    )

    assert count_transcript_assistant_work_entries(str(transcript_file)) == 1


def test_a_tool_using_assistant_response_is_work(tmp_path):
    transcript_file = tmp_path / "session.jsonl"
    write_transcript_entries(
        transcript_file,
        [
            {
                "type": "assistant",
                "message": {"content": [{"type": "tool_use"}]},
            }
        ],
    )

    assert count_transcript_assistant_work_entries(str(transcript_file)) == 1
