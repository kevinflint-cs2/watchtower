"""
Script to delete all AI agents in the current Azure AI Project.
"""
import os
from dotenv import load_dotenv
import asyncio
import logging

from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from azure.core.exceptions import ResourceNotFoundError

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("cleanup_agents")

async def delete_all_agents():
    endpoint = os.environ.get('AZURE_EXISTING_AIPROJECT_ENDPOINT')
    if not endpoint:
        raise RuntimeError("AZURE_EXISTING_AIPROJECT_ENDPOINT must be set.")
    async with DefaultAzureCredential(exclude_shared_token_cache_credential=True) as creds:
        async with AIProjectClient(credential=creds, endpoint=endpoint) as ai_client:
            agent_client = ai_client.agents
            logger.info("Listing all agents...")
            agent_list = agent_client.list_agents()
            deleted = 0
            async for agent in agent_list:
                try:
                    logger.info(f"Deleting agent: {agent.id} ({agent.name})")
                    await agent_client.delete_agent(agent.id)
                    deleted += 1
                except ResourceNotFoundError:
                    logger.warning(f"Agent {agent.id} already deleted or not found.")
                except Exception as e:
                    logger.error(f"Failed to delete agent {agent.id}: {e}")
            logger.info(f"Deleted {deleted} agents.")

if __name__ == "__main__":
    # Load root .env
    load_dotenv()
    try:
        asyncio.run(delete_all_agents())
    except ResourceNotFoundError as e:
        logger.warning(f"Paging complete or all agents deleted: {e}")
        logger.info("Cleanup complete. No agents remain.")
