import os
import pytest
import asyncio
from dotenv import load_dotenv
import asyncio
import time
from azure.identity.aio import DefaultAzureCredential
from azure.ai.projects.aio import AIProjectClient
from azure.core.exceptions import ResourceNotFoundError

# Load root .env before tests
load_dotenv(dotenv_path=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

@pytest.mark.asyncio
async def test_file_agent_best_tent():
    endpoint = os.environ.get('AZURE_EXISTING_AIPROJECT_ENDPOINT')
    assert endpoint, "AZURE_EXISTING_AIPROJECT_ENDPOINT must be set."
    agent_id = os.environ.get('FILE_AGENT_ID')
    assert agent_id, "FILE_AGENT_ID must be set to the file search agent's id."
    prompt = "What's the best tent under $200 for two people, and what features does it include?"
    async with DefaultAzureCredential(exclude_shared_token_cache_credential=True) as creds:
        async with AIProjectClient(credential=creds, endpoint=endpoint) as ai_client:
            agent_client = ai_client.agents
            try:
                # Create a thread for this chat session
                thread = await agent_client.threads.create()

                # Post user message
                message = await agent_client.messages.create(
                    thread_id=thread.id,
                    role="user",
                    content=prompt,
                )

                # Kick off a run for the agent
                run = await agent_client.runs.create(thread_id=thread.id, agent_id=agent_id)

                # Poll the run until it completes or fails (timeout after ~60s)
                for _ in range(60):
                    # short sleep between polls
                    await asyncio.sleep(1)
                    run = await agent_client.runs.get(thread_id=thread.id, run_id=run.id)
                    if run.status not in ["queued", "in_progress", "requires_action"]:
                        break

                assert run.status == "completed", f"Agent run did not complete (status={run.status})"

                # Read messages from the thread and ensure assistant replied
                got_reply = False
                async for msg in agent_client.messages.list(thread_id=thread.id):
                    if msg.text_messages:
                        text = msg.text_messages[0].text.value.strip()
                        if text:
                            # Prefer the assistant's reply (role may be 'assistant')
                            got_reply = True
                            print("Agent response:", text)
                            break

                assert got_reply, "Agent did not return a textual reply."
            except ResourceNotFoundError:
                pytest.fail(f"Agent with id {agent_id} not found.")
