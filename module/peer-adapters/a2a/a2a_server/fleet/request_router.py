import json

from ..task_store import Task
from .registry import AttachedAgentRegistry

JSON_CONTENT_TYPE = "application/json"


def json_response(status_code: int, document: dict) -> tuple[int, str, bytes]:
    return status_code, JSON_CONTENT_TYPE, json.dumps(document).encode("utf-8")


def task_response(status_code: int, task: Task) -> tuple[int, str, bytes]:
    return json_response(status_code, task.to_json_serializable_dict())


class FleetRequestRouter:
    def __init__(self, registry: AttachedAgentRegistry) -> None:
        self._registry = registry

    def serve_health_probe(self) -> tuple[int, str, bytes]:
        return json_response(200, {"status": "ok"})

    def serve_agent_directory(self) -> tuple[int, str, bytes]:
        return json_response(
            200,
            {
                "agents": sorted(
                    (
                        session.to_registry_entry()
                        for session in self._registry.every_session()
                    ),
                    key=lambda entry: entry["name"],
                )
            },
        )

    def serve_agent_card(self, peer_name: str) -> tuple[int, str, bytes]:
        session = self._registry.session_named(peer_name)
        if session is None:
            return self._unknown_agent_response(peer_name)
        return 200, JSON_CONTENT_TYPE, session.agent_card.serialize_to_json_bytes()

    def submit_task(
        self, peer_name: str, request_body_bytes: bytes
    ) -> tuple[int, str, bytes]:
        session = self._registry.session_named(peer_name)
        if session is None:
            return self._unknown_agent_response(peer_name)
        input_text, rejection_reason = self._read_input_text_from_body(
            request_body_bytes
        )
        if input_text is None:
            return json_response(400, {"error": rejection_reason})
        task, was_accepted = session.coordinator.submit_new_task_if_idle(input_text)
        return task_response(201 if was_accepted else 409, task)

    def get_task(self, peer_name: str, task_id: str) -> tuple[int, str, bytes]:
        session = self._registry.session_named(peer_name)
        if session is None:
            return self._unknown_agent_response(peer_name)
        task = session.task_store.get_task(task_id)
        if task is None:
            return json_response(404, {"error": "task_not_found"})
        return task_response(200, task)

    def cancel_task(self, peer_name: str, task_id: str) -> tuple[int, str, bytes]:
        session = self._registry.session_named(peer_name)
        if session is None:
            return self._unknown_agent_response(peer_name)
        task = session.coordinator.cancel_active_task_if_matches(task_id)
        if task is None:
            return json_response(404, {"error": "task_not_found"})
        return task_response(200, task)

    def _unknown_agent_response(self, peer_name: str) -> tuple[int, str, bytes]:
        return json_response(
            404,
            {
                "error": "unknown_agent",
                "requested": peer_name,
                "attached": sorted(
                    session.peer_name for session in self._registry.every_session()
                ),
            },
        )

    @staticmethod
    def _read_input_text_from_body(
        request_body_bytes: bytes,
    ) -> tuple[str | None, str]:
        try:
            parsed_body = json.loads(request_body_bytes.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None, "invalid_json"
        input_text = parsed_body.get("input")
        if not isinstance(input_text, str) or not input_text:
            return None, "missing_input_field"
        return input_text, ""
