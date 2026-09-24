import json
import subprocess
import sys
from pathlib import Path

import pytest

PARSER_PATH = (
    Path(__file__).resolve().parents[4]
    / "harnesses/claude/scripts/extract-channel-reply.py"
)


def run_parser(payload):
    return subprocess.run(
        [sys.executable, str(PARSER_PATH)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("reply", ["", "public reply"])
def test_only_a_successful_result_is_published(reply):
    result = run_parser(
        {"type": "result", "subtype": "success", "is_error": False, "result": reply}
    )
    assert result.returncode == 0
    assert result.stdout == reply


@pytest.mark.parametrize(
    "payload",
    [
        {},
        [],
        {"type": "result", "subtype": "success", "is_error": True, "result": "quota"},
        {"type": "result", "subtype": "error_max_turns", "result": "partial reply"},
        {"type": "assistant", "result": "intermediate reply"},
        {"type": "result", "subtype": "success", "is_error": False},
        {"type": "result", "subtype": "success", "is_error": False, "result": 42},
    ],
)
def test_unsuccessful_or_missing_results_never_become_public_text(payload):
    result = run_parser(payload)
    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr
