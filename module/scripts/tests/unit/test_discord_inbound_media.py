import asyncio
import os
import time

from discord_stub_test_support import install_discord_stub

install_discord_stub()

from channel_message import inbound_media  # noqa: E402


class StubAttachment:
    def __init__(
        self,
        filename,
        content_type="image/png",
        size=1024,
        url="https://cdn.discordapp.example/file",
        payload=b"payload",
        saving_failure=None,
    ):
        self.filename = filename
        self.content_type = content_type
        self.size = size
        self.url = url
        self.payload = payload
        self.saving_failure = saving_failure

    async def save(self, destination_path):
        if self.saving_failure is not None:
            raise self.saving_failure
        with open(destination_path, "wb") as destination_file:
            destination_file.write(self.payload)


class StubSticker:
    def __init__(self, name):
        self.name = name


class StubMessage:
    def __init__(self, identifier, clean_content="", attachments=(), stickers=()):
        self.id = identifier
        self.clean_content = clean_content
        self.attachments = list(attachments)
        self.stickers = list(stickers)


def build_prompt(message, state_directory):
    reported = []
    prompt = asyncio.run(
        inbound_media.prompt_for_message_with_media(
            message, str(state_directory), reported.append
        )
    )
    return prompt, reported


def test_a_message_carrying_only_a_video_no_longer_reaches_the_agent_as_an_empty_prompt(
    tmp_path,
):
    message = StubMessage(
        7, attachments=[StubAttachment("spiderman.mp4", "video/mp4", 3 * 1024 * 1024)]
    )

    prompt, _ = build_prompt(message, tmp_path)

    assert prompt.strip()
    assert "spiderman.mp4" in prompt
    assert "video/mp4" in prompt
    assert inbound_media.MEDIA_BLOCK_OPENING_TAG in prompt


def test_an_attachment_is_saved_into_the_agents_inbox_and_named_by_absolute_path(
    tmp_path,
):
    message = StubMessage(7, attachments=[StubAttachment("cat.png", payload=b"gif89a")])

    prompt, _ = build_prompt(message, tmp_path)

    saved_path = str(tmp_path / "inbox" / "7" / "0-cat.png")
    assert saved_path in prompt
    assert os.path.isfile(saved_path)
    with open(saved_path, "rb") as saved_file:
        assert saved_file.read() == b"gif89a"


def test_an_attachment_filename_cannot_escape_the_inbox_directory(tmp_path):
    message = StubMessage(7, attachments=[StubAttachment("../../escaped.sh")])

    prompt, _ = build_prompt(message, tmp_path)

    saved_files = list((tmp_path / "inbox" / "7").iterdir())
    assert len(saved_files) == 1
    assert str(saved_files[0]) in prompt
    assert not os.path.exists(str(tmp_path.parent / "escaped.sh"))
    assert not os.path.exists(str(tmp_path / "escaped.sh"))


def test_an_oversized_attachment_is_offered_by_url_instead_of_downloaded(tmp_path):
    oversized = inbound_media.ATTACHMENT_DOWNLOAD_SIZE_LIMIT_BYTES + 1
    message = StubMessage(
        7,
        attachments=[
            StubAttachment(
                "huge.mp4", "video/mp4", oversized, url="https://cdn.example/huge.mp4"
            )
        ],
    )

    prompt, _ = build_prompt(message, tmp_path)

    assert "not saved" in prompt
    assert "https://cdn.example/huge.mp4" in prompt
    assert not os.path.exists(str(tmp_path / "inbox" / "7" / "0-huge.mp4"))


def test_a_failed_download_still_tells_the_agent_the_attachment_arrived(tmp_path):
    message = StubMessage(
        7,
        attachments=[
            StubAttachment("broken.png", saving_failure=OSError("disk is full"))
        ],
    )

    prompt, reported = build_prompt(message, tmp_path)

    assert inbound_media.DOWNLOAD_FAILED_REASON in prompt
    assert "broken.png" in prompt
    assert any("disk is full" in note for note in reported)


def test_a_caption_stays_above_the_media_block(tmp_path):
    message = StubMessage(
        7, clean_content="olha isso", attachments=[StubAttachment("cat.png")]
    )

    prompt, _ = build_prompt(message, tmp_path)

    assert prompt.startswith("olha isso\n\n")
    assert prompt.index("olha isso") < prompt.index("cat.png")


def test_a_sticker_only_message_names_the_sticker(tmp_path):
    message = StubMessage(7, stickers=[StubSticker("capivara")])

    prompt, _ = build_prompt(message, tmp_path)

    assert prompt == "\n".join(
        [
            inbound_media.MEDIA_BLOCK_OPENING_TAG,
            "sticker capivara",
            inbound_media.MEDIA_BLOCK_CLOSING_TAG,
        ]
    )


def test_a_plain_text_message_reaches_the_agent_unchanged(tmp_path):
    message = StubMessage(7, clean_content="bom dia")

    prompt, _ = build_prompt(message, tmp_path)

    assert prompt == "bom dia"
    assert not os.path.exists(str(tmp_path / "inbox"))


def test_inbox_directories_older_than_the_retention_window_are_pruned(tmp_path):
    expired_directory = tmp_path / "inbox" / "1"
    kept_directory = tmp_path / "inbox" / "2"
    expired_directory.mkdir(parents=True)
    kept_directory.mkdir(parents=True)
    now = time.time()
    os.utime(expired_directory, (now - inbound_media.INBOX_RETENTION_SECONDS - 1,) * 2)

    inbound_media.prune_expired_inbox(str(tmp_path), now)

    assert not expired_directory.exists()
    assert kept_directory.exists()
