import importlib.util
import json
from pathlib import Path

import pytest


specification = importlib.util.spec_from_file_location(
    "opencode_channel_output",
    Path(__file__).resolve().parents[4]
    / "harnesses/opencode/scripts/extract-reply-from-run-output.py",
)
parser = importlib.util.module_from_spec(specification)
specification.loader.exec_module(parser)


def output_event(kind, **part):
    return json.dumps({"type": kind, "part": part}) + "\n"


def extract(*events):
    return parser.extract_assistant_reply(iter(events))


def test_only_the_final_assistant_step_reaches_the_channel():
    assert (
        extract(
            output_event("step_start"),
            output_event("text", id="one", text="I will inspect a file"),
            output_event("tool_use", state={"output": "private tool output"}),
            output_event("step_finish", reason="tool-calls"),
            output_event("step_start"),
            output_event("reasoning", text="private reasoning"),
            output_event("text", id="two", text="public answer"),
            output_event("step_finish", reason="stop"),
        )
        == "public answer"
    )


def test_a_completed_empty_final_step_is_silence():
    assert (
        extract(
            output_event("step_start"),
            output_event("text", id="one", text="intermediate commentary"),
            output_event("step_finish", reason="tool-calls"),
            output_event("step_start"),
            output_event("step_finish", reason="stop"),
        )
        == ""
    )


def test_repeated_text_events_do_not_duplicate_the_reply():
    assert (
        extract(
            output_event("step_start"),
            output_event("text", id="one", text="hello"),
            output_event("text", id="one", text="hello"),
            output_event("step_finish", reason="stop"),
        )
        == "hello"
    )


@pytest.mark.parametrize(
    "events",
    [
        [],
        ["terminal diagnostic"],
        ["[]"],
        [output_event("text", id="one", text="unfinished")],
        [output_event("step_finish", reason="tool-calls")],
        [output_event("step_finish", reason="length")],
        [output_event("step_finish", reason="stop")],
        [
            output_event("step_start"),
            output_event("step_finish", reason="stop"),
            output_event("text", id="late", text="uncompleted"),
        ],
        [output_event("step_start"), output_event("text", id="one", text=42)],
        [json.dumps({"type": "error", "error": {"data": {"message": "quota"}}})],
        [output_event("step_finish", reason="stop"), json.dumps({"type": "error"})],
    ],
)
def test_missing_malformed_and_failed_completions_are_not_silent_success(events):
    with pytest.raises(ValueError):
        extract(*events)
