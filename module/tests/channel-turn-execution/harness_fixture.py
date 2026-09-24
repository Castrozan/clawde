import json
import os
import sys
from pathlib import Path

harness, *arguments = sys.argv[1:]
reply = os.environ["FIXTURE_REPLY"]
envelope = json.loads(reply) if reply.startswith("{") else None
failure = os.environ.get("FIXTURE_FAILURE") == "1"

if harness == "codex":
    assert "--output-schema" in arguments
    output_path = arguments[arguments.index("--output-last-message") + 1]
    Path(output_path).write_text(reply)
elif harness == "claude":
    assert arguments[arguments.index("--output-format") + 1] == "json"
    schema = json.loads(arguments[arguments.index("--json-schema") + 1])
    assert set(schema["required"]) == {"action", "text"}
    print(
        json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": failure,
                "result": "private model narration",
                "structured_output": envelope,
            }
        )
    )
elif harness == "opencode":
    assert arguments[arguments.index("--format") + 1] == "json"
    events = [
        {"type": "step_start", "part": {}},
        {"type": "text", "part": {"id": "final", "text": reply}},
        {"type": "step_finish", "part": {"reason": "stop"}},
    ]
    if failure:
        events.append({"type": "error", "error": {"name": "ProviderError"}})
    for event in events:
        print(json.dumps(event))
sys.exit(3 if failure else 0)
