"""
Standalone script to build and test a single AI Agent (smoke test).
"""
import os
import asyncio
import logging
from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from azure.core.credentials_async import AsyncTokenCredential

from helpers import create_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent_builder")

async def main():
    base_dir = os.path.dirname(__file__)
    endpoint = os.environ.get('AZURE_EXISTING_AIPROJECT_ENDPOINT')
    if not endpoint:
        raise RuntimeError("AZURE_EXISTING_AIPROJECT_ENDPOINT must be set.")
    async with DefaultAzureCredential(exclude_shared_token_cache_credential=True) as creds:
        async with AIProjectClient(credential=creds, endpoint=endpoint) as ai_client:
            agent = await create_agent(ai_client, creds, base_dir)
            logger.info(f"Created agent: {agent.id} (name: {agent.name})")
            # Smoke test: fetch agent by ID
            fetched = await ai_client.agents.get_agent(agent.id)
            assert fetched.id == agent.id, "Smoke test failed: Agent ID mismatch"
            logger.info("Smoke test passed: Agent created and fetched successfully.")

if __name__ == "__main__":
    asyncio.run(main())
