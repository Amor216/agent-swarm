from __future__ import annotations

import anthropic

from ..channel import Channel, Turn
from ..costs import CostTracker


class Agent:
    role: str = "Agent"
    model: str = "claude-sonnet-4-5"
    system: str = ""
    max_tokens: int = 1024
    tools: list[dict] = []

    def __init__(self, cost: CostTracker, client: anthropic.Anthropic | None = None) -> None:
        self.cost = cost
        self.client = client or anthropic.Anthropic()

    def act(self, ch: Channel) -> Turn:  # pragma: no cover - subclasses override
        raise NotImplementedError

    def _call(self, messages: list[dict], extra_system: str | None = None,
              tools: list[dict] | None = None, max_tokens: int | None = None):
        kwargs: dict = {
            "model": self.model,
            "max_tokens": max_tokens or self.max_tokens,
            "system": (self.system + ("\n\n" + extra_system if extra_system else "")).strip(),
            "messages": messages,
        }
        if tools or self.tools:
            kwargs["tools"] = tools or self.tools
        resp = self.client.messages.create(**kwargs)
        self.cost.add(self.model, resp.usage.input_tokens, resp.usage.output_tokens)
        return resp

    @staticmethod
    def _text_of(resp) -> str:
        return "".join(b.text for b in resp.content if b.type == "text").strip()

    @staticmethod
    def _tool_uses(resp) -> list:
        return [b for b in resp.content if b.type == "tool_use"]
