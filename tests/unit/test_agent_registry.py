import pytest


def test_builtin_agents_and_user_override_are_discoverable_without_writing_templates(tmp_path):
    from xiliu.capabilities.agent_registry import AgentRegistry

    registry = AgentRegistry(tmp_path)
    assert {"rag", "research", "code"} <= set(registry.agents)
    assert not (tmp_path / "agents").exists()
    directory = tmp_path / "agents" / "custom"
    directory.mkdir(parents=True)
    (directory / "agent.yaml").write_text(
        "id: custom\nname: Custom\ndescription: Local search\nallowed_modes: [deep]\n"
        "allowed_tools: [app]\nnetwork_access: false\nprompt_path: prompt.md\n"
    )
    (directory / "prompt.md").write_text("Use only actual sources.")
    registry.refresh()
    assert registry.agents["custom"].prompt == "Use only actual sources."


def test_invalid_manifest_cannot_escape_or_grant_unknown_tools(tmp_path):
    from xiliu.capabilities.agent_registry import AgentRegistry

    root = tmp_path / "agents" / "bad"
    root.mkdir(parents=True)
    (root / "agent.yaml").write_text(
        "id: bad\nname: Bad\ndescription: Escape\nallowed_tools: [unknown]\n"
        "prompt_path: ../../secret.md\n"
    )
    registry = AgentRegistry(tmp_path)
    assert "bad" not in registry.agents
    assert registry.errors
    with pytest.raises(ValueError):
        registry.get("rag", "fast")
