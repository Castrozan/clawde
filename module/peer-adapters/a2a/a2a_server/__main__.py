import argparse
from pathlib import Path

from .fleet.daemon import run_fleet_daemon_blocking

DEFAULT_LISTEN_HOST = "127.0.0.1"
DEFAULT_LISTEN_PORT = 7000


def parse_command_line_arguments(argument_list=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="a2a_server",
        description="Serve every herdr pane running an agent as an A2A peer.",
    )
    parser.add_argument("--listen-host", default=DEFAULT_LISTEN_HOST)
    parser.add_argument("--listen-port", type=int, default=DEFAULT_LISTEN_PORT)
    parser.add_argument("--public-base-url", default=None)
    parser.add_argument("--agent-metadata-file", default=None)
    return parser.parse_args(argument_list)


def resolve_public_base_url(arguments: argparse.Namespace) -> str:
    if arguments.public_base_url:
        return arguments.public_base_url.rstrip("/")
    return f"http://{arguments.listen_host}:{arguments.listen_port}"


def main(argument_list=None) -> None:
    arguments = parse_command_line_arguments(argument_list)
    run_fleet_daemon_blocking(
        arguments.listen_host,
        arguments.listen_port,
        resolve_public_base_url(arguments),
        Path(arguments.agent_metadata_file) if arguments.agent_metadata_file else None,
    )


if __name__ == "__main__":
    main()
