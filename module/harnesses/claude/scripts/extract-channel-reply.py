import json
import sys


def extract_assistant_reply(payload: object) -> str:
    if not isinstance(payload, dict) or payload.get("type") != "result":
        raise ValueError("Claude did not return a completed turn result")
    if payload.get("subtype") != "success" or payload.get("is_error") is not False:
        raise ValueError(
            f"Claude turn failed: {payload.get('subtype', 'unknown result')}"
        )
    reply = payload.get("result")
    if not isinstance(reply, str):
        raise ValueError("Claude turn result has no assistant text field")
    return reply


def main() -> int:
    try:
        reply = extract_assistant_reply(json.load(sys.stdin))
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    sys.stdout.write(reply)
    return 0


if __name__ == "__main__":
    sys.exit(main())
