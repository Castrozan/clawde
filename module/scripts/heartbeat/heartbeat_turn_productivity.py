import os
import time

from harness_productivity_record import (
    judge_previously_delivered_turn,
    record_delivered_turn_evidence,
)
from session_persistence import session_transcript_file
from session_store import build_session_record_file_path, read_persisted_session_record

ACTIVE_WORK_SAMPLE_COUNT = 6
ACTIVE_WORK_SAMPLE_INTERVAL_SECONDS = 5


def live_session_identifier(runtime_root_directory: str, agent_name: str) -> str | None:
    persisted_session_identifier, _ = read_persisted_session_record(
        build_session_record_file_path(runtime_root_directory, agent_name)
    )
    return persisted_session_identifier


def session_transcript_byte_size(
    harness_runtime_profile,
    session_identifier: str | None,
    workspace_directory: str | None,
) -> int | None:
    if not session_identifier or not workspace_directory:
        return None
    if not harness_runtime_profile.exposes_session_transcript_store():
        return None
    try:
        return os.stat(
            session_transcript_file(
                harness_runtime_profile, session_identifier, workspace_directory
            )
        ).st_size
    except OSError:
        return None


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

    def current_transcript_evidence(self) -> tuple[str | None, int | None]:
        session_identifier = live_session_identifier(
            self.runtime_root_directory, self.agent_name
        )
        return session_identifier, session_transcript_byte_size(
            self.harness_runtime_profile, session_identifier, self.workspace_directory
        )

    def judge_previous_delivery(self) -> dict:
        session_identifier, transcript_byte_size = self.current_transcript_evidence()
        return judge_previously_delivered_turn(
            self.record_file_path, session_identifier, transcript_byte_size
        )

    def observe_this_delivery(
        self, backend, pane_handle, sleep_function=time.sleep
    ) -> dict:
        showed_active_work = False
        for _ in range(ACTIVE_WORK_SAMPLE_COUNT):
            sleep_function(ACTIVE_WORK_SAMPLE_INTERVAL_SECONDS)
            if backend.pane_reports_active_work(pane_handle):
                showed_active_work = True
        session_identifier, transcript_byte_size = self.current_transcript_evidence()
        return record_delivered_turn_evidence(
            self.record_file_path,
            session_identifier,
            transcript_byte_size,
            showed_active_work,
        )
