import time

from a2a_server.active_task_coordinator import ActiveTaskCoordinator
from a2a_server.backends.base import AgentBackend, BackendObservation
from a2a_server.task_store import TaskStore

A_TIMEOUT_LONG_ENOUGH_THAT_ONLY_THE_REPORTED_TURN_CAN_COMPLETE_THE_TASK = 3600.0


class ReplayingAgentBackend(AgentBackend):
    def __init__(self, busy_states_to_replay: list[bool | None]) -> None:
        self._busy_states_to_replay = busy_states_to_replay
        self._next_index = 0

    def start(self) -> None:
        return None

    def send_input_text(self, text: str) -> None:
        return None

    def observe(self) -> BackendObservation:
        agent_is_busy = self._busy_states_to_replay[
            min(self._next_index, len(self._busy_states_to_replay) - 1)
        ]
        self._next_index += 1
        return BackendObservation(
            raw_output_since_last_call="",
            is_alive=True,
            last_activity_at_epoch_seconds=time.time(),
            agent_is_busy=agent_is_busy,
        )

    def cancel_gracefully(self) -> None:
        return None

    def stop(self) -> None:
        return None


def submit_a_task_then_observe(busy_states_to_replay: list[bool | None]):
    task_store = TaskStore()
    coordinator = ActiveTaskCoordinator(
        task_store,
        ReplayingAgentBackend(busy_states_to_replay),
        auto_complete_idle_timeout_seconds=(
            A_TIMEOUT_LONG_ENOUGH_THAT_ONLY_THE_REPORTED_TURN_CAN_COMPLETE_THE_TASK
        ),
    )
    task, _ = coordinator.submit_new_task_if_idle("ping")
    for _ in busy_states_to_replay:
        coordinator.observe_once_and_apply_to_active_task()
    return task_store.get_task(task.id)


class TestCompletionFollowsTheReportedTurn:
    def test_completes_once_the_agent_stops_working(self):
        task = submit_a_task_then_observe([True, True, False])
        assert task.state == "completed"

    def test_stays_working_while_the_agent_is_still_working(self):
        task = submit_a_task_then_observe([True, True, True])
        assert task.state == "working"

    def test_stays_working_when_the_agent_has_not_picked_the_prompt_up_yet(self):
        task = submit_a_task_then_observe([False, False, False])
        assert task.state == "working"

    def test_stays_working_when_the_multiplexer_reports_no_turn_state_at_all(self):
        task = submit_a_task_then_observe([None, None, None])
        assert task.state == "working"

    def test_a_turn_reported_for_the_previous_task_does_not_complete_the_next_one(self):
        task_store = TaskStore()
        backend = ReplayingAgentBackend([True, False])
        coordinator = ActiveTaskCoordinator(
            task_store,
            backend,
            auto_complete_idle_timeout_seconds=(
                A_TIMEOUT_LONG_ENOUGH_THAT_ONLY_THE_REPORTED_TURN_CAN_COMPLETE_THE_TASK
            ),
        )
        first_task, _ = coordinator.submit_new_task_if_idle("first")
        coordinator.observe_once_and_apply_to_active_task()
        coordinator.observe_once_and_apply_to_active_task()
        assert task_store.get_task(first_task.id).state == "completed"
        second_task, _ = coordinator.submit_new_task_if_idle("second")
        coordinator.observe_once_and_apply_to_active_task()
        assert task_store.get_task(second_task.id).state == "working"
