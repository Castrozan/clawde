import os
import shlex
import subprocess
import sys

USAGE = """\
usage: clawde [command] [arguments...]

Manage the persistent Claude Code agents declared in the home-manager
configuration. With no command, start the supervised agents session, or the
default agent session.

Commands:
  active   Override an agent's active-hours gate so it runs now through the
           next active-hours start, or clear the override.
  harness  Show or switch the harness a deployed agent runs on.
  list     List every deployed agent with its active-hours window, override,
           and on-demand state.
  start    Start an on-demand agent on a lease the supervisor honours until it
           goes idle past its timeout.
  stop     Stop an on-demand agent, preserving its session for the next start.
  help     Show this help.

Run 'clawde <command> --help' for command-specific help.
"""

HELP_ARGUMENTS = ("--help", "-h", "help")

SUBCOMMAND_SCRIPT_PATHS = {
    "active": ("activate_after_hours.py", False),
    "harness": ("harness_control.py", False),
    "list": ("list_agents.py", False),
    "start": ("on_demand_control.py", True),
    "stop": ("on_demand_control.py", True),
}


def substitute_uid_token_into_service_restart_command(
    service_restart_command: str,
) -> str:
    return service_restart_command.replace("UID", str(os.getuid()))


def start_supervised_agents_session(
    tmux_bin_path: str, default_session_name: str, service_restart_command: str
) -> int:
    session_probe = subprocess.run(
        [tmux_bin_path, "has-session", "-t", default_session_name],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if session_probe.returncode == 0:
        print(
            f"Session {default_session_name} already running. "
            f"Attach with: tmux attach -t {default_session_name}",
            file=sys.stderr,
        )
        return 0
    restart_result = subprocess.run(
        shlex.split(
            substitute_uid_token_into_service_restart_command(service_restart_command)
        )
    )
    return restart_result.returncode


def dispatch_to_subcommand_script(
    agent_wrapper_directory: str, script_name: str, forwarded_arguments: list[str]
) -> int:
    script_path = f"{agent_wrapper_directory}/{script_name}"
    os.execvpe(
        sys.executable, [sys.executable, script_path, *forwarded_arguments], os.environ
    )
    return 0


def main(arguments: list[str]) -> int:
    if not arguments:
        return start_supervised_agents_session(
            os.environ["TMUX_BIN"],
            os.environ["DEFAULT_TMUX_SESSION_NAME"],
            os.environ["CLAWDE_SERVICE_RESTART_COMMAND"],
        )
    if arguments[0] in HELP_ARGUMENTS:
        print(USAGE)
        return 0
    if arguments[0] in SUBCOMMAND_SCRIPT_PATHS:
        script_name, keeps_subcommand_word = SUBCOMMAND_SCRIPT_PATHS[arguments[0]]
        forwarded_arguments = arguments if keeps_subcommand_word else arguments[1:]
        return dispatch_to_subcommand_script(
            os.environ["CLAWDE_AGENT_WRAPPER_DIR"], script_name, forwarded_arguments
        )
    print(f"clawde: unknown command {arguments[0]!r}", file=sys.stderr)
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
