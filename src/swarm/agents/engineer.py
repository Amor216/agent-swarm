import os
from pathlib import Path

from ..channel import Channel, Turn
from ..tools import Tool, build_file_tools
from .base import Agent

WORKER_MODEL = os.environ.get("SWARM_WORKER_MODEL", "claude-sonnet-4-5")
MAX_STEPS = 8

SYSTEM = """You are the Engineer in a tiny software team. Read the Designer's wireframe and any QA/Critic feedback, then write or edit the actual files.

Constraints:
- The project must run by opening `index.html` in a browser. No build step. Use vanilla HTML, CSS, JS.
- Keep it to a handful of files. Inline small CSS, separate JS into game.js or app.js if it grows past ~50 lines.
- Use `write_file` for new files and `replace_in_file` for targeted edits. Read before you write when fixing.
- Stop after you've finished the edit. The verifier will run it; you do not announce success."""


class Engineer(Agent):
    role = "Engineer"
    model = WORKER_MODEL
    system = SYSTEM
    max_tokens = 3072

    def __init__(self, workdir: Path, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.workdir = workdir
        self._tools = build_file_tools(workdir)
        self._by_name = {t.name: t for t in self._tools}
        self.tools = [t.schema() for t in self._tools]

    def act(self, ch: Channel) -> Turn:
        msgs = ch.for_agent(self.role)
        all_calls: list[dict] = []

        for _ in range(MAX_STEPS):
            resp = self._call(msgs, tools=self.tools)
            assistant_blocks = [_block_to_dict(b) for b in resp.content]
            msgs.append({"role": "assistant", "content": assistant_blocks})

            uses = self._tool_uses(resp)
            if not uses:
                text = self._text_of(resp) or "edits applied"
                return Turn(agent=self.role, text=text, tool_calls=all_calls)

            results = []
            for u in uses:
                all_calls.append({"name": u.name, "args": u.input})
                results.append(_run_tool(self._by_name, u))
            msgs.append({"role": "user", "content": results})

        return Turn(agent=self.role, text="max steps reached", tool_calls=all_calls)


def _block_to_dict(b) -> dict:
    if b.type == "text":
        return {"type": "text", "text": b.text}
    if b.type == "tool_use":
        return {"type": "tool_use", "id": b.id, "name": b.name, "input": b.input}
    return b.model_dump()


def _run_tool(by_name: dict[str, Tool], block) -> dict:
    try:
        out = by_name[block.name].handler(block.input)
        return {"type": "tool_result", "tool_use_id": block.id, "content": out}
    except KeyError:
        return {"type": "tool_result", "tool_use_id": block.id,
                "content": f"unknown tool: {block.name}", "is_error": True}
    except Exception as e:
        return {"type": "tool_result", "tool_use_id": block.id,
                "content": f"{type(e).__name__}: {e}", "is_error": True}
