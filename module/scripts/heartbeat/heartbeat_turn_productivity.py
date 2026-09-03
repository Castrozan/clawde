import time

from harness_productivity_record import (
    judge_previous_turn_and_baseline_the_next,
    record_that_the_delivered_turn_showed_active_work,
)
from session_persistence import session_transcript_file
from session_store import build_session_record_file_path, read_persisted_session_record
from transcript_productivity import count_transcript_assistant_work_entries

ACTIVE_WORK_SAMPLE_COUNT = 6
ACTIVE_WORK_SAMPLE_INTERVAL_SECONDS = 5


def live_session_identifier(runtime_root_directory: str, agent_name: str) -> str | None:
    persisted_session_identifier, _ = read_persisted_session_record(
        build_session_record_file_path(runtime_root_directory, agent_name)
    )
    return persisted_session_identifier


def session_transcript_work_entry_count(
    harness_runtime_profile,
    session_identifier: str | None,
    workspace_directory: str | None,
) -> int | None:
    if not session_identifier or not workspace_directory:
        return None
    if not harness_runtime_profile.exposes_session_transcript_store():
        return None
    return count_transcript_assistant_work_entries(
        session_transcript_file(
            harness_runtime_profile, session_identifier, workspace_directory
        )
    )


class DeliveredTurnObserver:
    def __init__(
        self,
        record_file_path: str,
        harness_runtime_profile,
        runtime_root_directory: str,
        agent_name: str,
        workspace_directory: str | None,
    ):
        self.record_file_path = record_file_path
        self.harness_runtime_profile = harness_runtime_profile
        self.runtime_root_directory = runtime_root_directory
        self.agent_name = agent_name
        self.workspace_directory = workspace_directory

    def judge_previous_delivery(self) -> dict:
        session_identifier = live_session_identifier(
            self.runtime_root_directory, self.agent_name
        )
        return judge_previous_turn_and_baseline_the_next(
            self.record_file_path,
            session_identifier,
            session_transcript_work_entry_count(
                self.harness_runtime_profile,
                session_identifier,
                self.workspace_directory,
            ),
        )

    def watch_this_delivery_for_active_work(
        self, backend, pane_handle, sleep_function=time.sleep
    ) -> None:
        for _ in range(ACTIVE_WORK_SAMPLE_COUNT):
            sleep_function(ACTIVE_WORK_SAMPLE_INTERVAL_SECONDS)
            if backend.pane_reports_active_work(pane_handle):
                record_that_the_delivered_turn_showed_active_work(self.record_file_path)
                return
