import json
import pathlib
import subprocess
import sys

PARSER_PATH = (
    pathlib.Path(__file__).resolve().parents[3]
    / "harnesses"
    / "codex"
    / "scripts"
    / "publish-codex-structured-reply.py"
)


def run_parser(structured_path, reply_path):
    return subprocess.run(
        [sys.executable, str(PARSER_PATH), str(structured_path), str(reply_path)],
        capture_output=True,
        text=True,
    )


def write_structured_output(structured_path, envelope):
    structured_path.write_text(json.dumps(envelope), encoding="utf-8")


def test_publishes_only_the_reply_text_for_a_valid_reply(tmp_path):
    structured_path = tmp_path / "codex-raw.json"
    reply_path = tmp_path / "reply.txt"
    write_structured_output(structured_path, {"action": "reply", "text": "hello world"})

    result = run_parser(structured_path, reply_path)

    assert result.returncode == 0
    assert reply_path.read_text(encoding="utf-8") == "hello world"


def test_publishes_no_content_for_a_valid_silence(tmp_path):
    structured_path = tmp_path / "codex-raw.json"
    reply_path = tmp_path / "reply.txt"
    write_structured_output(structured_path, {"action": "silence", "text": ""})

    result = run_parser(structured_path, reply_path)

    assert result.returncode == 0
    assert not reply_path.exists()


def test_fails_closed_on_malformed_json(tmp_path):
    structured_path = tmp_path / "codex-raw.json"
    reply_path = tmp_path / "reply.txt"
    structured_path.write_text("{not valid json", encoding="utf-8")

    result = run_parser(structured_path, reply_path)

    assert result.returncode != 0
    assert not reply_path.exists()


def test_fails_closed_on_unknown_action(tmp_path):
    structured_path = tmp_path / "codex-raw.json"
    reply_path = tmp_path / "reply.txt"
    write_structured_output(structured_path, {"action": "shout", "text": "hello"})

    result = run_parser(structured_path, reply_path)

    assert result.returncode != 0
    assert not reply_path.exists()


def test_fails_closed_on_extra_keys(tmp_path):
    structured_path = tmp_path / "codex-raw.json"
    reply_path = tmp_path / "reply.txt"
    write_structured_output(
        structured_path, {"action": "reply", "text": "hello", "intent": "greeting"}
    )

    result = run_parser(structured_path, reply_path)

    assert result.returncode != 0
    assert not reply_path.exists()


def test_fails_closed_on_nonempty_silence(tmp_path):
    structured_path = tmp_path / "codex-raw.json"
    reply_path = tmp_path / "reply.txt"
    write_structured_output(structured_path, {"action": "silence", "text": "oops"})

    result = run_parser(structured_path, reply_path)

    assert result.returncode != 0
    assert not reply_path.exists()


def test_fails_closed_on_empty_reply(tmp_path):
    structured_path = tmp_path / "codex-raw.json"
    reply_path = tmp_path / "reply.txt"
    write_structured_output(structured_path, {"action": "reply", "text": ""})

    result = run_parser(structured_path, reply_path)

    assert result.returncode != 0
    assert not reply_path.exists()
