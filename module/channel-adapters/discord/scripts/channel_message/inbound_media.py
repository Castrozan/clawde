import dataclasses
import os
import re
import shutil
import time

import discord

ATTACHMENT_DOWNLOAD_SIZE_LIMIT_BYTES = 25 * 1024 * 1024
INBOX_DIRECTORY_NAME = "inbox"
INBOX_RETENTION_SECONDS = 7 * 24 * 60 * 60
MEDIA_BLOCK_OPENING_TAG = "<discord-media>"
MEDIA_BLOCK_CLOSING_TAG = "</discord-media>"
DOWNLOAD_FAILED_REASON = "download failed"
UNSAFE_FILE_NAME_CHARACTERS = re.compile(r"[^A-Za-z0-9._-]")
LONGEST_KEPT_FILE_NAME = 96
FALLBACK_FILE_NAME = "attachment"


@dataclasses.dataclass(frozen=True)
class AttachmentIntake:
    attachment: object
    destination_path: str | None
    description_line: str


def inbox_directory(state_directory: str) -> str:
    return os.path.join(state_directory, INBOX_DIRECTORY_NAME)


def message_inbox_directory(state_directory: str, message_identifier: str) -> str:
    return os.path.join(
        inbox_directory(state_directory), safe_file_name(message_identifier)
    )


def safe_file_name(file_name: str) -> str:
    sanitized = UNSAFE_FILE_NAME_CHARACTERS.sub("_", file_name).lstrip(".")
    if len(sanitized) > LONGEST_KEPT_FILE_NAME:
        stem, extension = os.path.splitext(sanitized)
        sanitized = stem[: LONGEST_KEPT_FILE_NAME - len(extension)] + extension
    return sanitized or FALLBACK_FILE_NAME


def human_readable_size(byte_count: int) -> str:
    if byte_count >= 1024 * 1024:
        return f"{byte_count / 1024 / 1024:.1f} MB"
    if byte_count >= 1024:
        return f"{byte_count / 1024:.1f} KB"
    return f"{byte_count} B"


def oversized_reason() -> str:
    return f"over the {human_readable_size(ATTACHMENT_DOWNLOAD_SIZE_LIMIT_BYTES)} limit"


def measure_attachment(attachment) -> str:
    described_type = attachment.content_type or "unknown type"
    return (
        f"{attachment.filename} "
        f"({described_type}, {human_readable_size(attachment.size)})"
    )


def describe_saved_attachment(attachment, destination_path: str) -> str:
    return f"attachment {measure_attachment(attachment)} saved at {destination_path}"


def describe_unsaved_attachment(attachment, reason: str) -> str:
    return (
        f"attachment {measure_attachment(attachment)} not saved "
        f"({reason}), at {attachment.url}"
    )


def plan_attachment_intake(
    attachments, destination_directory: str
) -> list[AttachmentIntake]:
    planned = []
    for position, attachment in enumerate(attachments):
        if attachment.size > ATTACHMENT_DOWNLOAD_SIZE_LIMIT_BYTES:
            planned.append(
                AttachmentIntake(
                    attachment,
                    None,
                    describe_unsaved_attachment(attachment, oversized_reason()),
                )
            )
            continue
        destination_path = os.path.join(
            destination_directory, f"{position}-{safe_file_name(attachment.filename)}"
        )
        planned.append(
            AttachmentIntake(
                attachment,
                destination_path,
                describe_saved_attachment(attachment, destination_path),
            )
        )
    return planned


def describe_stickers(stickers) -> list[str]:
    return [f"sticker {sticker.name}" for sticker in stickers]


def prompt_for_message(text: str, description_lines: list[str]) -> str:
    if not description_lines:
        return text
    media_block = "\n".join(
        [MEDIA_BLOCK_OPENING_TAG, *description_lines, MEDIA_BLOCK_CLOSING_TAG]
    )
    if not text.strip():
        return media_block
    return f"{text}\n\n{media_block}"


def prune_expired_inbox(state_directory: str, now: float) -> None:
    cutoff = now - INBOX_RETENTION_SECONDS
    try:
        message_directories = os.scandir(inbox_directory(state_directory))
    except OSError:
        return
    with message_directories:
        for entry in message_directories:
            if entry.is_dir() and entry.stat().st_mtime < cutoff:
                shutil.rmtree(entry.path, ignore_errors=True)


def prepare_inbox_for_message(state_directory: str, message_identifier: str) -> str:
    prune_expired_inbox(state_directory, time.time())
    destination_directory = message_inbox_directory(state_directory, message_identifier)
    os.makedirs(destination_directory, exist_ok=True)
    return destination_directory


async def save_attachments(attachments, state_directory, message_identifier, report):
    if not attachments:
        return []
    destination_directory = prepare_inbox_for_message(
        state_directory, message_identifier
    )
    description_lines = []
    for intake in plan_attachment_intake(attachments, destination_directory):
        if intake.destination_path is None:
            description_lines.append(intake.description_line)
            continue
        try:
            await intake.attachment.save(intake.destination_path)
        except (discord.DiscordException, OSError) as saving_failure:
            report(f"could not save {intake.attachment.filename}: {saving_failure}")
            description_lines.append(
                describe_unsaved_attachment(intake.attachment, DOWNLOAD_FAILED_REASON)
            )
            continue
        description_lines.append(intake.description_line)
    return description_lines


async def prompt_for_message_with_media(message, state_directory, report) -> str:
    description_lines = await save_attachments(
        message.attachments, state_directory, str(message.id), report
    )
    description_lines.extend(describe_stickers(message.stickers))
    return prompt_for_message(message.clean_content, description_lines)
