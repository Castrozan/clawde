import argparse

import pytest
from a2a_server.__main__ import construct_backend_from_arguments
from a2a_server.backends.herdr_backend import HerdrAttachedAgentBackend
from a2a_server.backends.subprocess_backend import SubprocessAgentBackend
from a2a_server.backends.tmux_backend import TmuxAttachedAgentBackend


def command_line(**overrides) -> argparse.Namespace:
    return argparse.Namespace(
        **{
            "backend_type": None,
            "meaningful_line_pattern": None,
            "tmux_session_name": None,
            "tmux_window_name": None,
            "herdr_workspace_label": None,
            "herdr_tab_label": None,
            "subprocess_command": None,
            **overrides,
        }
    )


class TestConstructBackendFromArguments:
    def test_builds_a_herdr_backend_from_the_workspace_and_tab_labels(self):
        backend = construct_backend_from_arguments(
            command_line(
                backend_type="herdr",
                herdr_workspace_label="clawde",
                herdr_tab_label="jenny",
            )
        )
        assert isinstance(backend, HerdrAttachedAgentBackend)

    def test_builds_a_tmux_backend_from_the_session_and_window_names(self):
        backend = construct_backend_from_arguments(
            command_line(
                backend_type="tmux",
                tmux_session_name="clawde",
                tmux_window_name="jenny",
            )
        )
        assert isinstance(backend, TmuxAttachedAgentBackend)

    def test_builds_a_subprocess_backend_from_the_command_argv(self):
        backend = construct_backend_from_arguments(
            command_line(backend_type="subprocess", subprocess_command=["echo", "hi"])
        )
        assert isinstance(backend, SubprocessAgentBackend)

    def test_compiles_the_meaningful_line_pattern_it_is_given(self):
        backend = construct_backend_from_arguments(
            command_line(
                backend_type="herdr",
                herdr_workspace_label="clawde",
                herdr_tab_label="jenny",
                meaningful_line_pattern=r"^⏺ ",
            )
        )
        assert backend._meaningful_line_tracker is not None

    @pytest.mark.parametrize(
        "incomplete_command_line",
        [
            {"backend_type": "herdr", "herdr_workspace_label": "clawde"},
            {"backend_type": "herdr", "herdr_tab_label": "jenny"},
            {"backend_type": "tmux", "tmux_session_name": "clawde"},
            {"backend_type": "tmux", "tmux_window_name": "jenny"},
            {"backend_type": "subprocess"},
        ],
    )
    def test_refuses_to_start_without_the_arguments_the_backend_needs(
        self, incomplete_command_line
    ):
        with pytest.raises(SystemExit) as raised:
            construct_backend_from_arguments(command_line(**incomplete_command_line))
        assert raised.value.code == 2
