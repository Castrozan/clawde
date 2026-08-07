import datetime

from active_harness import (
    active_harness_name_for_launch_config,
    override_file_path_for_launch_config,
    read_harness_override,
)
from harness_failover_test_support import (
    AT_NOON,
    STEWARD_LAUNCH_CONFIG,
    deploy_launch_config,
    harness_failover,
    park_agent_on_its_harness,
)
from harness_productivity_record import (
    CONSECUTIVE_UNPRODUCTIVE_TURNS_BEFORE_FAILOVER,
    begin_harness_productivity_record,
    harness_productivity_record_path,
    read_harness_productivity_record,
    record_observed_heartbeat_turn,
)


def test_a_refusing_harness_moves_the_agent_onto_the_next_one(tmp_path):
    launch_config_path = deploy_launch_config(tmp_path, STEWARD_LAUNCH_CONFIG)
    park_agent_on_its_harness(tmp_path, "opencode")

    assert (
        harness_failover.harness_for_next_launch(
            "steward", STEWARD_LAUNCH_CONFIG, launch_config_path
        )
        == "codex"
    )
    assert (
        active_harness_name_for_launch_config(STEWARD_LAUNCH_CONFIG, launch_config_path)
        == "codex"
    )


def test_the_failover_records_where_the_agent_came_from_and_when_it_returns(tmp_path):
    launch_config_path = deploy_launch_config(tmp_path, STEWARD_LAUNCH_CONFIG)
    park_agent_on_its_harness(tmp_path, "opencode")
    harness_failover.harness_for_next_launch(
        "steward", STEWARD_LAUNCH_CONFIG, launch_config_path
    )

    override = read_harness_override(
        override_file_path_for_launch_config(launch_config_path)
    )
    assert override["superseded_harness"] == "opencode"
    assert override["expires_at"] > datetime.datetime.now().isoformat()


def test_the_failover_resets_the_run_so_the_fresh_harness_starts_clean(tmp_path):
    launch_config_path = deploy_launch_config(tmp_path, STEWARD_LAUNCH_CONFIG)
    record_path = park_agent_on_its_harness(tmp_path, "opencode")
    harness_failover.harness_for_next_launch(
        "steward", STEWARD_LAUNCH_CONFIG, launch_config_path
    )

    record = read_harness_productivity_record(record_path)
    assert (record["harness"], record["consecutive_unproductive_turns"]) == ("codex", 0)


def test_a_productive_harness_is_left_alone(tmp_path):
    launch_config_path = deploy_launch_config(tmp_path, STEWARD_LAUNCH_CONFIG)
    begin_harness_productivity_record(
        harness_productivity_record_path(str(tmp_path), "steward"), "opencode", AT_NOON
    )

    assert (
        harness_failover.harness_for_next_launch(
            "steward", STEWARD_LAUNCH_CONFIG, launch_config_path
        )
        == "opencode"
    )


def test_an_elapsed_failover_returns_the_agent_to_its_declared_harness(tmp_path):
    launch_config_path = deploy_launch_config(tmp_path, STEWARD_LAUNCH_CONFIG)
    harness_failover.fail_over_to_harness(
        override_file_path_for_launch_config(launch_config_path),
        "codex",
        "opencode",
        now=datetime.datetime.now()
        - datetime.timedelta(
            hours=harness_failover.FAILOVER_OVERRIDE_LIFETIME_HOURS + 1
        ),
    )

    assert (
        harness_failover.harness_for_next_launch(
            "steward", STEWARD_LAUNCH_CONFIG, launch_config_path
        )
        == "opencode"
    )
    assert (
        read_harness_override(override_file_path_for_launch_config(launch_config_path))
        == {}
    )


def test_a_live_failover_survives_a_supervisor_restart(tmp_path):
    launch_config_path = deploy_launch_config(tmp_path, STEWARD_LAUNCH_CONFIG)
    harness_failover.fail_over_to_harness(
        override_file_path_for_launch_config(launch_config_path), "codex", "opencode"
    )

    assert (
        harness_failover.harness_for_next_launch(
            "steward", STEWARD_LAUNCH_CONFIG, launch_config_path
        )
        == "codex"
    ), (
        "the wrapper re-reads this decision on every restart, so a failover that "
        "did not outlive the restart would bounce the agent straight back onto the "
        "harness that is refusing work"
    )


def test_no_replacement_reason_is_built_when_there_is_nowhere_to_move(tmp_path):
    assert (
        harness_failover.build_refusing_harness_replacement_reason(
            str(tmp_path / "unused.json"), "opencode", None
        )
        is None
    )


def test_the_replacement_reason_fires_only_once_the_harness_is_refusing_work(tmp_path):
    record_path = harness_productivity_record_path(str(tmp_path), "steward")
    begin_harness_productivity_record(record_path, "opencode", AT_NOON)
    reason_to_replace_session = (
        harness_failover.build_refusing_harness_replacement_reason(
            record_path, "opencode", "codex"
        )
    )

    assert reason_to_replace_session() is None
    for _turn in range(CONSECUTIVE_UNPRODUCTIVE_TURNS_BEFORE_FAILOVER):
        record_observed_heartbeat_turn(record_path, False, AT_NOON)
    assert "codex" in reason_to_replace_session()
