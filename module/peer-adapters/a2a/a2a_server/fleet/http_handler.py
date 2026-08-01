import http.server
import json
from typing import Callable

from .request_router import FleetRequestRouter, json_response

AGENT_PATH_PREFIX = "/agents/"


def split_agent_scoped_path(request_path: str) -> tuple[str, str] | None:
    if not request_path.startswith(AGENT_PATH_PREFIX):
        return None
    remainder = request_path[len(AGENT_PATH_PREFIX) :]
    peer_name, separator, path_within_agent = remainder.partition("/")
    if not peer_name:
        return None
    return peer_name, f"/{path_within_agent}" if separator else "/"


def route_get_request(
    router: FleetRequestRouter, request_path: str
) -> Callable[[], tuple[int, str, bytes]]:
    if request_path == "/health":
        return router.serve_health_probe
    if request_path in ("/agents", "/agents/"):
        return router.serve_agent_directory
    agent_scoped_path = split_agent_scoped_path(request_path)
    if agent_scoped_path is not None:
        peer_name, path_within_agent = agent_scoped_path
        if path_within_agent == "/.well-known/agent.json":
            return lambda: router.serve_agent_card(peer_name)
        if path_within_agent.startswith("/tasks/"):
            task_id = path_within_agent[len("/tasks/") :]
            return lambda: router.get_task(peer_name, task_id)
    return not_found_response


def route_post_request(
    router: FleetRequestRouter, request_path: str, request_body_bytes: bytes
) -> Callable[[], tuple[int, str, bytes]]:
    agent_scoped_path = split_agent_scoped_path(request_path)
    if agent_scoped_path is None:
        return not_found_response
    peer_name, path_within_agent = agent_scoped_path
    if path_within_agent == "/tasks/send":
        return lambda: router.submit_task(peer_name, request_body_bytes)
    if path_within_agent.startswith("/tasks/") and path_within_agent.endswith(
        "/cancel"
    ):
        task_id = path_within_agent[len("/tasks/") : -len("/cancel")]
        return lambda: router.cancel_task(peer_name, task_id)
    return not_found_response


def not_found_response() -> tuple[int, str, bytes]:
    return json_response(404, {"error": "not_found"})


def build_http_request_handler_class(
    router: FleetRequestRouter,
) -> type[http.server.BaseHTTPRequestHandler]:
    class _FleetHTTPRequestHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self._respond_with_router_result(route_get_request(router, self.path))

        def do_POST(self) -> None:
            self._respond_with_router_result(
                route_post_request(router, self.path, self._read_request_body_bytes())
            )

        def log_message(self, format: str, *args) -> None:
            return

        def _read_request_body_bytes(self) -> bytes:
            try:
                content_length_bytes = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                content_length_bytes = 0
            if content_length_bytes <= 0:
                return b""
            return self.rfile.read(content_length_bytes)

        def _respond_with_router_result(
            self, router_method_call: Callable[[], tuple[int, str, bytes]]
        ) -> None:
            try:
                status_code, content_type, body_bytes = router_method_call()
            except Exception as router_exception:
                status_code, content_type, body_bytes = (
                    500,
                    "application/json",
                    json.dumps(
                        {"error": "internal_error", "detail": str(router_exception)}
                    ).encode("utf-8"),
                )
            self.send_response(status_code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body_bytes)))
            self.end_headers()
            self.wfile.write(body_bytes)

    return _FleetHTTPRequestHandler
