from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from .channel import Turn

COLORS = {
    "PM": "cyan",
    "Designer": "magenta",
    "Engineer": "green",
    "QA": "yellow",
    "Critic": "red",
    "System": "white",
}


def panel(console: Console, turn: Turn) -> None:
    color = COLORS.get(turn.agent, "white")
    body = Text()
    if turn.text:
        body.append(turn.text)
    if turn.tool_calls:
        if body.plain:
            body.append("\n\n")
        for call in turn.tool_calls:
            args = call.get("args", {})
            summary = _summarize(call.get("name", "?"), args)
            body.append(f"- {summary}\n", style="dim")
    if turn.metadata:
        verdict = turn.metadata.get("verdict")
        nxt = turn.metadata.get("next")
        if verdict:
            body.append(f"\nVERDICT: {verdict}", style="bold")
        if nxt:
            body.append(f"\nNEXT: {nxt}", style="bold")
    console.print(Panel(body or Text("(silent)"), title=f"[{color}]{turn.agent}[/{color}]",
                        border_style=color, padding=(0, 1)))


def _summarize(name: str, args: dict) -> str:
    if name == "write_file":
        path = args.get("path", "?")
        size = len(args.get("content", "") or "")
        return f"write_file {path} ({size} bytes)"
    if name == "replace_in_file":
        path = args.get("path", "?")
        return f"replace_in_file {path}"
    if name == "read_file":
        return f"read_file {args.get('path', '?')}"
    if name == "list_dir":
        return f"list_dir {args.get('path', '.')}"
    short_args = ", ".join(f"{k}={_short(v)}" for k, v in args.items())
    return f"{name}({short_args})"


def _short(v) -> str:
    s = str(v)
    return s if len(s) < 50 else s[:47] + "..."
