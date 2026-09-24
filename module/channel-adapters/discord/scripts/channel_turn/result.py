import json
from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelTurnResult:
    reply: str = ""
    failure: str | None = None
    discarded_reply_reason: str | None = None

    @property
    def succeeded(self) -> bool:
        return self.failure is None


def completed_channel_turn(reply: str) -> ChannelTurnResult:
    if not reply.strip():
        return ChannelTurnResult()
    try:
        envelope = json.loads(reply)
    except ValueError:
        return ChannelTurnResult(discarded_reply_reason="reply is not a JSON envelope")
    if not isinstance(envelope, dict) or set(envelope) != {"action", "text"}:
        return ChannelTurnResult(discarded_reply_reason="invalid reply envelope fields")
    action, text = envelope["action"], envelope["text"]
    if not isinstance(action, str) or not isinstance(text, str):
        return ChannelTurnResult(discarded_reply_reason="invalid reply envelope types")
    if action == "silence" and text == "":
        return ChannelTurnResult()
    if action == "reply" and text.strip():
        return ChannelTurnResult(reply=text.strip())
    return ChannelTurnResult(discarded_reply_reason="invalid reply action or text")
