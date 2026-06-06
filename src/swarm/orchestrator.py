from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import browser
from .agents import PM, QA, Critic, Designer, Engineer
from .channel import Channel, Turn
from .costs import CostTracker
from .server import StaticServer


@dataclass
class SwarmResult:
    ok: bool
    rounds: int
    reason: str
    cost: CostTracker
    workdir: Path


Logger = Callable[[Turn], None]


def _noop(_: Turn) -> None:
    pass


def run(requirement: str, workdir: Path, max_rounds: int = 8,
        on_turn: Logger = _noop) -> SwarmResult:
    workdir = workdir.resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    artifacts = workdir / "artifacts"
    artifacts.mkdir(exist_ok=True)

    static = StaticServer(workdir)
    url = static.start()

    cost = CostTracker()
    ch = Channel(requirement=requirement)

    pm = PM(cost=cost)
    designer = Designer(cost=cost)
    engineer = Engineer(workdir=workdir, cost=cost)
    qa = QA(url=url, artifacts=artifacts, cost=cost)
    critic = Critic(workdir=workdir, cost=cost)

    agents = {
        "PM": pm, "Designer": designer, "Engineer": engineer, "QA": qa, "Critic": critic,
    }

    try:
        speaker = "PM"
        for round_n in range(1, max_rounds + 1):
            turn = agents[speaker].act(ch)
            ch.append(turn)
            on_turn(turn)

            if speaker == "Critic" and turn.metadata.get("verdict") == "APPROVE":
                _write_transcript(workdir, ch)
                return SwarmResult(True, round_n, "critic approved", cost, workdir)

            if speaker == "PM":
                nxt = turn.metadata.get("next") or "Designer"
                if nxt == "DONE":
                    _write_transcript(workdir, ch)
                    return SwarmResult(True, round_n, "PM signaled done", cost, workdir)
                speaker = nxt
                continue

            speaker = "PM"

        _write_transcript(workdir, ch)
        return SwarmResult(False, max_rounds, "max rounds reached", cost, workdir)
    finally:
        static.stop()
        browser.shutdown()


def _write_transcript(workdir: Path, ch: Channel) -> None:
    (workdir / "conversation.md").write_text(ch.transcript_md(), encoding="utf-8")
