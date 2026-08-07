import datetime

from active_harness import (
    active_harness_name_for_launch_config,
    clear_override,
    declared_harness_name,
    eligible_harness_names,
    harness_override_has_expired,
    override_file_path_for_launch_config,
    read_harness_override,
    runtime_root_directory_from_launch_config_path,
    write_overridden_harness_name,
)
from agent_log import emit_timestamped_log
from harness_productivity_record import (
    begin_harness_productivity_record,
    consecutive_unproductive_turns,
    harness_is_refusing_work,
    harness_productivity_record_path,
    read_harness_productivity_record,
)

FALLBACK_CHAIN_LAUNCH_CONFIG_KEY = "harness_fallback_chain"
FAILOVER_OVERRIDE_LIFETIME_HOURS = 24


def declared_fallback_chain(launch_config: dict) -> list[str]:
    declared_chain = launch_config.get(FALLBACK_CHAIN_LAUNCH_CONFIG_KEY)
    return declared_chain if isinstance(declared_chain, list) else []


def failover_rotation(launch_config: dict) -> list[str]:
    eligible = eligible_harness_names(launch_config)
    rotation: list[str] = []
    for harness_name in [
        declared_harness_name(launch_config),
        *declared_fallback_chain(launch_config),
    ]:
        if harness_name in eligible and harness_name not in rotation:
            rotation.append(harness_name)
    return rotation


def next_harness_after_refusal(
    launch_config: dict, active_harness_name: str
) -> str | None:
    rotation = failover_rotation(launch_config)
    if len(rotation) < 2:
        return None
    if active_harness_name not in rotation:
        return rotation[0]
    return rotation[(rotation.index(active_harness_name) + 1) % len(rotation)]


def fail_over_to_harness(
    override_file_path: str,
    next_harness_name: str,
    superseded_harness_name: str,
    now: datetime.datetime | None = None,
) -> None:
    write_overridden_harness_name(
        override_file_path,
        next_harness_name,
        expires_at=(now or datetime.datetime.now())
        + datetime.timedelta(hours=FAILOVER_OVERRIDE_LIFETIME_HOURS),
        superseded_harness_name=superseded_harness_name,
    )


def return_agent_to_declared_harness_when_failover_elapsed(
    agent_name: str, override_file_path: str
) -> None:
    if not harness_override_has_expired(read_harness_override(override_file_path)):
        return
    clear_override(override_file_path)
    emit_timestamped_log(
        agent_name,
        "harness failover window elapsed. Returning to its declared harness to "
        "find out whether it accepts work again.",
    )


def harness_for_next_launch(
    agent_name: str, launch_config: dict, launch_config_path: str
) -> str:
    override_file_path = override_file_path_for_launch_config(launch_config_path)
    return_agent_to_declared_harness_when_failover_elapsed(
        agent_name, override_file_path
    )

    active_harness_name = active_harness_name_for_launch_config(
        launch_config, launch_config_path
    )
    next_harness_name = next_harness_after_refusal(launch_config, active_harness_name)
    if next_harness_name is None:
        return active_harness_name

    productivity_record_path = harness_productivity_record_path(
        runtime_root_directory_from_launch_config_path(launch_config_path), agent_name
    )
    if not harness_is_refusing_work(
        read_harness_productivity_record(productivity_record_path), active_harness_name
    ):
        return active_harness_name

    fail_over_to_harness(override_file_path, next_harness_name, active_harness_name)
    begin_harness_productivity_record(productivity_record_path, next_harness_name)
    emit_timestamped_log(
        agent_name,
        f"moved off {active_harness_name} onto {next_harness_name} because "
        f"{active_harness_name} stopped producing turns. It goes back to its "
        f"declared harness once the failover window elapses.",
    )
    return next_harness_name


def build_refusing_harness_replacement_reason(
    productivity_record_path: str,
    active_harness_name: str,
    next_harness_name: str | None,
):
    if next_harness_name is None:
        return None

    def reason_to_replace_session() -> str | None:
        record = read_harness_productivity_record(productivity_record_path)
        if not harness_is_refusing_work(record, active_harness_name):
            return None
        return (
            f"Agent produced nothing across {consecutive_unproductive_turns(record)} "
            f"consecutive heartbeats on {active_harness_name}, so that harness is "
            f"refusing work. Failing over to {next_harness_name}"
        )

    return reason_to_replace_session
