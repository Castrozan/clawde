import sys
import types


class StubDiscordException(Exception):
    pass


class StubDiscordFile:
    def __init__(self, path):
        self.path = path


def install_discord_stub():
    discord_stub = types.ModuleType("discord")
    discord_stub.Client = type("Client", (), {})
    discord_stub.Message = object
    discord_stub.Intents = type(
        "Intents", (), {"default": staticmethod(lambda: object())}
    )
    discord_stub.DiscordException = StubDiscordException
    discord_stub.File = StubDiscordFile
    sys.modules["discord"] = discord_stub
    return discord_stub
