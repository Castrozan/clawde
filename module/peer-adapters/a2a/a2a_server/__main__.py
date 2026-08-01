import argparse
import re
import sys

from .a2a_server import run_a2a_server_blocking
from .agent_card import build_agent_card_from_environment
from .backends.base import AgentBackend
from .backends.herdr_backend import HerdrAttachedAgentBackend
from .backends.subprocess_backend import SubprocessAgentBackend
from .backends.tmux_backend import TmuxAttachedAgentBackend


def parse_command_line_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="a2a-server",
        description=(
            "HTTP server that exposes a single CLI agent as an A2A peer. "
            "Wraps an agent already running in a tmux window or a herdr tab, "
            "or a subprocess agent it starts itself."
        ),
    )
    parser.add_argument("--agent-name", required=True)
    parser.add_argument("--agent-description", default="A CLI agent exposed via A2A.")
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, required=True)
    parser.add_argument(
        "--public-endpoint-url",
        default=None,
        help="URL advertised in the Agent Card. Defaults to http://<listen-host>:<listen-port>.",
    )
    parser.add_argument(
        "--backend-type",
        choices=["tmux", "herdr", "subprocess"],
        required=True,
    )
    parser.add_argument(
        "--meaningful-line-pattern",
        default=None,
        help=(
            "Optional regex. When set, only pane lines matching this pattern count as "
            "meaningful new output; status-line/spinner redraws are ignored so the idle "
            "auto-complete timeout actually fires. For claude-code TUI, use '^⏺ '."
        ),
    )
    parser.add_argument("--tmux-session-name", default=None)
    parser.add_argument("--tmux-window-name", default=None)
    parser.add_argument("--herdr-workspace-label", default=None)
    parser.add_argument("--herdr-tab-label", default=None)
    parser.add_argument(
        "--subprocess-command",
        nargs="+",
        default=None,
        help="argv for the subprocess backend (everything after this flag is the command)",
    )
    return parser.parse_args()


def exit_because_required_arguments_are_missing(missing_arguments: str) -> None:
    print(f"error: {missing_arguments}", file=sys.stderr)
    sys.exit(2)


def compile_meaningful_line_pattern(pattern: str | None) -> re.Pattern | None:
    return re.compile(pattern) if pattern else None


def construct_tmux_backend(arguments: argparse.Namespace) -> AgentBackend:
    if not arguments.tmux_session_name or not arguments.tmux_window_name:
        exit_because_required_arguments_are_missing(
            "--tmux-session-name and --tmux-window-name are required for backend-type=tmux"
        )
    return TmuxAttachedAgentBackend(
        tmux_session_name=arguments.tmux_session_name,
        tmux_window_name=arguments.tmux_window_name,
        meaningful_line_pattern=compile_meaningful_line_pattern(
            arguments.meaningful_line_pattern
        ),
    )


def construct_herdr_backend(arguments: argparse.Namespace) -> AgentBackend:
    if not arguments.herdr_workspace_label or not arguments.herdr_tab_label:
        exit_because_required_arguments_are_missing(
            "--herdr-workspace-label and --herdr-tab-label are required for backend-type=herdr"
        )
    return HerdrAttachedAgentBackend(
        workspace_label=arguments.herdr_workspace_label,
        tab_label=arguments.herdr_tab_label,
        meaningful_line_pattern=compile_meaningful_line_pattern(
            arguments.meaningful_line_pattern
        ),
    )


def construct_subprocess_backend(arguments: argparse.Namespace) -> AgentBackend:
    if not arguments.subprocess_command:
        exit_because_required_arguments_are_missing(
            "--subprocess-command is required for backend-type=subprocess"
        )
    return SubprocessAgentBackend(command_argv=arguments.subprocess_command)


def construct_backend_from_arguments(arguments: argparse.Namespace) -> AgentBackend:
    backend_constructors = {
        "tmux": construct_tmux_backend,
        "herdr": construct_herdr_backend,
        "subprocess": construct_subprocess_backend,
    }
    return backend_constructors[arguments.backend_type](arguments)


def main() -> None:
    arguments = parse_command_line_arguments()
    endpoint_url = (
        arguments.public_endpoint_url
        or f"http://{arguments.listen_host}:{arguments.listen_port}"
    )
    agent_card = build_agent_card_from_environment(
        agent_name=arguments.agent_name,
        description=arguments.agent_description,
        endpoint_url=endpoint_url,
    )
    backend = construct_backend_from_arguments(arguments)
    run_a2a_server_blocking(
        host=arguments.listen_host,
        port=arguments.listen_port,
        agent_card=agent_card,
        agent_backend=backend,
    )


if __name__ == "__main__":
    main()
