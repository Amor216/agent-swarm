from swarm.channel import Channel, Turn


def test_empty_channel_just_has_goal():
    ch = Channel(requirement="Build a calculator")
    msgs = ch.for_agent("Engineer")
    assert len(msgs) == 1
    assert "calculator" in msgs[0]["content"]


def test_turns_get_role_prefix():
    ch = Channel(requirement="x")
    ch.append(Turn(agent="PM", text="Plan."))
    ch.append(Turn(agent="Designer", text="Wireframe."))
    msgs = ch.for_agent("Engineer")
    assert "[PM] Plan." in msgs[1]["content"]
    assert "[Designer] Wireframe." in msgs[2]["content"]


def test_speaker_sees_own_turn_as_you():
    ch = Channel(requirement="x")
    ch.append(Turn(agent="Engineer", text="wrote it"))
    msgs = ch.for_agent("Engineer")
    assert "[you] wrote it" in msgs[1]["content"]


def test_transcript_md_includes_metadata():
    ch = Channel(requirement="x")
    ch.append(Turn(agent="Critic", text="ok", metadata={"verdict": "APPROVE"}))
    md = ch.transcript_md()
    assert "Critic" in md
    assert "APPROVE" in md
