import os
from pathlib import Path

from ..channel import Channel, Turn
from ..tools import Tool, build_file_tools
from .base import Agent

CRITIC_MODEL = os.environ.get("SWARM_CRITIC_MODEL", "claude-opus-4-5")

SYSTEM = """You are the Critic. You review the Engineer's code and QA's screenshot summary.

Use `read_file` to inspect files when you need to. Be concrete: name files and what's wrong.
Do not request stylistic changes. Only flag things that genuinely break the user goal.

When you decide, call the `decide` tool with APPROVE or REQUEST_FIX. If REQUEST_FIX, give the Engineer a brief, actionable list of what to change."""

DECIDE_TOOL = {
    "name": "decide",
    "description": "Final review decision.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {"type": "string", "enum": ["APPROVE", "REQUEST_FIX"]},
            "notes": {"type": "string", "description": "Concrete reasoning. If REQUEST_FIX, list what to change."},
        },
        "required": ["verdict", "notes"],
    },
}


class Critic(Agent):
    role = "Critic"
    model = CRITIC_MODEL
    system = SYSTEM
    max_tokens = 1024

    def __init__(self, workdir: Path, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        file_tools = build_file_tools(workdir)
        self._by_name = {t.name: t for t in file_tools if t.name == "read_file"}
        self.tools = [self._by_name["read_file"].schema(), DECIDE_TOOL]

    def act(self, ch: Channel) -> Turn:
        msgs = ch.for_agent(self.role)
        all_calls: list[dict] = []

        for _ in range(6):
            resp = self._call(msgs, tools=self.tools)
            assistant_blocks = [_block_to_dict(b) for b in resp.content]
            msgs.append({"role": "assistant", "content": assistant_blocks})

            uses = self._tool_uses(resp)
            if not uses:
                text = self._text_of(resp)
                return Turn(agent=self.role, text=text or "no decision",
                            tool_calls=all_calls, metadata={"verdict": "REQUEST_FIX"})

            results = []
            for u in uses:
                all_calls.append({"name": u.name, "args": u.input})
                if u.name == "decide":
                    return Turn(
                        agent=self.role,
                        text=u.input.get("notes", ""),
                        tool_calls=all_calls,
                        metadata={"verdict": u.input.get("verdict", "REQUEST_FIX")},
                    )
                results.append(_run_read(self._by_name, u))
            msgs.append({"role": "user", "content": results})

        return Turn(agent=self.role, text="no decision in time",
                    tool_calls=all_calls, metadata={"verdict": "REQUEST_FIX"})


def _block_to_dict(b) -> dict:
    if b.type == "text":
        return {"type": "text", "text": b.text}
    if b.type == "tool_use":
        return {"type": "tool_use", "id": b.id, "name": b.name, "input": b.input}
    return b.model_dump()


def _run_read(by_name: dict[str, Tool], block) -> dict:
    try:
        out = by_name[block.name].handler(block.input)
        return {"type": "tool_result", "tool_use_id": block.id, "content": out}
    except KeyError:
        return {"type": "tool_result", "tool_use_id": block.id,
                "content": f"unknown tool: {block.name}", "is_error": True}
    except Exception as e:
        return {"type": "tool_result", "tool_use_id": block.id,
                "content": f"{type(e).__name__}: {e}", "is_error": True}
