import json


def prompt_with_discord_message_context(
    message, content: str, is_bot_mentioned: bool
) -> str:
    return json.dumps(
        {
            "source": "discord",
            "message_id": str(message.id),
            "chat_id": str(message.channel.id),
            "user_id": str(message.author.id),
            "is_dm": message.guild is None,
            "is_bot_mentioned": is_bot_mentioned,
            "content": content,
        },
        ensure_ascii=False,
    )
