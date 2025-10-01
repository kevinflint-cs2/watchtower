import os
import pytest
import asyncio
import pytest_asyncio
from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from azure.core.exceptions import ResourceNotFoundError

from dotenv import load_dotenv

# Load root .env before tests
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

# Ensure pytest-asyncio is registered
pytest_plugins = ["pytest_asyncio"]

@pytest.mark.asyncio
async def test_smoke_agent_exists():
    endpoint = os.environ.get('AZURE_EXISTING_AIPROJECT_ENDPOINT')
    assert endpoint, "AZURE_EXISTING_AIPROJECT_ENDPOINT must be set."
    agent_id = os.environ.get('SMOKE_AGENT_ID')
    assert agent_id, "SMOKE_AGENT_ID must be set to the test agent's id."
    async with DefaultAzureCredential(exclude_shared_token_cache_credential=True) as creds:
        async with AIProjectClient(credential=creds, endpoint=endpoint) as ai_client:
            agent_client = ai_client.agents
            try:
                agent = await agent_client.get_agent(agent_id)
                assert agent is not None
                assert agent.id == agent_id
            except ResourceNotFoundError:
                pytest.fail(f"Agent with id {agent_id} not found.")
