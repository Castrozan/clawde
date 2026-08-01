import json
import re
from pathlib import Path


class FleetAgentMetadata:
    def __init__(self, metadata_document: dict) -> None:
        self._harness_line_patterns = metadata_document.get(
            "harnessMeaningfulLinePatterns", {}
        )
        self._agents = metadata_document.get("agents", {})

    def description_for(self, peer_name: str, harness: str) -> str:
        declared_description = self._agents.get(peer_name, {}).get("description")
        if declared_description:
            return declared_description
        return f"{harness} session {peer_name}"

    def meaningful_line_pattern_for(
        self, peer_name: str, harness: str
    ) -> re.Pattern | None:
        declared_override = self._agents.get(peer_name, {}).get("meaningfulLinePattern")
        pattern_source = declared_override or self._harness_line_patterns.get(harness)
        if not pattern_source:
            return None
        try:
            return re.compile(pattern_source)
        except re.error:
            return None


def read_fleet_agent_metadata(metadata_file_path: Path | None) -> FleetAgentMetadata:
    if metadata_file_path is None or not metadata_file_path.is_file():
        return FleetAgentMetadata({})
    try:
        return FleetAgentMetadata(
            json.loads(metadata_file_path.read_text(encoding="utf-8"))
        )
    except (json.JSONDecodeError, UnicodeDecodeError, OSError):
        return FleetAgentMetadata({})
