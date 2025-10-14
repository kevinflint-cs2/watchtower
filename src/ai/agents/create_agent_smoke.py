"""
create_agent_smoke.py

Standalone script to create a simple smoke test agent in Azure AI Project.
"""

import json
import logging
import os

from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

# Optional: Enable Application Insights trace logging if connection string is set
try:
    from azure.monitor.opentelemetry import configure_azure_monitor
except ImportError:
    configure_azure_monitor = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("create_agent_smoke")

# Load the .env file from the current working directory (default behavior)
load_dotenv()

# Optional: Application Insights connection string for tracing
APPINSIGHTS_CONNECTION_STRING = os.environ.get("AZURE_APPINSIGHTS_CONNECTION_STRING")

# Fail fast if Application Insights connection string is not provided. This
# ensures smoke agents are only created when tracing is available.
if not APPINSIGHTS_CONNECTION_STRING:
    logger.error("AZURE_APPINSIGHTS_CONNECTION_STRING is not set in the environment. Aborting smoke agent creation.")
    raise RuntimeError(
        "AZURE_APPINSIGHTS_CONNECTION_STRING must be set in the root .env to create a smoke agent with tracing enabled."
    )


# Get the Azure AI Project endpoint from the environment and strip quotes if present
PROJECT_ENDPOINT = os.environ.get("AZURE_EXISTING_AIPROJECT_ENDPOINT")
if PROJECT_ENDPOINT:
    PROJECT_ENDPOINT = PROJECT_ENDPOINT.strip('"').strip("'")
if not PROJECT_ENDPOINT:
    raise RuntimeError("AZURE_EXISTING_AIPROJECT_ENDPOINT must be set in the root .env file.")

# Hardcoded agent parameters
AGENT_NAME = "smoke-agent"
AGENT_MODEL = "gpt-4o-mini"  # Change as needed for your deployment
AGENT_DESCRIPTION = "A simple smoke test agent"
AGENT_INSTRUCTIONS = "This is a minimal smoke test agent, respond only with 'No smoke found'"

# Path to ai_state.json
AI_STATE_PATH = os.path.join(os.path.dirname(__file__), "ai_state.json")


def main():
    """
    Main function to create a smoke test agent in the Azure AI Project.
    """

    # Enable Application Insights tracing if connection string is set
    if APPINSIGHTS_CONNECTION_STRING and configure_azure_monitor:
        try:
            configure_azure_monitor(connection_string=APPINSIGHTS_CONNECTION_STRING)
            logger.info("Configured Application Insights for tracing.")
        except Exception as e:
            logger.exception("Failed to configure azure monitor opentelemetry: %s", e)
    elif APPINSIGHTS_CONNECTION_STRING:
        logger.warning("azure.monitor.opentelemetry not installed; tracing will not be enabled.")

    # Authenticate using DefaultAzureCredential (supports Azure CLI, environment, etc.)
    logger.info("Authenticating with Azure...")
    credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)

    # Create the AIProjectClient
    logger.info(f"Connecting to Azure AI Project at: {PROJECT_ENDPOINT}")
    client = AIProjectClient(credential=credential, endpoint=PROJECT_ENDPOINT)

    try:
        # Create the agent
        logger.info(f"Creating agent: {AGENT_NAME}")
        agent = client.agents.create_agent(
            model=AGENT_MODEL,
            name=AGENT_NAME,
            instructions=AGENT_INSTRUCTIONS,
            toolset=None,  # No tools for a smoke test agent
        )
        logger.info(f"Created agent: {agent.id} (name: {agent.name})")
        print(f"Smoke agent created! ID: {agent.id}, Name: {agent.name}")

        # Prepare agent info object (include agent.id)
        agent_info = {
            "AGENT_ID": agent.id,
            "AGENT_NAME": AGENT_NAME,
            "AGENT_MODEL": AGENT_MODEL,
            "AGENT_DESCRIPTION": AGENT_DESCRIPTION,
            "AGENT_INSTRUCTIONS": AGENT_INSTRUCTIONS,
        }

        # Read or create ai_state.json as an array
        if os.path.exists(AI_STATE_PATH):
            try:
                with open(AI_STATE_PATH, encoding="utf-8") as f:
                    state = json.load(f)
                if not isinstance(state, list):
                    logger.warning("ai_state.json is not a list, resetting to empty list.")
                    state = []
            except Exception as e:
                logger.warning(f"Failed to read ai_state.json, resetting: {e}")
                state = []
        else:
            state = []

        # Append new agent info and write back
        state.append(agent_info)
        with open(AI_STATE_PATH, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        logger.info(f"Appended agent info to {AI_STATE_PATH}")
    finally:
        # Clean up resources
        client.close()
        credential.close()
        logger.info("Closed Azure resources.")


if __name__ == "__main__":
    main()
