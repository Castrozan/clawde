import re
import sys

ANSI_ESCAPE_SEQUENCE = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")
SESSION_HEADER_LINE = re.compile(r"^>\s")


def strip_terminal_control_sequences(raw_output: str) -> str:
    return ANSI_ESCAPE_SEQUENCE.sub("", raw_output)


def lines_after_the_session_header(output_lines: list[str]) -> list[str]:
    for line_index, line in enumerate(output_lines):
        if SESSION_HEADER_LINE.match(line):
            return output_lines[line_index + 1 :]
    return output_lines


def extract_assistant_reply(raw_output: str) -> str:
    reply_lines = lines_after_the_session_header(
        strip_terminal_control_sequences(raw_output).splitlines()
    )
    return "\n".join(reply_lines).strip()


def main() -> None:
    sys.stdout.write(extract_assistant_reply(sys.stdin.read()))


if __name__ == "__main__":
    main()
