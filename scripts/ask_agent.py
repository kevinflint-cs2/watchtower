# ./scripts/ask_agent.py
import os
import sys
import time
from typing import Optional

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ListSortOrder  # for ordering messages

POLL_SECONDS = 1.5


def ensure_agent_id(client: AIProjectClient) -> str:
    # Prefer AGENT_ID if set
    if os.getenv("AGENT_ID"):
        return os.environ["AGENT_ID"]

    # Fallback: try to find by name
    name = os.getenv("AGENT_NAME")
    if name:
        try:
            # list() may not exist in older builds; if so, just create
            for a in (
                client.agents.list_agents()
            ):  # may be named slightly differently across betas
                if getattr(a, "name", "") == name:
                    return a.id
        except Exception:
            pass

    # Last resort: create a new one
    model = os.environ["MODEL_DEPLOYMENT_NAME"]
    agent = client.agents.create_agent(
        model=model,
        name=name or "TempAgent",
        instructions="You are a helpful agent for quick Q&A.",
    )
    return agent.id


def wait_for_run(project_client: AIProjectClient, thread_id: str, run_id: str):
    """Poll until run reaches a terminal state."""
    while True:
        run = project_client.agents.runs.get(thread_id=thread_id, run_id=run_id)
        status = (run.status or "").lower()
        if status in {"completed", "cancelled", "canceled", "failed", "expired"}:
            return run
        time.sleep(POLL_SECONDS)


def latest_assistant_text(
    project_client: AIProjectClient, thread_id: str
) -> Optional[str]:
    # Newer SDKs provide order/limit args
    try:
        msgs = project_client.agents.messages.list(
            thread_id=thread_id,
            order=ListSortOrder.DESCENDING,
            limit=10,
        )
    except TypeError:
        # Older builds: fallback without params
        msgs = project_client.agents.messages.list(thread_id=thread_id)

    for m in msgs:
        if getattr(m, "role", "") == "assistant":
            content = getattr(m, "content", None)
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                for part in content:
                    if isinstance(part, dict) and (
                        "text" in part or part.get("type") == "text"
                    ):
                        return part.get("text") or part["text"]
            return str(content) if content is not None else None
    return None


def main():
    load_dotenv()

    question = " ".join(sys.argv[1:]).strip()
    if not question:
        print('Usage: poetry run python ./scripts/ask_agent.py "Your question"')
        sys.exit(1)

    endpoint = os.environ["PROJECT_ENDPOINT"]
    cred = DefaultAzureCredential()

    project_client = AIProjectClient(endpoint=endpoint, credential=cred)

    with project_client:
        agent_id = ensure_agent_id(project_client)

        # 1) Create a thread
        thread = project_client.agents.threads.create()

        # 2) Add the user message
        project_client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=question,
        )

        # 3) Start a run
        run = project_client.agents.runs.create(
            thread_id=thread.id,
            agent_id=agent_id,
        )

        # 4) Poll until done
        done = wait_for_run(project_client, thread_id=thread.id, run_id=run.id)
        if (done.status or "").lower() != "completed":
            raise RuntimeError(f"Run ended with status: {done.status}")

        # 5) Print the latest assistant reply
        answer = latest_assistant_text(project_client, thread_id=thread.id)
        print("\n=== Agent Reply ===\n")
        print(answer or "[No assistant reply found]")


if __name__ == "__main__":
    main()
