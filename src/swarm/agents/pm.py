import os

from ..channel import Channel, Turn
from .base import Agent

PM_MODEL = os.environ.get("SWARM_PM_MODEL", "claude-opus-4-5")

SYSTEM = """You are the PM of a tiny software team. Your job is to break the goal into concrete steps and decide who speaks next.

Roster:
- Designer: produces an ASCII wireframe and brief UX notes.
- Engineer: writes and edits the actual files.
- QA: runs the result in a headless browser and reports whether it works.
- Critic: reviews code + screenshot and decides APPROVE or REQUEST_FIX.

Rules:
- Open with a one-paragraph plan, then call `choose_next` to pick the first speaker.
- After the team has worked, you may be asked again. Pick the next speaker based on what just happened.
  Common flow: Designer -> Engineer -> QA -> Critic. If Critic says REQUEST_FIX, send Engineer again, then QA, then Critic.
- Set `next` to "DONE" only when the Critic has APPROVE'd.
- Be brief. The team reads your notes."""

CHOOSE_NEXT_TOOL = {
    "name": "choose_next",
    "description": "Pick which agent speaks next, or DONE to terminate.",
    "input_schema": {
        "type": "object",
        "properties": {
            "next": {"type": "string", "enum": ["Designer", "Engineer", "QA", "Critic", "DONE"]},
            "reason": {"type": "string", "description": "One sentence explaining the pick."},
        },
        "required": ["next", "reason"],
    },
}


class PM(Agent):
    role = "PM"
    model = PM_MODEL
    system = SYSTEM
    tools = [CHOOSE_NEXT_TOOL]

    def act(self, ch: Channel) -> Turn:
        msgs = ch.for_agent(self.role)
        msgs.append({
            "role": "user",
            "content": "Speak briefly, then call `choose_next` with the next agent.",
        })
        for _ in range(2):
            resp = self._call(msgs, max_tokens=1024)
            uses = self._tool_uses(resp)
            text = self._text_of(resp)
            if uses:
                u = uses[0]
                return Turn(
                    agent=self.role,
                    text=text or "(picking next)",
                    tool_calls=[{"name": u.name, "args": u.input}],
                    metadata={"next": u.input.get("next"), "reason": u.input.get("reason", "")},
                )
            msgs.append({"role": "assistant", "content": [{"type": "text", "text": text}]})
            msgs.append({
                "role": "user",
                "content": "You must call the `choose_next` tool. Try again.",
            })
        return Turn(agent=self.role, text="failed to pick next speaker",
                    metadata={"next": "DONE", "reason": "PM did not choose"})
