import asyncio
import os

from discord_stub_test_support import StubDiscordHTTPException, install_discord_stub

install_discord_stub()

from channel_message import outbound_reply  # noqa: E402


class RecordingChannel:
    def __init__(self, refuse_attachments=False):
        self.refuse_attachments = refuse_attachments
        self.sent = []

    async def send(self, content, files=None):
        if files and self.refuse_attachments:
            raise StubDiscordHTTPException("payload too large")
        self.sent.append((content, files))


def write_workspace_file(workspace_directory, relative_path, size=16):
    absolute_path = workspace_directory / relative_path
    absolute_path.parent.mkdir(parents=True, exist_ok=True)
    absolute_path.write_bytes(b"x" * size)
    return str(absolute_path)


def test_a_reply_line_naming_a_workspace_file_becomes_an_attachment(tmp_path):
    gif_path = write_workspace_file(tmp_path, "media/sneer.gif")

    split = outbound_reply.split_reply_into_text_and_attachments(
        f"olha o seu retrato\n{gif_path}", str(tmp_path)
    )

    assert split.text == "olha o seu retrato"
    assert split.attachment_paths == [gif_path]
    assert split.refused_paths == []


def test_a_reply_that_is_only_a_path_sends_the_file_with_no_text(tmp_path):
    voice_note_path = write_workspace_file(tmp_path, "media/sigh.mp3")

    split = outbound_reply.split_reply_into_text_and_attachments(
        voice_note_path, str(tmp_path)
    )

    assert split.text == ""
    assert split.attachment_paths == [voice_note_path]


def test_a_path_outside_the_workspace_is_never_attached(tmp_path):
    outside_path = tmp_path.parent / "outside.txt"
    outside_path.write_text("secret")
    workspace_directory = tmp_path / "workspace"
    workspace_directory.mkdir()

    split = outbound_reply.split_reply_into_text_and_attachments(
        f"toma\n{outside_path}", str(workspace_directory)
    )

    assert split.attachment_paths == []
    assert str(outside_path) in split.text


def test_a_symlink_pointing_out_of_the_workspace_is_never_attached(tmp_path):
    outside_path = tmp_path / "outside.txt"
    outside_path.write_text("secret")
    workspace_directory = tmp_path / "workspace"
    workspace_directory.mkdir()
    escaping_link = workspace_directory / "link.txt"
    escaping_link.symlink_to(outside_path)

    split = outbound_reply.split_reply_into_text_and_attachments(
        str(escaping_link), str(workspace_directory)
    )

    assert split.attachment_paths == []


def test_prose_that_merely_mentions_a_path_stays_in_the_text(tmp_path):
    gif_path = write_workspace_file(tmp_path, "media/sneer.gif")

    split = outbound_reply.split_reply_into_text_and_attachments(
        f"o arquivo {gif_path} existe", str(tmp_path)
    )

    assert split.attachment_paths == []
    assert split.text == f"o arquivo {gif_path} existe"


def test_an_oversized_file_is_refused_rather_than_uploaded(tmp_path):
    oversized_path = write_workspace_file(
        tmp_path,
        "media/huge.mp4",
        outbound_reply.ATTACHMENT_UPLOAD_SIZE_LIMIT_BYTES + 1,
    )

    split = outbound_reply.split_reply_into_text_and_attachments(
        f"toma\n{oversized_path}", str(tmp_path)
    )

    assert split.attachment_paths == []
    assert split.refused_paths == [oversized_path]


def test_files_beyond_the_discord_count_limit_are_refused(tmp_path):
    paths = [
        write_workspace_file(tmp_path, f"media/gif-{index}.gif")
        for index in range(outbound_reply.DISCORD_ATTACHMENT_COUNT_LIMIT + 2)
    ]

    split = outbound_reply.split_reply_into_text_and_attachments(
        "\n".join(paths), str(tmp_path)
    )

    assert len(split.attachment_paths) == outbound_reply.DISCORD_ATTACHMENT_COUNT_LIMIT
    assert split.refused_paths == paths[outbound_reply.DISCORD_ATTACHMENT_COUNT_LIMIT :]


def test_the_files_ride_along_with_the_first_sent_message(tmp_path):
    gif_path = write_workspace_file(tmp_path, "media/sneer.gif")
    channel = RecordingChannel()

    asyncio.run(
        outbound_reply.send_reply(
            channel,
            outbound_reply.ReplyAttachmentSplit("toma", [gif_path], []),
            [].append,
        )
    )

    assert len(channel.sent) == 1
    content, files = channel.sent[0]
    assert content == "toma"
    assert [attached.path for attached in files] == [gif_path]


def test_a_long_reply_attaches_to_the_first_chunk_only(tmp_path):
    gif_path = write_workspace_file(tmp_path, "media/sneer.gif")
    channel = RecordingChannel()
    long_text = "\n".join(["a" * 500] * 8)

    asyncio.run(
        outbound_reply.send_reply(
            channel,
            outbound_reply.ReplyAttachmentSplit(long_text, [gif_path], []),
            [].append,
        )
    )

    assert len(channel.sent) > 1
    assert channel.sent[0][1] is not None
    assert all(files is None for _, files in channel.sent[1:])


def test_a_file_with_no_text_is_sent_without_content(tmp_path):
    gif_path = write_workspace_file(tmp_path, "media/sneer.gif")
    channel = RecordingChannel()

    asyncio.run(
        outbound_reply.send_reply(
            channel, outbound_reply.ReplyAttachmentSplit("", [gif_path], []), [].append
        )
    )

    assert channel.sent[0][0] is None
    assert [attached.path for attached in channel.sent[0][1]] == [gif_path]


def test_nothing_is_sent_when_the_reply_has_neither_text_nor_files():
    channel = RecordingChannel()

    asyncio.run(
        outbound_reply.send_reply(
            channel, outbound_reply.ReplyAttachmentSplit("", [], []), [].append
        )
    )

    assert channel.sent == []


def test_a_missing_workspace_path_is_left_in_the_text(tmp_path):
    missing_path = str(tmp_path / "media" / "gone.gif")

    split = outbound_reply.split_reply_into_text_and_attachments(
        missing_path, str(tmp_path)
    )

    assert split.attachment_paths == []
    assert split.text == missing_path
    assert not os.path.exists(missing_path)


def test_a_reply_survives_when_discord_refuses_its_attachment(tmp_path):
    gif_path = write_workspace_file(tmp_path, "media/sneer.gif")
    channel = RecordingChannel(refuse_attachments=True)
    reported = []

    asyncio.run(
        outbound_reply.send_reply(
            channel,
            outbound_reply.ReplyAttachmentSplit("toma", [gif_path], []),
            reported.append,
        )
    )

    assert channel.sent == [("toma", None)]
    assert any("payload too large" in note for note in reported)


def test_a_refused_lone_attachment_reports_rather_than_sending_an_empty_message(
    tmp_path,
):
    gif_path = write_workspace_file(tmp_path, "media/sneer.gif")
    channel = RecordingChannel(refuse_attachments=True)
    reported = []

    asyncio.run(
        outbound_reply.send_reply(
            channel,
            outbound_reply.ReplyAttachmentSplit("", [gif_path], []),
            reported.append,
        )
    )

    assert channel.sent == []
    assert reported
