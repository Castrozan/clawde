import json
import sys
from collections.abc import Iterable


def extract_assistant_reply(output_lines: Iterable[str]) -> str:
    reply_parts: dict[str, str] = {}
    completed = False
    step_open = False
    for line in output_lines:
        if not line.strip():
            continue
        event = json.loads(line)
        if not isinstance(event, dict):
            raise ValueError("OpenCode emitted an invalid turn event")
        event_type = event.get("type")
        if event_type == "error":
            raise ValueError(
                f"OpenCode turn failed: {event.get('error', 'unknown error')}"
            )
        part = event.get("part", {})
        if not isinstance(part, dict):
            raise ValueError("OpenCode emitted an invalid message part")
        if event_type == "step_start":
            reply_parts.clear()
            completed = False
            step_open = True
        elif event_type == "text":
            if (
                not step_open
                or not isinstance(part.get("text"), str)
                or not isinstance(part.get("id"), str)
            ):
                raise ValueError("OpenCode emitted an invalid assistant text part")
            reply_parts[part["id"]] = part["text"]
        elif event_type == "step_finish":
            if not step_open:
                raise ValueError("OpenCode finished a step that never started")
            step_open = False
            completed = part.get("reason") == "stop"
            if not completed:
                reply_parts.clear()
    if not completed:
        raise ValueError("OpenCode did not complete a final assistant turn")
    return "\n".join(reply_parts.values())


def main() -> int:
    try:
        reply = extract_assistant_reply(sys.stdin)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    sys.stdout.write(reply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
