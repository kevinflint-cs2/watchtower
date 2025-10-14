#!/usr/bin/env python3
"""ai_chat_tui.py

Simple terminal UI to chat with agents listed in src/ai/ai_state.json.

- Reads `ai_state.json` from the same directory. If missing, prints a helpful
  message and exits (graceful failure).
- Displays agent name and description for selection.
- Creates a conversation thread for the chosen agent, allows sending prompts
  and prints agent responses. Loop until user exits or switches agent.

This file intentionally uses the synchronous Azure client APIs already used
elsewhere in the repo for simplicity.
"""

import argparse
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Optional

from azure.ai.agents.models import ListSortOrder
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv


def init_tracing_from_project(project_endpoint: str) -> bool:
    """Try to fetch the Application Insights connection string from the AI Project
    and configure the local process to export telemetry to it.

    Returns True if tracing was configured, False otherwise.
    """
    if not project_endpoint:
        logger.info("No project endpoint available for tracing initialization.")
        return False

    # First, prefer an explicit environment variable if present
    env_conn = os.environ.get("AZURE_APPINSIGHTS_CONNECTION_STRING")
    if env_conn:
        try:
            from azure.monitor.opentelemetry import configure_azure_monitor

            configure_azure_monitor(connection_string=env_conn)
            # Only log this when debug is enabled; keep normal runs quieter.
            logger.debug("Configured Application Insights from AZURE_APPINSIGHTS_CONNECTION_STRING env var.")
            return True
        except Exception as e:
            logger.warning("Failed to configure azure monitor from env var: %s", e)

    credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)
    try:
        # Try sync client first (may not expose get_connection_string on some SDK versions)
        try:
            with AIProjectClient(credential=credential, endpoint=project_endpoint) as project_client:
                conn_str = None
                getter = getattr(project_client.telemetry, "get_connection_string", None)
                if callable(getter):
                    try:
                        conn_str = getter()
                    except Exception as e:
                        logger.info("Sync telemetry.get_connection_string failed: %s", e)
                else:
                    logger.info(
                        "Sync telemetry.get_connection_string not available on this client, will try async fallback."
                    )

                if conn_str:
                    try:
                        from azure.monitor.opentelemetry import configure_azure_monitor

                        configure_azure_monitor(connection_string=conn_str)
                        logger.info("Configured Application Insights for client tracing (sync path).")
                        return True
                    except Exception as e:
                        logger.exception("Failed to configure azure monitor (sync path): %s", e)

        except Exception as e:
            logger.info("Sync AIProjectClient path failed: %s", e)

        # Async fallback: use the aio client to fetch the connection string
        try:
            import asyncio

            from azure.ai.projects.aio import AIProjectClient as AsyncAIProjectClient

            async def _fetch_conn():
                async with AsyncAIProjectClient(credential=credential, endpoint=project_endpoint) as p:
                    try:
                        conn = await p.telemetry.get_connection_string()
                        return conn
                    except Exception as e:
                        logger.info("Async telemetry.get_connection_string failed: %s", e)
                        return None

            conn_str = asyncio.run(_fetch_conn())
            if conn_str:
                try:
                    from azure.monitor.opentelemetry import configure_azure_monitor

                    configure_azure_monitor(connection_string=conn_str)
                    logger.info("Configured Application Insights for client tracing (async path).")
                    return True
                except Exception as e:
                    logger.exception("Failed to configure azure monitor (async path): %s", e)
        except Exception as e:
            logger.info("Async fallback failed: %s", e)

        logger.info("Could not obtain Application Insights connection string from project.")
        return False
    finally:
        try:
            credential.close()
        except Exception:
            pass


logger = logging.getLogger("ai_chat_tui")


def configure_logging(debug: bool) -> None:
    """Configure logging for the TUI. In debug mode enable verbose Azure logs.

    When not debugging, reduce noise from Azure libraries so only important
    messages are shown.
    """
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    level = logging.DEBUG if debug else logging.INFO
    logging.basicConfig(level=level, format=fmt)

    if not debug:
        # Keep our logger informative but silence very verbose azure internals
        logging.getLogger("azure").setLevel(logging.WARNING)
        logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.WARNING)
    else:
        logging.getLogger("azure").setLevel(logging.DEBUG)
        logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.DEBUG)


# The ai_state.json file was moved to src/ai/agents/ai_state.json; resolve it from the workspace
# Resolve workspace root from this file: parents[3] -> workspace root; then src/ai/agents/ai_state.json
AI_STATE_PATH = os.path.abspath(
    os.path.join(Path(__file__).resolve().parents[3], "src", "ai", "agents", "ai_state.json")
)
PROJECT_ENDPOINT_ENV = "AZURE_EXISTING_AIPROJECT_ENDPOINT"


# Load environment variables from the workspace root .env (not the src/ai/.env)
load_dotenv()


def load_state(path: str):
    if not os.path.exists(path):
        print(
            f"State file not found: {path}\n"
            f"Please create agents (e.g. with create_agent_smoke.py) or restore this file."
        )
        return None
    try:
        with open(path, encoding="utf-8") as f:
            state = json.load(f)
        if not isinstance(state, list):
            print("Invalid ai_state.json format: expected a JSON array of agent objects.")
            return None
        return state
    except Exception as e:
        print(f"Failed to read ai_state.json: {e}")
        return None


