from dataclasses import dataclass

SILENCE_PLACEHOLDERS = frozenset({"(no reply)", "(mute)", "(sem resposta)"})


@dataclass(frozen=True)
class ChannelTurnResult:
    reply: str = ""
    failure: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.failure is None


def completed_channel_turn(reply: str) -> ChannelTurnResult:
    reply = reply.strip()
    if reply.casefold() in SILENCE_PLACEHOLDERS:
        reply = ""
    return ChannelTurnResult(reply=reply)
