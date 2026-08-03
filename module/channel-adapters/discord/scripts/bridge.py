import argparse
import asyncio
import os
import sys

import discord
from channel_access import load_access_document, message_is_for_this_agent
from harness_turn import run_one_turn

DISCORD_MESSAGE_CHARACTER_LIMIT = 2000
BOT_TOKEN_ENVIRONMENT_VARIABLE = "DISCORD_BOT_TOKEN"


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


def log(agent_name: str, message: str) -> None:
    print(f"[clawde-discord-bridge:{agent_name}] {message}", flush=True)


class AgentBridgeClient(discord.Client):
    def __init__(
        self,
        agent_name: str,
        one_shot_turn_command: str,
        workspace_directory: str,
        state_directory: str,
        daily_session_rotation: bool,
        access_document_reader,
    ):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.agent_name = agent_name
        self.one_shot_turn_command = one_shot_turn_command
        self.workspace_directory = workspace_directory
        self.state_directory = state_directory
        self.daily_session_rotation = daily_session_rotation
        self.access_document_reader = access_document_reader
        self.turn_lock = asyncio.Lock()

    async def on_ready(self):
        log(self.agent_name, f"connected as {self.user}")

    async def on_message(self, message: discord.Message):
        if not message_is_for_this_agent(
            self.access_document_reader(),
            str(message.channel.id),
            str(message.author.id),
            message.author.bot,
            self.user in message.mentions,
            message.guild is None,
        ):
            return
        async with self.turn_lock:
            async with message.channel.typing():
                reply, failure = await asyncio.to_thread(
                    run_one_turn,
                    self.one_shot_turn_command,
                    self.workspace_directory,
                    self.state_directory,
                    message.clean_content,
                    self.daily_session_rotation,
                )
        if not reply:
            log(self.agent_name, f"turn produced no reply: {failure[:400]}")
            await message.channel.send(
                f"{self.agent_name} could not answer that turn. Its log has the detail."
            )
            return
        for sendable_message in split_into_sendable_messages(reply):
            await message.channel.send(sendable_message)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="clawde-discord-bridge",
        description="Carry one clawde agent's Discord channel for a harness that has "
        "no inbound transport of its own. Each allowed message runs a single "
        "headless turn of the agent's harness, continuing the previous turn, and "
        "posts the reply back.",
    )
    parser.add_argument("--agent-name", required=True)
    parser.add_argument("--one-shot-turn-command", required=True)
    parser.add_argument("--workspace-directory", required=True)
    parser.add_argument("--state-directory", required=True)
    parser.add_argument(
        "--daily-session-rotation",
        action="store_true",
        help="Start the channel session fresh whenever the last completed turn is "
        "from an earlier local date.",
    )
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    bot_token = os.environ.get(BOT_TOKEN_ENVIRONMENT_VARIABLE, "")
    if not bot_token:
        sys.exit(
            f"{BOT_TOKEN_ENVIRONMENT_VARIABLE} is unset, so the bridge for "
            f"{arguments.agent_name} has no way to reach Discord."
        )
    AgentBridgeClient(
        arguments.agent_name,
        arguments.one_shot_turn_command,
        arguments.workspace_directory,
        arguments.state_directory,
        arguments.daily_session_rotation,
        lambda: load_access_document(arguments.state_directory),
    ).run(bot_token, log_handler=None)


if __name__ == "__main__":
    main()