def choose_agent(state: list) -> Optional[dict]:
    print("Available agents:\n")
    for i, entry in enumerate(state, start=1):
        name = entry.get("AGENT_NAME") or entry.get("AGENT_DISPLAY_NAME") or "assist-agent"
        desc = entry.get("AGENT_DESCRIPTION") or entry.get("AGENT_INSTRUCTIONS") or "You are a helpful assistant."
        print(f"{i}) {name} - {desc}")
    print("\n0) Exit")

    while True:
        choice = input("Select an agent by number: ")
        if not choice.isdigit():
            print("Please enter a number.")
            continue
        idx = int(choice)
        if idx == 0:
            return None
        if 1 <= idx <= len(state):
            return state[idx - 1]
        print("Invalid selection, try again.")


def find_agent_id_by_name(project_client: AIProjectClient, name: str) -> Optional[str]:
    # Iterate through agents and return the first ID that matches the given name
    try:
        agent_list = project_client.agents.list_agents()
        for agent in agent_list:
            if agent.name == name:
                return agent.id
    except Exception as e:
        logger.error("Error listing agents: %s", e)
    return None


def chat_with_agent(entry: dict):
    # Get project endpoint
    project_endpoint = os.environ.get(PROJECT_ENDPOINT_ENV)
    if not project_endpoint:
        print(f"Environment variable {PROJECT_ENDPOINT_ENV} is not set. Unable to connect to AI Project.")
        return

    # Initialize client-side tracing if the project has App Insights configured
    try:
        init_tracing_from_project(project_endpoint)
    except Exception:
        logger.exception("init_tracing_from_project raised an unexpected exception")

    credential = DefaultAzureCredential(exclude_shared_token_cache_credential=True)
    try:
        with AIProjectClient(credential=credential, endpoint=project_endpoint) as project_client:
            # Resolve agent id
            agent_id = entry.get("AGENT_ID")
            if not agent_id:
                agent_name = entry.get("AGENT_NAME")
                if not agent_name:
                    print("Agent entry lacks both AGENT_ID and AGENT_NAME; cannot target agent.")
                    return
                print(f"Looking up agent by name: {agent_name} ...")
                agent_id = find_agent_id_by_name(project_client, agent_name)
                if not agent_id:
                    print(f"Agent with name '{agent_name}' not found in project.")
                    return

            try:
                agent = project_client.agents.get_agent(agent_id)
            except Exception as e:
                print(f"Failed to fetch agent {agent_id}: {e}")
                return

            # Create a new thread for this conversation
            thread = project_client.agents.threads.create()
            print("\n--- Conversation started (type '/exit' to leave, '/switch' to choose another agent) ---\n")

            while True:
                try:
                    user_input = input("You: ")
                except (KeyboardInterrupt, EOFError):
                    print("\nExiting conversation.")
                    break

                if not user_input:
                    continue
                if user_input.strip().lower() in ("/exit", "/quit"):
                    print("Exiting conversation.")
                    break
                if user_input.strip().lower() == "/switch":
                    print("Switching agent.")
                    return

                # Create user message
                try:
                    project_client.agents.messages.create(thread_id=thread.id, role="user", content=user_input)
                except Exception as e:
                    print(f"Failed to create message: {e}")
                    continue

                # Kick off a run and poll for completion
                try:
                    run = project_client.agents.runs.create(thread_id=thread.id, agent_id=agent.id)
                except Exception as e:
                    print(f"Failed to create run for agent: {e}")
                    continue

                # Poll until run completes
                run_status = getattr(run, "status", None)
                poll_count = 0
                while run_status in ("queued", "in_progress", "requires_action"):
                    time.sleep(1)
                    poll_count += 1
                    try:
                        run = project_client.agents.runs.get(thread_id=thread.id, run_id=run.id)
                        run_status = getattr(run, "status", None)
                    except Exception:
                        # If polling fails once, continue trying for a short while
                        if poll_count > 30:
                            print("Run polling failed repeatedly; giving up on this message.")
                            run_status = "failed"
                            break

                if run_status == "failed":
                    last_err = getattr(run, "last_error", None)
                    print(f"Agent run failed: {last_err}")
                    continue

                # Get the latest assistant message
                try:
                    messages = project_client.agents.messages.list(thread_id=thread.id, order=ListSortOrder.DESCENDING)
                    assistant_text = None
                    for msg in messages:
                        # text_messages is an array of text message objects in the SDK
                        if getattr(msg, "text_messages", None):
                            text_msgs = msg.text_messages
                            if len(text_msgs) > 0:
                                assistant_text = text_msgs[0].text.value
                                break
                    if assistant_text:
                        print(f"Agent: {assistant_text}\n")
                    else:
                        print("Agent produced no text response.")
                except Exception as e:
                    print(f"Failed to retrieve messages: {e}")

    finally:
        try:
            credential.close()
        except Exception:
            pass


def main():
    state = load_state(AI_STATE_PATH)
    if state is None:
        # Graceful exit
        sys.exit(0)

    while True:
        entry = choose_agent(state)
        if entry is None:
            print("Goodbye.")
            break
        # Launch chat loop for selected agent
        chat_with_agent(entry)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chat TUI for agents in ai_state.json")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging and verbose Azure output")
    args = parser.parse_args()
    configure_logging(args.debug)
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted by user. Exiting.")
