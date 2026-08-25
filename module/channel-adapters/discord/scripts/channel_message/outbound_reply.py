import dataclasses
import os

import discord

DISCORD_MESSAGE_CHARACTER_LIMIT = 2000
DISCORD_ATTACHMENT_COUNT_LIMIT = 10
ATTACHMENT_UPLOAD_SIZE_LIMIT_BYTES = 25 * 1024 * 1024


@dataclasses.dataclass(frozen=True)
class ReplyAttachmentSplit:
    text: str
    attachment_paths: list[str]
    refused_paths: list[str]


def split_into_sendable_messages(reply: str) -> list[str]:
    remaining = reply
    messages = []
    while len(remaining) > DISCORD_MESSAGE_CHARACTER_LIMIT:
        split_position = remaining.rfind("\n", 0, DISCORD_MESSAGE_CHARACTER_LIMIT)
        if split_position <= 0:
            split_position = DISCORD_MESSAGE_CHARACTER_LIMIT
        messages.append(remaining[:split_position])
        remaining = remaining[split_position:].lstrip("\n")
    if remaining:
        messages.append(remaining)
    return messages


def path_lies_inside_directory(candidate_path: str, directory: str) -> bool:
    resolved_directory = os.path.realpath(directory)
    resolved_candidate = os.path.realpath(candidate_path)
    if resolved_candidate == resolved_directory:
        return False
    return (
        os.path.commonpath([resolved_directory, resolved_candidate])
        == resolved_directory
    )


def line_names_a_workspace_file(line: str, workspace_directory: str) -> bool:
    candidate_path = line.strip()
    if not os.path.isabs(candidate_path):
        return False
    if not path_lies_inside_directory(candidate_path, workspace_directory):
        return False
    return os.path.isfile(candidate_path)


def attachment_is_small_enough_to_upload(attachment_path: str) -> bool:
    return os.path.getsize(attachment_path) <= ATTACHMENT_UPLOAD_SIZE_LIMIT_BYTES


def split_reply_into_text_and_attachments(
    reply: str, workspace_directory: str
) -> ReplyAttachmentSplit:
    kept_lines = []
    attachment_paths = []
    refused_paths = []
    for line in reply.split("\n"):
        if not line_names_a_workspace_file(line, workspace_directory):
            kept_lines.append(line)
            continue
        attachment_path = line.strip()
        if len(attachment_paths) >= DISCORD_ATTACHMENT_COUNT_LIMIT:
            refused_paths.append(attachment_path)
        elif not attachment_is_small_enough_to_upload(attachment_path):
            refused_paths.append(attachment_path)
        else:
            attachment_paths.append(attachment_path)
    return ReplyAttachmentSplit(
        "\n".join(kept_lines).strip(), attachment_paths, refused_paths
    )


async def send_reply(channel, split: ReplyAttachmentSplit) -> None:
    sendable_messages = split_into_sendable_messages(split.text)
    attachments = [discord.File(path) for path in split.attachment_paths]
    leading_message = sendable_messages[0] if sendable_messages else None
    if leading_message is None and not attachments:
        return
    await channel.send(leading_message, files=attachments or None)
    for sendable_message in sendable_messages[1:]:
        await channel.send(sendable_message)
