#!/usr/bin/env python3
"""
agents_cleanup.py

Deletes all AI agents in the configured Azure AI Project and removes
src/ai/agents/ai_state.json. Supports a --debug flag to enable verbose
logging (including Azure pipeline headers). Without --debug the script
prints only concise summary lines.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
from pathlib import Path

from azure.ai.projects.aio import AIProjectClient
from azure.core.exceptions import ResourceNotFoundError
from azure.identity.aio import DefaultAzureCredential
from dotenv import load_dotenv

logger = logging.getLogger("agents_cleanup")


async def delete_all_agents(endpoint: str) -> int:
    """Delete all agents in the specified AI Project endpoint.

    Returns the number of agents deleted.
    """
    deleted = 0
    async with DefaultAzureCredential(exclude_shared_token_cache_credential=True) as creds:
        async with AIProjectClient(credential=creds, endpoint=endpoint) as ai_client:
            agent_client = ai_client.agents
            logger.info("Listing all agents...")
            agent_list = agent_client.list_agents()
            async for agent in agent_list:
                try:
                    logger.info(f"Deleting agent: {agent.id} ({agent.name})")
                    await agent_client.delete_agent(agent.id)
                    deleted += 1
                except ResourceNotFoundError:
                    logger.warning(f"Agent {agent.id} already deleted or not found.")
                except Exception as e:
                    logger.error(f"Failed to delete agent {agent.id}: {e}")
    return deleted


def remove_ai_state_file(workspace_root: Path) -> bool:
    """Remove src/ai/agents/ai_state.json relative to workspace_root.

    Returns True if file was deleted, False if it did not exist.
    """
    ai_state_path = workspace_root / "src" / "ai" / "agents" / "ai_state.json"
    try:
        if ai_state_path.exists():
            logger.info(f"Removing ai_state.json at: {ai_state_path}")
            ai_state_path.unlink()
            logger.info(f"Deleted {ai_state_path}.")
            return True
        else:
            logger.info(f"ai_state.json not found at {ai_state_path}, nothing to delete.")
            return False
    except Exception as e:
        logger.error(f"Failed to delete {ai_state_path}: {e}")
        return False


async def _run(endpoint: str) -> tuple[int, bool]:
    deleted = await delete_all_agents(endpoint)
    # compute workspace root relative to this file
    workspace_root = Path(__file__).resolve().parents[3]
    ai_state_deleted = remove_ai_state_file(workspace_root)
    return deleted, ai_state_deleted


def configure_logging(debug: bool) -> None:
    # Default formatter
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    level = logging.DEBUG if debug else logging.WARNING
    logging.basicConfig(level=level, format=fmt)

    # Reduce azure noise unless debugging
    if not debug:
        logging.getLogger("azure").setLevel(logging.WARNING)
        logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
    else:
        # In debug mode, enable detailed azure pipeline logging (headers/body)
        logging.getLogger("azure").setLevel(logging.DEBUG)
        logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.DEBUG)


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete all AI agents in the configured Azure AI Project.")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging and verbose output")
    args = parser.parse_args()

    # Load root .env
    load_dotenv()

    configure_logging(args.debug)

    endpoint = os.environ.get("AZURE_EXISTING_AIPROJECT_ENDPOINT")
    if not endpoint:
        logger.error("AZURE_EXISTING_AIPROJECT_ENDPOINT must be set.")
        return 2

    try:
        deleted, ai_state_deleted = asyncio.run(_run(endpoint))
    except ResourceNotFoundError as e:
        logger.warning(f"Paging complete or all agents deleted: {e}")
        deleted = 0
        # attempt removal of ai_state.json anyway
        workspace_root = Path(__file__).resolve().parents[3]
        ai_state_deleted = remove_ai_state_file(workspace_root)
    except Exception as e:
        logger.exception("Unexpected failure while cleaning agents: %s", e)
        return 1

    # Concise output when not debugging
    if not args.debug:
        print(f"Deleted {deleted} agents.")
        print(f"ai_state.json deleted: {'yes' if ai_state_deleted else 'no'}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
