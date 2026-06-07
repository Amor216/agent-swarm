from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from . import browser, state
from .agents import PM, QA, Critic, Designer, Engineer
from .channel import Channel, Turn
from .costs import BudgetExceeded, CostTracker
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


def run(requirement: str, workdir: Path, max_rounds: int = 12,
        on_turn: Logger = _noop, max_usd: float | None = None,
        resume: bool = False) -> SwarmResult:
    workdir = workdir.resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    artifacts = workdir / "artifacts"
    artifacts.mkdir(exist_ok=True)

    static = StaticServer(workdir)
    url = static.start()

    cost = CostTracker(max_usd=max_usd)
    ch = Channel(requirement=requirement)

    start_round = 0
    speaker_override: str | None = None
    if resume:
        raw = state.load(workdir)
        if raw is not None:
            ch = state.restore_channel(raw)
            start_round = int(raw.get("round", 0))
            speaker_override = raw.get("speaker")
            for model, (i, o) in (raw.get("cost_by_model") or {}).items():
                cost.by_model[model] = (i, o)

    pm = PM(cost=cost)
    designer = Designer(cost=cost)
    engineer = Engineer(workdir=workdir, cost=cost)
    qa = QA(url=url, artifacts=artifacts, workdir=workdir, cost=cost)
    critic = Critic(workdir=workdir, cost=cost)

    agents = {
        "PM": pm, "Designer": designer, "Engineer": engineer, "QA": qa, "Critic": critic,
    }

    try:
        speaker = speaker_override or "PM"
        for round_n in range(start_round + 1, max_rounds + 1):
            try:
                turn = agents[speaker].act(ch)
            except BudgetExceeded as exc:
                _write_transcript(workdir, ch)
                state.save(workdir, requirement, ch, speaker, round_n - 1, cost.by_model)
                return SwarmResult(False, round_n, str(exc), cost, workdir)
            ch.append(turn)
            on_turn(turn)

            if speaker == "Critic" and turn.metadata.get("verdict") == "APPROVE":
                _write_transcript(workdir, ch)
                state.save(workdir, requirement, ch, "PM", round_n, cost.by_model)
                return SwarmResult(True, round_n, "critic approved", cost, workdir)

            if speaker == "PM":
                nxt = turn.metadata.get("next") or "Designer"
                if nxt == "DONE":
                    _write_transcript(workdir, ch)
                    state.save(workdir, requirement, ch, "PM", round_n, cost.by_model)
                    return SwarmResult(True, round_n, "PM signaled done", cost, workdir)
                speaker = nxt
            else:
                speaker = "PM"

            state.save(workdir, requirement, ch, speaker, round_n, cost.by_model)

        _write_transcript(workdir, ch)
        state.save(workdir, requirement, ch, speaker, max_rounds, cost.by_model)
        return SwarmResult(False, max_rounds, "max rounds reached", cost, workdir)
    finally:
        static.stop()
        browser.shutdown()


def _write_transcript(workdir: Path, ch: Channel) -> None:
    (workdir / "conversation.md").write_text(ch.transcript_md(), encoding="utf-8")
