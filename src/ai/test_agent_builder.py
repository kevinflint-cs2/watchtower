"""
Test for agent_builder.py (smoke test).
"""
import asyncio
import os

import pytest
from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from .helpers import create_agent

@pytest.mark.asyncio
async def test_agent_builder_smoke(monkeypatch):
    base_dir = os.path.dirname(__file__)
    endpoint = os.environ.get('AZURE_EXISTING_AIPROJECT_ENDPOINT')
    if not endpoint:
        pytest.skip("AZURE_EXISTING_AIPROJECT_ENDPOINT not set")
    async with DefaultAzureCredential(exclude_shared_token_cache_credential=True) as creds:
        async with AIProjectClient(credential=creds, endpoint=endpoint) as ai_client:
            agent = await create_agent(ai_client, creds, base_dir)
            fetched = await ai_client.agents.get_agent(agent.id)
            assert fetched.id == agent.id
