import threading
import time

from .backends.base import AgentBackend, BackendObservation
from .task_store import Task, TaskStore

WORKING_TASK_IDLE_TIMEOUT_SECONDS_FOR_AUTO_COMPLETE = 30.0
TARGET_VANISHED_ERROR_MESSAGE = "the agent pane this task was sent to is gone"


class ActiveTaskCoordinator:
    def __init__(
        self,
        task_store: TaskStore,
        agent_backend: AgentBackend,
        auto_complete_idle_timeout_seconds: float = WORKING_TASK_IDLE_TIMEOUT_SECONDS_FOR_AUTO_COMPLETE,
    ) -> None:
        self._task_store = task_store
        self._agent_backend = agent_backend
        self._auto_complete_idle_timeout_seconds = auto_complete_idle_timeout_seconds
        self._active_task_id: str | None = None
        self._active_task_target_was_observed_busy = False
        self._lock = threading.Lock()

    def is_holding_an_unfinished_task(self) -> bool:
        with self._lock:
            if self._active_task_id is None:
                return False
            return not self._task_store.is_task_in_terminal_state(self._active_task_id)

    def submit_new_task_if_idle(self, input_text: str) -> tuple[Task, bool]:
        with self._lock:
            if (
                self._active_task_id is not None
                and not self._task_store.is_task_in_terminal_state(self._active_task_id)
            ):
                existing_task = self._task_store.get_task(self._active_task_id)
                return existing_task, False
            new_task = self._task_store.create_task(input_text)
            self._active_task_id = new_task.id
            self._active_task_target_was_observed_busy = False
            self._task_store.transition_task_state(new_task.id, "working")
        self._agent_backend.send_input_text(input_text)
        return new_task, True

    def cancel_active_task_if_matches(self, task_id: str) -> Task | None:
        with self._lock:
            if self._active_task_id != task_id:
                return self._task_store.get_task(task_id)
            if self._task_store.is_task_in_terminal_state(task_id):
                return self._task_store.get_task(task_id)
        self._agent_backend.cancel_gracefully()
        return self._task_store.transition_task_state(task_id, "canceled")

    def observe_once_and_apply_to_active_task(self) -> None:
        self._apply_observation_to_active_task_if_any(self._agent_backend.observe())

    def fail_active_task_because_the_target_vanished(self) -> None:
        with self._lock:
            active_task_id = self._active_task_id
        if active_task_id is None:
            return
        if self._task_store.is_task_in_terminal_state(active_task_id):
            return
        self._task_store.mark_task_failed_with_error_message(
            active_task_id, TARGET_VANISHED_ERROR_MESSAGE
        )

    def _apply_observation_to_active_task_if_any(
        self, observation: BackendObservation
    ) -> None:
        with self._lock:
            active_task_id = self._active_task_id
        if active_task_id is None:
            return
        if self._task_store.is_task_in_terminal_state(active_task_id):
            return
        if observation.raw_output_since_last_call:
            self._task_store.append_task_output(
                active_task_id, observation.raw_output_since_last_call
            )
        if not observation.is_alive:
            self._task_store.mark_task_failed_with_error_message(
                active_task_id, TARGET_VANISHED_ERROR_MESSAGE
            )
            return
        if self._reported_agent_status_says_the_turn_is_over(observation):
            self._task_store.transition_task_state(active_task_id, "completed")
            return
        idle_for_seconds = time.time() - observation.last_activity_at_epoch_seconds
        if idle_for_seconds >= self._auto_complete_idle_timeout_seconds:
            self._task_store.transition_task_state(active_task_id, "completed")

    def _reported_agent_status_says_the_turn_is_over(
        self, observation: BackendObservation
    ) -> bool:
        if observation.agent_is_busy is None:
            return False
        if observation.agent_is_busy:
            self._active_task_target_was_observed_busy = True
            return False
        return self._active_task_target_was_observed_busy
