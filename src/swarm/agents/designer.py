import os

from ..channel import Channel, Turn
from .base import Agent

WORKER_MODEL = os.environ.get("SWARM_WORKER_MODEL", "claude-sonnet-4-5")

SYSTEM = """You are the Designer in a tiny software team. The PM has given a goal.

Produce:
1) A short ASCII wireframe of the final UI (use box characters and labels).
2) 3-5 bullet points describing the UX: inputs, outputs, key interactions.

Keep it tight. The Engineer will use your wireframe as the spec. Do NOT write code.
Do NOT discuss architecture or libraries. Just the visual layout and what the user does."""


class Designer(Agent):
    role = "Designer"
    model = WORKER_MODEL
    system = SYSTEM
    max_tokens = 800

    def act(self, ch: Channel) -> Turn:
        resp = self._call(ch.for_agent(self.role))
        return Turn(agent=self.role, text=self._text_of(resp))
