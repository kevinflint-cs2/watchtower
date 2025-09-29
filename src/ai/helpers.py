"""
Helper functions for agent creation and future multi-agent support.
"""
import os
from azure.ai.projects.aio import AIProjectClient
from azure.core.credentials_async import AsyncTokenCredential
from azure.ai.agents.models import AsyncToolSet, AzureAISearchTool
import logging

logger = logging.getLogger("agent_helpers")

async def create_agent(ai_client: AIProjectClient, creds: AsyncTokenCredential, base_dir: str):
    # Minimal agent creation for smoke test
    # You can expand this for more complex agents later
    toolset = AsyncToolSet()
    # For smoke test, no tools or a dummy tool can be added
    instructions = "Smoke test agent."
    agent = await ai_client.agents.create_agent(
        model=os.environ["AZURE_AI_AGENT_DEPLOYMENT_NAME"],
        name=os.environ["AZURE_AI_AGENT_NAME"],
        instructions=instructions,
        toolset=toolset
    )
    return agent
