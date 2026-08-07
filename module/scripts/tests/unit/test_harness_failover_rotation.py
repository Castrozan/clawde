from harness_failover_test_support import STEWARD_LAUNCH_CONFIG, harness_failover


def test_the_rotation_starts_at_the_declared_harness():
    assert harness_failover.failover_rotation(STEWARD_LAUNCH_CONFIG) == [
        "opencode",
        "codex",
        "claude",
    ]


def test_a_fallback_the_agent_is_not_eligible_for_is_dropped_from_the_rotation():
    launch_config = STEWARD_LAUNCH_CONFIG | {
        "harness_launch_commands": {"opencode": "opencode", "codex": "codex"}
    }
    assert harness_failover.failover_rotation(launch_config) == ["opencode", "codex"]


def test_a_fallback_repeating_the_declared_harness_is_not_visited_twice():
    launch_config = STEWARD_LAUNCH_CONFIG | {
        "harness_fallback_chain": ["opencode", "codex"]
    }
    assert harness_failover.failover_rotation(launch_config) == ["opencode", "codex"]


def test_the_next_harness_follows_the_declared_order():
    assert (
        harness_failover.next_harness_after_refusal(STEWARD_LAUNCH_CONFIG, "opencode")
        == "codex"
    )
    assert (
        harness_failover.next_harness_after_refusal(STEWARD_LAUNCH_CONFIG, "codex")
        == "claude"
    )


def test_the_last_fallback_wraps_back_to_the_declared_harness():
    assert (
        harness_failover.next_harness_after_refusal(STEWARD_LAUNCH_CONFIG, "claude")
        == "opencode"
    ), (
        "an agent whose whole chain is refusing work must keep cycling rather than "
        "stop on the last entry, because the harness it started on is the one most "
        "likely to have recovered by the time the chain runs out"
    )


def test_an_agent_without_a_chain_has_nowhere_to_fail_over_to():
    launch_config = STEWARD_LAUNCH_CONFIG | {"harness_fallback_chain": []}
    assert (
        harness_failover.next_harness_after_refusal(launch_config, "opencode") is None
    )


def test_a_manually_pinned_harness_outside_the_rotation_falls_back_to_the_declared_one():
    assert (
        harness_failover.next_harness_after_refusal(
            STEWARD_LAUNCH_CONFIG | {"harness_fallback_chain": ["codex"]}, "claude"
        )
        == "opencode"
    )
