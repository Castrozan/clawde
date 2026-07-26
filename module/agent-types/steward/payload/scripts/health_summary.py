import json
from pathlib import Path

HEALTH_CHECK_TIMEOUT_SECONDS = 60


NON_FAILING_PROBE_STATUSES = ("pass", "skip")


def is_own_daemon_self_probe(probe: dict) -> bool:
    return probe.get("category") == "daemon" and "clawde agent: steward" in probe.get(
        "name", ""
    )


def is_failing_probe(probe: dict) -> bool:
    return probe.get("status", "pass") not in NON_FAILING_PROBE_STATUSES


def health_check_summary(run_capturing) -> dict:
    return_code, output = run_capturing(
        ["health-check", "--json"], Path.home(), HEALTH_CHECK_TIMEOUT_SECONDS
    )
    if return_code == 127:
        return {"available": False}
    try:
        parsed = json.loads(output)
    except json.JSONDecodeError:
        return {"available": True, "parse_error": True, "exit_code": return_code}
    probes = parsed if isinstance(parsed, list) else parsed.get("probes", [])
    failing = [
        probe
        for probe in probes
        if is_failing_probe(probe) and not is_own_daemon_self_probe(probe)
    ]
    skipped = [probe for probe in probes if probe.get("status") == "skip"]
    return {
        "available": True,
        "exit_code": return_code,
        "total": len(probes),
        "failing": [
            f"{probe.get('category', '?')}/{probe.get('name', '?')}"
            for probe in failing
        ],
        "skipped": [
            f"{probe.get('category', '?')}/{probe.get('name', '?')}"
            f" ({probe.get('reason', 'not applicable')})"
            for probe in skipped
        ],
    }
