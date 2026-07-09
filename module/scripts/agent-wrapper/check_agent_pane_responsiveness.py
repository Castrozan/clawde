import argparse
import sys
import time

from multiplexer_pane_capture import capture_pane_content
from stuck_indicators import pane_poll_is_stuck_evidence

SECONDS_BETWEEN_CAPTURES = 3
HEALTHY_EXIT_CODE = 0
UNRESPONSIVE_EXIT_CODE = 1


def determine_pane_health_exit_code(
    first_pane_content: str | None, second_pane_content: str | None
) -> int:
    if second_pane_content is None:
        return HEALTHY_EXIT_CODE
    if pane_poll_is_stuck_evidence(second_pane_content, first_pane_content):
        return UNRESPONSIVE_EXIT_CODE
    return HEALTHY_EXIT_CODE


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="check-agent-pane-responsiveness",
        description="Exit non-zero when a clawde agent's pane is unresponsive: "
        "frozen and not at the idle prompt across two captures, or showing a "
        "usage-limit modal. Captures twice so a working agent that merely mentions "
        "an error is not flagged. Captures via the active multiplexer backend "
        "(tmux or herdr) selected by CLAWDE_MULTIPLEXER.",
    )
    parser.add_argument(
        "--tmux-target",
        required=True,
        help="tmux target in session:window form for the agent pane to inspect",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    first_pane_content = capture_pane_content(arguments.tmux_target)
    time.sleep(SECONDS_BETWEEN_CAPTURES)
    second_pane_content = capture_pane_content(arguments.tmux_target)
    sys.exit(determine_pane_health_exit_code(first_pane_content, second_pane_content))


if __name__ == "__main__":
    main()
