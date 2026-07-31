import json
import os


def load_access_document(state_directory: str) -> dict:
    try:
        with open(os.path.join(state_directory, "access.json")) as access_file:
            return json.load(access_file)
    except (OSError, ValueError):
        return {}


def allowed_channel_identifiers(access_document: dict) -> set[str]:
    groups = access_document.get("groups", {})
    if not isinstance(groups, dict):
        return set()
    return {str(channel_identifier) for channel_identifier in groups}


def group_settings_for_channel(access_document: dict, channel_identifier: str) -> dict:
    settings = access_document.get("groups", {}).get(channel_identifier, {})
    return settings if isinstance(settings, dict) else {}


def author_is_allowed_in_channel(
    access_document: dict, channel_identifier: str, author_identifier: str
) -> bool:
    allowed_authors = group_settings_for_channel(
        access_document, channel_identifier
    ).get("allowFrom", [])
    if not allowed_authors:
        return True
    return str(author_identifier) in {str(author) for author in allowed_authors}


def channel_requires_a_mention(access_document: dict, channel_identifier: str) -> bool:
    return bool(
        group_settings_for_channel(access_document, channel_identifier).get(
            "requireMention", False
        )
    )


def message_is_for_this_agent(
    access_document: dict,
    channel_identifier: str,
    author_identifier: str,
    author_is_a_bot: bool,
    agent_was_mentioned: bool,
) -> bool:
    if author_is_a_bot:
        return False
    if channel_identifier not in allowed_channel_identifiers(access_document):
        return False
    if not author_is_allowed_in_channel(
        access_document, channel_identifier, author_identifier
    ):
        return False
    if channel_requires_a_mention(access_document, channel_identifier):
        return agent_was_mentioned
    return True
