import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from .channel import Channel, Turn

STATE_FILE = "state.json"


def state_path(workdir: Path) -> Path:
    return workdir / STATE_FILE


def save(workdir: Path, requirement: str, channel: Channel, speaker: str,
         round_n: int, cost_by_model: dict[str, tuple[int, int]]) -> None:
    payload: dict[str, Any] = {
        "requirement": requirement,
        "round": round_n,
        "speaker": speaker,
        "cost_by_model": {m: list(v) for m, v in cost_by_model.items()},
        "turns": [asdict(t) for t in channel.turns],
    }
    state_path(workdir).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load(workdir: Path) -> dict[str, Any] | None:
    p = state_path(workdir)
    if not p.exists():
        return None
    raw = json.loads(p.read_text(encoding="utf-8"))
    return raw


def restore_channel(raw: dict[str, Any]) -> Channel:
    ch = Channel(requirement=raw["requirement"])
    for t in raw.get("turns", []):
        ch.append(Turn(
            agent=t["agent"],
            text=t["text"],
            tool_calls=t.get("tool_calls", []),
            metadata=t.get("metadata", {}),
        ))
    return ch
