import json

from steward_test_helpers import health_summary


def fake_run_capturing(return_code: int, output: str):
    def run(arguments, working_directory, timeout_seconds):
        return return_code, output

    return run


def test_health_check_summary_reports_failing_probes():
    probes = json.dumps(
        [
            {"category": "bin", "name": "a", "status": "pass"},
            {"category": "daemon", "name": "b", "status": "fail"},
        ]
    )
    summary = health_summary.health_check_summary(fake_run_capturing(1, probes))
    assert summary["available"] is True
    assert summary["failing"] == ["daemon/b"]


def test_health_check_summary_ignores_own_daemon_self_probe():
    probes = json.dumps(
        [
            {"category": "daemon", "name": "clawde agent: steward", "status": "fail"},
            {"category": "daemon", "name": "clawde agent: golden", "status": "fail"},
        ]
    )
    summary = health_summary.health_check_summary(fake_run_capturing(1, probes))
    assert summary["failing"] == ["daemon/clawde agent: golden"]


def test_health_check_summary_does_not_count_a_skipped_probe_as_failing():
    probes = json.dumps(
        [
            {
                "category": "daemon",
                "name": "clawde agent: golden",
                "status": "skip",
                "reason": "weekday-only agent, weekend",
            },
            {"category": "daemon", "name": "clawde agent: silver", "status": "fail"},
        ]
    )
    summary = health_summary.health_check_summary(fake_run_capturing(1, probes))
    assert summary["failing"] == ["daemon/clawde agent: silver"]


def test_health_check_summary_reports_why_a_probe_skipped():
    probes = json.dumps(
        [
            {
                "category": "daemon",
                "name": "clawde agent: golden",
                "status": "skip",
                "reason": "on demand, not started",
            }
        ]
    )
    summary = health_summary.health_check_summary(fake_run_capturing(0, probes))
    assert summary["skipped"] == [
        "daemon/clawde agent: golden (on demand, not started)"
    ]


def test_health_check_summary_marks_unavailable_when_missing():
    summary = health_summary.health_check_summary(fake_run_capturing(127, "not found"))
    assert summary == {"available": False}
