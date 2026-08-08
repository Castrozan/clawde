import argparse

from agent_process_tree import terminate_process_tree
from agent_wrapper_processes import find_wrapper_process_id_for_agent
from clawde_runtime_layout import deployed_agent_names


def refuse_when_agent_is_not_deployed(agent_name: str) -> None:
    deployed_names = deployed_agent_names()
    if agent_name in deployed_names:
        return
    raise SystemExit(
        f"Agent {agent_name} is not deployed on this machine, so there is no wrapper "
        f"to restart. Deployed agents: {', '.join(deployed_names) or 'none'}."
    )


def refuse_when_agent_holds_no_wrapper(agent_name: str) -> int:
    wrapper_process_id = find_wrapper_process_id_for_agent(agent_name)
    if wrapper_process_id is not None:
        return wrapper_process_id
    raise SystemExit(
        f"Agent {agent_name} is deployed but holds no wrapper process, so there is "
        "nothing to restart. It is on demand and stopped, outside its active hours, "
        "or already down, and the supervisor brings it back up on its next poll."
    )


def restart_agent(agent_name: str) -> None:
    refuse_when_agent_is_not_deployed(agent_name)
    wrapper_process_id = refuse_when_agent_holds_no_wrapper(agent_name)
    terminate_process_tree(wrapper_process_id)
    print(
        f"Restarted {agent_name}: terminated wrapper {wrapper_process_id} and the "
        "harness under it. The supervisor relaunches the agent into its existing "
        "window on its next poll, reading the current wrapper code and per-agent "
        "config and resuming its pinned session."
    )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="clawde restart",
        description="Restart a deployed clawde agent by terminating its wrapper and "
        "the harness under it, so the supervisor relaunches it on its next poll. Use "
        "this to adopt new wrapper code, which a running wrapper never picks up on "
        "its own because it keeps executing whatever it launched with. The agent "
        "resumes its pinned session, so the conversation survives the restart.",
    )
    parser.add_argument("agent_name", help="Name of the deployed agent")
    return parser.parse_args()


def main() -> None:
    restart_agent(parse_arguments().agent_name)


if __name__ == "__main__":
    main()
