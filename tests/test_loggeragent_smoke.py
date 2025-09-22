# tests/test_loggeragent_smoke.py
import pytest
from azure.ai.agents.models import MessageRole

def _msg_text(m):
    # Try content array -> text.value, then top-level .text
    for c in getattr(m, "content", []) or []:
        t = getattr(getattr(c, "text", None), "value", None) or getattr(c, "text", None)
        if isinstance(t, str) and t.strip():
            return t
    t2 = getattr(m, "text", None)
    return t2 if isinstance(t2, str) and t2.strip() else None

@pytest.mark.smoke
def test_loggeragent_exists(project_client, env):
    agents = list(project_client.agents.list_agents())
    names = [a.name for a in agents]
    assert env["agent_multi_logger"] in names, (
        f"Logger-agent '{env['agent_multi_logger']}' not found. Available: {names}"
    )

@pytest.mark.smoke
def test_loggeragent_responds_anything(project_client, env):
    agents = list(project_client.agents.list_agents())
    agent = next((a for a in agents if a.name == env["agent_multi_logger"]), None)
    if agent is None:
        pytest.skip(f"Logger-agent '{env['agent_multi_logger']}' not found via list_agents().")

    # 1) Create thread + user message
    thread = project_client.agents.threads.create()
    project_client.agents.messages.create(
        thread_id=thread.id,
        role=MessageRole.USER,  # known to exist in your SDK
        content="Reply with any short acknowledgement.",
    )

    # 2) Run to completion (SDKs vary on arg name)
    try:
        run = project_client.agents.runs.create_and_process(
            thread_id=thread.id, agent_id=agent.id
        )
    except TypeError:
        run = project_client.agents.runs.create_and_process(
            thread_id=thread.id, assistant_id=agent.id
        )

    assert getattr(run, "status", None) not in {"failed", "cancelled", "expired"}, \
        f"Run failed: {getattr(run, 'last_error', '')}"

    # 3) Get the last non-user reply (role may be 'assistant' or 'agent' depending on SDK)
    msgs = list(project_client.agents.messages.list(thread_id=thread.id))
    assistant_like = [m for m in msgs if str(getattr(m, "role", "")).lower() in {"assistant", "agent"}]
    if not assistant_like:
        assistant_like = [m for m in msgs if getattr(m, "role", None) != MessageRole.USER]

    # Sort by timestamp if present (created_at or created), then take the latest
    assistant_like.sort(key=lambda m: getattr(m, "created_at", getattr(m, "created", 0)))
    assert assistant_like, "No assistant/agent reply found."

    text = _msg_text(assistant_like[-1])
    assert isinstance(text, str) and text.strip(), "Assistant/agent returned empty response."
