import base64
import os
from pathlib import Path

from .. import browser
from ..channel import Channel, Turn
from ..validator import validate
from .base import Agent

WORKER_MODEL = os.environ.get("SWARM_WORKER_MODEL", "claude-sonnet-4-5")

SYSTEM = """You are QA. You are shown one screenshot of the current build.

Decide whether the project visually matches the goal and works as a static page. Be concrete:
- Does it render at all (not a blank page or error)?
- Are the main visual elements from the Designer's wireframe present?
- Anything obviously broken?

End your reply with exactly one line:
VERDICT: works | partial | broken"""


class QA(Agent):
    role = "QA"
    model = WORKER_MODEL
    system = SYSTEM
    max_tokens = 600

    def __init__(self, url: str, artifacts: Path, workdir: Path, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.url = url
        self.artifacts = artifacts
        self.workdir = workdir
        self._counter = 0

    def act(self, ch: Channel) -> Turn:
        self._counter += 1
        out = self.artifacts / f"qa-{self._counter:03d}.png"

        static_issues = validate(self.workdir)

        try:
            browser.screenshot_url(self.url, out)
        except Exception as e:
            return Turn(agent=self.role, text=f"could not take screenshot: {e}",
                        metadata={"verdict": "broken", "static_issues": _serialize(static_issues)})

        b64 = base64.b64encode(out.read_bytes()).decode()
        msgs = ch.for_agent(self.role)
        static_note = _format_static_issues(static_issues)
        text = f"Screenshot saved as {out.name}. Judge it.{static_note}"
        msgs.append({"role": "user", "content": [
            {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": b64}},
            {"type": "text", "text": text},
        ]})

        resp = self._call(msgs)
        reply = self._text_of(resp)
        verdict = _parse_verdict(reply)
        return Turn(agent=self.role, text=reply,
                    metadata={"verdict": verdict, "screenshot": str(out),
                              "static_issues": _serialize(static_issues)})


def _format_static_issues(issues: list) -> str:
    if not issues:
        return ""
    lines = "\n".join(f"  - {i.file}: {i.message}" for i in issues[:10])
    return f"\n\nStatic check found these issues before the screenshot:\n{lines}"


def _serialize(issues: list) -> list[dict]:
    return [{"file": i.file, "message": i.message} for i in issues]


def _parse_verdict(text: str) -> str:
    for line in reversed(text.splitlines()):
        line = line.strip().lower()
        if line.startswith("verdict:"):
            tail = line.split(":", 1)[1].strip()
            for v in ("works", "partial", "broken"):
                if v in tail:
                    return v
    return "partial"
