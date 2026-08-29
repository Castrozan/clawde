import json
import sys

ALLOWED_ACTIONS = {"silence", "reply"}


def read_structured_output(structured_output_path):
    with open(structured_output_path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def is_valid_envelope(envelope):
    if not isinstance(envelope, dict):
        return False
    if set(envelope.keys()) != {"action", "text"}:
        return False
    action = envelope.get("action")
    text = envelope.get("text")
    if action not in ALLOWED_ACTIONS:
        return False
    if not isinstance(text, str):
        return False
    if action == "silence" and text != "":
        return False
    if action == "reply" and text == "":
        return False
    return True


def write_public_reply(reply_path, text):
    with open(reply_path, "w", encoding="utf-8") as handle:
        handle.write(text)


def main(argv):
    if len(argv) != 3:
        return 2
    structured_output_path = argv[1]
    reply_path = argv[2]
    try:
        envelope = read_structured_output(structured_output_path)
    except (json.JSONDecodeError, OSError):
        return 1
    if not is_valid_envelope(envelope):
        return 1
    if envelope["action"] == "reply":
        write_public_reply(reply_path, envelope["text"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
