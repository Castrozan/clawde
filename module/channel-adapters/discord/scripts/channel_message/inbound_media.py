import dataclasses
import os

import discord
from channel_message.inbox_retention import prepare_inbox_for_message, safe_file_name

ATTACHMENT_DOWNLOAD_SIZE_LIMIT_BYTES = 25 * 1024 * 1024
MEDIA_BLOCK_OPENING_TAG = "<discord-media>"
MEDIA_BLOCK_CLOSING_TAG = "</discord-media>"
DOWNLOAD_FAILED_REASON = "download failed"


@dataclasses.dataclass(frozen=True)
class AttachmentIntake:
    attachment: object
    destination_path: str | None
    description_line: str


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
