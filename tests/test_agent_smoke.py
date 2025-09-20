import pytest


@pytest.mark.smoke
def test_agent_exists(project_client, env):
    """Agent with the configured name exists in the project."""
    agents = list(project_client.agents.list_agents())  # <-- fix
    names = [a.name for a in agents]
    assert env["agent_name"] in names, (
        f"Agent '{env['agent_name']}' not found. Available: {names}"
    )


@pytest.mark.smoke
def test_agent_get_roundtrip(project_client, env):
    """We can fetch the agent and basic fields are present."""
    agents = list(project_client.agents.list_agents())  # <-- fix
    agent = next((a for a in agents if a.name == env["agent_name"]), None)
    assert agent is not None, (
        f"Agent '{env['agent_name']}' not found via list_agents()."
    )

    got = project_client.agents.get_agent(agent.id)  # <-- fix
    assert got is not None
    assert got.id == agent.id
    assert got.name == env["agent_name"]

    model_attr = getattr(got, "model", None)
    assert model_attr is not None, "Agent object has no 'model' attribute"
