from dataclasses import dataclass, field


@dataclass
class Turn:
    agent: str
    text: str
    tool_calls: list[dict] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


@dataclass
class Channel:
    requirement: str
    turns: list[Turn] = field(default_factory=list)

    def append(self, turn: Turn) -> None:
        self.turns.append(turn)

    def for_agent(self, role: str) -> list[dict]:
        msgs: list[dict] = [{
            "role": "user",
            "content": f"Project goal: {self.requirement}",
        }]
        for t in self.turns:
            tag = "you" if t.agent == role else t.agent
            body = t.text
            if t.tool_calls:
                summaries = ", ".join(c.get("name", "?") for c in t.tool_calls)
                body = f"{body}\n(tool calls: {summaries})" if body else f"(tool calls: {summaries})"
            msgs.append({"role": "user", "content": f"[{tag}] {body}"})
        return msgs

    def transcript_md(self) -> str:
        out = ["# Swarm transcript", "", f"**Goal:** {self.requirement}", ""]
        for t in self.turns:
            out.append(f"## {t.agent}")
            out.append("")
            if t.text:
                out.append(t.text)
            if t.tool_calls:
                out.append("")
                out.append("Tool calls:")
                for c in t.tool_calls:
                    out.append(f"- `{c.get('name')}`: {c.get('args', {})}")
            if t.metadata:
                out.append("")
                out.append(f"_metadata: {t.metadata}_")
            out.append("")
        return "\n".join(out)
