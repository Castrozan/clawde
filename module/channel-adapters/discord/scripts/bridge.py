import argparse
import asyncio
import os
import sys

import discord
from channel_access import load_access_document, message_is_for_this_agent
from channel_turn_harness import (
    record_channel_turn_productivity,
    resolve_active_one_shot_turn_command,
)
from channel_message.inbound_media import prompt_for_message_with_media
from channel_message.outbound_reply import (
    send_reply,
    split_reply_into_text_and_attachments,
)
from harness_turn import run_one_turn

BOT_TOKEN_ENVIRONMENT_VARIABLE = "DISCORD_BOT_TOKEN"


def log(agent_name: str, message: str) -> None:
    print(f"[clawde-discord-bridge:{agent_name}] {message}", flush=True)


class AgentBridgeClient(discord.Client):
    def __init__(
        self,
        agent_name: str,
        launch_config_path: str,
        workspace_directory: str,
        state_directory: str,
        daily_session_rotation: bool,
        access_document_reader,
    ):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.agent_name = agent_name
        self.launch_config_path = launch_config_path
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
                active_harness_name, one_shot_turn_command = (
                    resolve_active_one_shot_turn_command(self.launch_config_path)
                )
                if one_shot_turn_command is None:
                    log(
                        self.agent_name,
                        f"active harness {active_harness_name} has no one-shot "
                        "turn command to answer Discord with",
                    )
                    await message.channel.send(
                        f"{self.agent_name} cannot answer turns on "
                        f"{active_harness_name}."
                    )
                    return
                prompt = await prompt_for_message_with_media(
                    message,
                    self.state_directory,
                    lambda note: log(self.agent_name, note),
                )
                if not prompt.strip():
                    log(
                        self.agent_name,
                        f"message {message.id} carried nothing this bridge can render",
                    )
                    return
                reply, failure = await asyncio.to_thread(
                    run_one_turn,
                    one_shot_turn_command,
                    self.workspace_directory,
                    self.state_directory,
                    prompt,
                    self.daily_session_rotation,
                )
                record_channel_turn_productivity(
                    self.launch_config_path,
                    self.agent_name,
                    active_harness_name,
                    turn_was_productive=bool(reply),
                )
        if not reply:
            log(self.agent_name, f"turn produced no reply: {failure[:400]}")
            if failure:
                await message.channel.send(
                    f"{self.agent_name} could not answer that turn. Its log has the detail."
                )
            return
        split = split_reply_into_text_and_attachments(reply, self.workspace_directory)
        for refused_path in split.refused_paths:
            log(self.agent_name, f"refused to attach {refused_path}")
        await send_reply(
            message.channel, split, lambda note: log(self.agent_name, note)
        )


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="clawde-discord-bridge",
        description="Carry one clawde agent's Discord channel for a harness that has "
        "no inbound transport of its own. Each allowed message runs a single "
        "headless turn of the agent's harness, continuing the previous turn, and "
        "posts the reply back.",
    )
    parser.add_argument("--agent-name", required=True)
    parser.add_argument("--launch-config", required=True)
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
        arguments.launch_config,
        arguments.workspace_directory,
        arguments.state_directory,
        arguments.daily_session_rotation,
        lambda: load_access_document(arguments.state_directory),
    ).run(bot_token, log_handler=None)


if __name__ == "__main__":
    main()
