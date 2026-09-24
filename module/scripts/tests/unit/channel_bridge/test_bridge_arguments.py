import sys

from .discord_bridge_test_support import load_bridge_module


def test_the_bridge_parses_the_daily_session_rotation_flag(monkeypatch):
    bridge = load_bridge_module()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bridge.py",
            "--agent-name",
            "agent-a",
            "--launch-config",
            "/tmp/launch-config/agent-a.json",
            "--workspace-directory",
            "/tmp",
            "--state-directory",
            "/tmp",
            "--daily-session-rotation",
        ],
    )

    arguments = bridge.parse_arguments()

    assert arguments.daily_session_rotation is True


def test_the_bridge_defaults_to_no_daily_session_rotation(monkeypatch):
    bridge = load_bridge_module()
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bridge.py",
            "--agent-name",
            "agent-a",
            "--launch-config",
            "/tmp/launch-config/agent-a.json",
            "--workspace-directory",
            "/tmp",
            "--state-directory",
            "/tmp",
        ],
    )

    arguments = bridge.parse_arguments()

    assert arguments.daily_session_rotation is False
