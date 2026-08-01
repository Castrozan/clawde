import http.server
from pathlib import Path

from .agent_metadata import read_fleet_agent_metadata
from .http_handler import build_http_request_handler_class
from .observation_loop import FleetObservationLoop
from .registry import AttachedAgentRegistry
from .request_router import FleetRequestRouter


def run_fleet_daemon_blocking(
    host: str,
    port: int,
    daemon_base_url: str,
    metadata_file_path: Path | None,
) -> None:
    registry = AttachedAgentRegistry(
        read_fleet_agent_metadata(metadata_file_path), daemon_base_url
    )
    observation_loop = FleetObservationLoop(registry)
    observation_loop.run_one_pass()
    http_server = http.server.ThreadingHTTPServer(
        (host, port), build_http_request_handler_class(FleetRequestRouter(registry))
    )
    observation_loop.start()
    try:
        http_server.serve_forever()
    finally:
        observation_loop.stop()
        http_server.server_close()
