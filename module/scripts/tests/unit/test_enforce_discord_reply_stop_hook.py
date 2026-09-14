import importlib.util
import json
import pathlib


def _load_hook_module():
    module_path = (
        pathlib.Path(__file__).resolve().parent.parent.parent.parent
        / "channel-adapters"
        / "discord"
        / "scripts"
        / "enforce-discord-reply-stop-hook.py"
    )
    module_spec = importlib.util.spec_from_file_location(
        "enforce_discord_reply_stop_hook", module_path
    )
    module = importlib.util.module_from_spec(module_spec)
    module_spec.loader.exec_module(module)
    return module


hook = _load_hook_module()

DISCORD_ENVELOPE = (
    '<channel source="plugin:discord:discord" chat_id="555" '
    'message_id="1" user="user1" ts="t">\nhello\n</channel>'
)


def _user(text):
    return {"type": "user", "message": {"content": text}}


def _assistant_reply(chat_id):
    return {
        "type": "assistant",
        "message": {
            "content": [
                {
                    "type": "tool_use",
                    "name": "mcp__plugin_discord_discord__reply",
                    "input": {"chat_id": chat_id, "text": "hi"},
                }
            ]
        },
    }


def _assistant_text(text):
    return {
        "type": "assistant",
        "message": {"content": [{"type": "text", "text": text}]},
    }


def test_blocks_when_discord_turn_has_no_reply():
    entries = [_user(DISCORD_ENVELOPE), _assistant_text("answered in terminal only")]
    assert hook.chat_id_needing_reply(entries, stop_hook_active=False) == "555"


def test_allows_when_reply_tool_was_called():
    entries = [_user(DISCORD_ENVELOPE), _assistant_reply("555")]
    assert hook.chat_id_needing_reply(entries, stop_hook_active=False) is None


def test_allows_non_discord_turn():
    entries = [_user("Heartbeat tick. Read HEARTBEAT.md."), _assistant_text("idle")]
    assert hook.chat_id_needing_reply(entries, stop_hook_active=False) is None


def test_fails_open_on_second_pass_to_avoid_infinite_loop():
    entries = [_user(DISCORD_ENVELOPE), _assistant_text("still no reply")]
    assert hook.chat_id_needing_reply(entries, stop_hook_active=True) is None


def test_enforces_reply_to_newest_discord_message_even_after_earlier_reply():
    entries = [
        _user(DISCORD_ENVELOPE),
        _assistant_reply("555"),
        _user(
            '<channel source="plugin:discord:discord" chat_id="777" '
            'message_id="2" user="user1" ts="t">\nfollow up\n</channel>'
        ),
        _assistant_text("answered the new one in terminal"),
    ]
    assert hook.chat_id_needing_reply(entries, stop_hook_active=False) == "777"


def _write_transcript(tmp_path, entries):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text("".join(json.dumps(entry) + "\n" for entry in entries))
    return transcript


def test_tail_reader_returns_suffix_from_newest_discord_turn(tmp_path):
    entries = (
        [_assistant_text(f"old work {index}") for index in range(2000)]
        + [_user(DISCORD_ENVELOPE)]
        + [_assistant_text("answered in terminal only")]
    )
    transcript = _write_transcript(tmp_path, entries)
    tail = hook.read_transcript_tail_through_latest_discord_turn(str(transcript))
    assert len(tail) == 2
    assert hook.user_entry_carries_discord_envelope(tail[0])
    assert hook.chat_id_needing_reply(tail, stop_hook_active=False) == "555"


def test_tail_reader_decision_matches_full_parse_when_reply_present(tmp_path):
    entries = (
        [_assistant_text(f"old work {index}") for index in range(500)]
        + [_user(DISCORD_ENVELOPE)]
        + [_assistant_reply("555")]
    )
    transcript = _write_transcript(tmp_path, entries)
    tail = hook.read_transcript_tail_through_latest_discord_turn(str(transcript))
    assert hook.chat_id_needing_reply(tail, stop_hook_active=False) is None


def test_tail_reader_ignores_older_unanswered_discord_turn(tmp_path):
    entries = [
        _user(DISCORD_ENVELOPE),
        _assistant_text("never answered the old one"),
        _user(
            '<channel source="plugin:discord:discord" chat_id="777" '
            'message_id="2" user="user1" ts="t">\nnewer\n</channel>'
        ),
        _assistant_reply("777"),
    ]
    transcript = _write_transcript(tmp_path, entries)
    tail = hook.read_transcript_tail_through_latest_discord_turn(str(transcript))
    assert hook.chat_id_needing_reply(tail, stop_hook_active=False) is None


def test_tail_reader_handles_missing_trailing_newline(tmp_path):
    transcript = tmp_path / "transcript.jsonl"
    transcript.write_text(
        json.dumps(_user(DISCORD_ENVELOPE))
        + "\n"
        + json.dumps(_assistant_text("answered in terminal only"))
    )
    tail = hook.read_transcript_tail_through_latest_discord_turn(str(transcript))
    assert hook.chat_id_needing_reply(tail, stop_hook_active=False) == "555"


def test_tail_reader_returns_empty_for_missing_file(tmp_path):
    missing = tmp_path / "does-not-exist.jsonl"
    assert hook.read_transcript_tail_through_latest_discord_turn(str(missing)) == []
