from pathlib import Path
from unittest.mock import MagicMock, patch

from swarm import orchestrator
from swarm.channel import Turn


def _agent_returning(role: str, turn: Turn) -> MagicMock:
    a = MagicMock()
    a.act.return_value = turn
    return a


def _patch_agents(designer, engineer, qa, critic, pm):
    return {
        "PM": pm, "Designer": designer, "Engineer": engineer, "QA": qa, "Critic": critic,
    }


def test_happy_path_approves_first_try(tmp_path: Path):
    pm1 = Turn(agent="PM", text="plan", metadata={"next": "Designer"})
    pm2 = Turn(agent="PM", text="ok", metadata={"next": "Engineer"})
    pm3 = Turn(agent="PM", text="ok", metadata={"next": "QA"})
    pm4 = Turn(agent="PM", text="ok", metadata={"next": "Critic"})

    designer_turn = Turn(agent="Designer", text="wireframe")
    engineer_turn = Turn(agent="Engineer", text="wrote files")
    qa_turn = Turn(agent="QA", text="screenshot ok", metadata={"verdict": "works"})
    critic_turn = Turn(agent="Critic", text="lgtm", metadata={"verdict": "APPROVE"})

    pm = MagicMock()
    pm.act.side_effect = [pm1, pm2, pm3, pm4]

    designer = _agent_returning("Designer", designer_turn)
    engineer = _agent_returning("Engineer", engineer_turn)
    qa = _agent_returning("QA", qa_turn)
    critic = _agent_returning("Critic", critic_turn)

    with patch("swarm.orchestrator.PM", return_value=pm), \
         patch("swarm.orchestrator.Designer", return_value=designer), \
         patch("swarm.orchestrator.Engineer", return_value=engineer), \
         patch("swarm.orchestrator.QA", return_value=qa), \
         patch("swarm.orchestrator.Critic", return_value=critic), \
         patch("swarm.orchestrator.StaticServer") as mock_server, \
         patch("swarm.orchestrator.browser"):
        mock_server.return_value.start.return_value = "http://127.0.0.1:0/index.html"
        result = orchestrator.run("snake", tmp_path)

    assert result.ok
    assert result.reason == "critic approved"
    assert (tmp_path / "conversation.md").exists()


def test_max_rounds_gives_up(tmp_path: Path):
    pm_always = Turn(agent="PM", text="...", metadata={"next": "Designer"})
    designer_turn = Turn(agent="Designer", text="...")

    pm = MagicMock()
    pm.act.return_value = pm_always
    designer = _agent_returning("Designer", designer_turn)
    engineer = MagicMock()
    qa = MagicMock()
    critic = MagicMock()

    with patch("swarm.orchestrator.PM", return_value=pm), \
         patch("swarm.orchestrator.Designer", return_value=designer), \
         patch("swarm.orchestrator.Engineer", return_value=engineer), \
         patch("swarm.orchestrator.QA", return_value=qa), \
         patch("swarm.orchestrator.Critic", return_value=critic), \
         patch("swarm.orchestrator.StaticServer") as mock_server, \
         patch("swarm.orchestrator.browser"):
        mock_server.return_value.start.return_value = "http://127.0.0.1:0/index.html"
        result = orchestrator.run("x", tmp_path, max_rounds=4)

    assert not result.ok
    assert "max rounds" in result.reason


def test_pm_says_done_short_circuits(tmp_path: Path):
    pm = MagicMock()
    pm.act.return_value = Turn(agent="PM", text="trivial", metadata={"next": "DONE"})
    designer = MagicMock()
    engineer = MagicMock()
    qa = MagicMock()
    critic = MagicMock()

    with patch("swarm.orchestrator.PM", return_value=pm), \
         patch("swarm.orchestrator.Designer", return_value=designer), \
         patch("swarm.orchestrator.Engineer", return_value=engineer), \
         patch("swarm.orchestrator.QA", return_value=qa), \
         patch("swarm.orchestrator.Critic", return_value=critic), \
         patch("swarm.orchestrator.StaticServer") as mock_server, \
         patch("swarm.orchestrator.browser"):
        mock_server.return_value.start.return_value = "http://127.0.0.1:0/index.html"
        result = orchestrator.run("x", tmp_path)

    assert result.ok
    assert "done" in result.reason.lower()
