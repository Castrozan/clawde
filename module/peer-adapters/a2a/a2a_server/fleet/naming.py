import collections
import os
import re

from .discovery import DiscoveredAgentPane

CHARACTERS_A_PEER_NAME_MAY_NOT_CARRY = re.compile(r"[^A-Za-z0-9._-]+")


def sanitize_for_use_in_a_url_path(candidate: str) -> str:
    return CHARACTERS_A_PEER_NAME_MAY_NOT_CARRY.sub("-", candidate).strip("-")


def preferred_name_for_pane(
    pane: DiscoveredAgentPane, tab_labels_by_tab_id: dict[str, str]
) -> str:
    tab_label = tab_labels_by_tab_id.get(pane.tab_id)
    if tab_label:
        return sanitize_for_use_in_a_url_path(tab_label)
    if pane.working_directory:
        directory_name = os.path.basename(pane.working_directory.rstrip("/"))
        if directory_name:
            return sanitize_for_use_in_a_url_path(directory_name)
    return sanitize_for_use_in_a_url_path(pane.pane_id)


def unique_peer_names_by_pane_id(
    panes: list[DiscoveredAgentPane], tab_labels_by_tab_id: dict[str, str]
) -> dict[str, str]:
    preferred_name_by_pane_id = {
        pane.pane_id: preferred_name_for_pane(pane, tab_labels_by_tab_id)
        for pane in panes
    }
    times_each_name_was_preferred = collections.Counter(
        preferred_name_by_pane_id.values()
    )
    return {
        pane_id: (
            preferred_name
            if times_each_name_was_preferred[preferred_name] == 1
            else f"{preferred_name}-{sanitize_for_use_in_a_url_path(pane_id)}"
        )
        for pane_id, preferred_name in preferred_name_by_pane_id.items()
    }
