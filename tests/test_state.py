from pathlib import Path

from swarm import state
from swarm.channel import Channel, Turn


def test_roundtrip(tmp_path: Path):
    ch = Channel(requirement="build me a thing")
    ch.append(Turn(agent="PM", text="plan",
                   metadata={"next": "Designer"}))
    ch.append(Turn(agent="Designer", text="wireframe"))

    state.save(tmp_path, "build me a thing", ch, "PM", 2,
               cost_by_model={"claude-opus-4-5": (100, 50)})

    raw = state.load(tmp_path)
    assert raw is not None
    assert raw["round"] == 2
    assert raw["speaker"] == "PM"
    assert raw["cost_by_model"]["claude-opus-4-5"] == [100, 50]

    restored = state.restore_channel(raw)
    assert restored.requirement == "build me a thing"
    assert len(restored.turns) == 2
    assert restored.turns[0].metadata["next"] == "Designer"


def test_load_missing(tmp_path: Path):
    assert state.load(tmp_path) is None
