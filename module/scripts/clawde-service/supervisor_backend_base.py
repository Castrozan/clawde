import os

BOOTSTRAP_PLACEHOLDER_WINDOW_NAME = "__bootstrap__"
MULTIPLEXER_ENVIRONMENT_VARIABLE = "CLAWDE_MULTIPLEXER"
DEFAULT_MULTIPLEXER = "tmux"


class SupervisorMultiplexerBackend:
    def ensure_host_ready(self, session_name: str) -> bool:
        raise NotImplementedError

    def agent_window_exists(self, session_name: str, agent_name: str) -> bool:
        raise NotImplementedError

    def create_agent_window(
        self, session_name: str, agent_name: str, wrapper_command: str
    ) -> bool:
        raise NotImplementedError

    def relaunch_wrapper_in_window(
        self, session_name: str, agent_name: str, wrapper_command: str
    ) -> bool:
        raise NotImplementedError

    def remove_bootstrap_scaffolding(self, session_name: str) -> None:
        raise NotImplementedError

    def ensure_agent_window(
        self, session_name: str, agent_name: str, wrapper_command: str
    ) -> bool:
        if self.agent_window_exists(session_name, agent_name):
            return self.relaunch_wrapper_in_window(
                session_name, agent_name, wrapper_command
            )
        return self.create_agent_window(session_name, agent_name, wrapper_command)


def select_supervisor_backend() -> SupervisorMultiplexerBackend:
    multiplexer = os.environ.get(MULTIPLEXER_ENVIRONMENT_VARIABLE, DEFAULT_MULTIPLEXER)
    if multiplexer == "herdr":
        from supervisor_backend_herdr import HerdrSupervisorBackend

        return HerdrSupervisorBackend()
    from supervisor_backend_tmux import TmuxSupervisorBackend

    return TmuxSupervisorBackend()
