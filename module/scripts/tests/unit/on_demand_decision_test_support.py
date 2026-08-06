import json
import os
import pathlib
import sys

sys.path.insert(
    0, str(pathlib.Path(__file__).resolve().parent.parent.parent / "agent-wrapper")
)

import on_demand_lease
from harness_profile_test_helpers import (
    CLAUDE_PROFILE_MAPPING,
    harness_launch_config_block,
)

AGENT_NAME = "on-demand-agent"


def deploy_agent(home_directory, launch_config, session_identifier=None):
    launch_config_directory = home_directory / "clawde" / "launch-config"
    launch_config_directory.mkdir(parents=True, exist_ok=True)
    (launch_config_directory / f"{AGENT_NAME}.json").write_text(
        json.dumps(
            {
                **harness_launch_config_block(CLAUDE_PROFILE_MAPPING, "claude"),
                **launch_config,
            }
        )
    )
    if session_identifier is None:
        return
    session_directory = home_directory / "clawde" / "session-ids"
    session_directory.mkdir(parents=True, exist_ok=True)
    (session_directory / f"{AGENT_NAME}.json").write_text(
        json.dumps(
            {"session_identifier": session_identifier, "started_on_date": "2026-07-20"}
        )
    )


def write_transcript(home_directory, workspace_directory, session_identifier, mtime):
    project_directory = (
        home_directory
        / ".claude"
        / "projects"
        / (str(workspace_directory).replace("/", "-"))
    )
    project_directory.mkdir(parents=True, exist_ok=True)
    transcript_file = project_directory / f"{session_identifier}.jsonl"
    transcript_file.write_text("{}\n")
    epoch_seconds = mtime.timestamp()
    os.utime(transcript_file, (epoch_seconds, epoch_seconds))


def grant_lease(home_directory, started_at):
    on_demand_lease.write_lease_started_at(
        on_demand_lease.lease_file_path_for_agent(
            str(home_directory / "clawde"), AGENT_NAME
        ),
        started_at,
    )
