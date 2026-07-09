import os

from pane_content import HeartbeatMultiplexerBackend

MULTIPLEXER_ENVIRONMENT_VARIABLE = "CLAWDE_MULTIPLEXER"
DEFAULT_MULTIPLEXER = "tmux"


def select_heartbeat_backend() -> HeartbeatMultiplexerBackend:
    multiplexer = os.environ.get(MULTIPLEXER_ENVIRONMENT_VARIABLE, DEFAULT_MULTIPLEXER)
    if multiplexer == "herdr":
        from herdr import HerdrHeartbeatBackend

        return HerdrHeartbeatBackend()
    from tmux import TmuxHeartbeatBackend

    return TmuxHeartbeatBackend()
