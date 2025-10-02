import os
from types import SimpleNamespace
from pathlib import Path
import importlib.util

import pytest

# Load the ai_chat_tui module directly from its file path so tests don't rely on
# 'src' being a package on sys.path.
MODULE_PATH = Path(__file__).resolve().parents[1] / "src" / "ai" / "chat" / "ai_chat_tui.py"
spec = importlib.util.spec_from_file_location("ai_chat_tui", MODULE_PATH)
tui = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tui)


class DummyCredential:
    def close(self):
        pass


class DummyClient:
    def __init__(self, *args, **kwargs):
        self._messages = []
        self._thread_id = "thread_dummy"
        self._run_id = "run_dummy"
        # expose nested helpers similar to real client under .agents
        self.agents = SimpleNamespace(
            list_agents=self._list_agents,
            get_agent=self.get_agent,
            threads=SimpleNamespace(create=lambda: SimpleNamespace(id=self._thread_id)),
            messages=SimpleNamespace(create=self._create_message, list=self._list_messages),
            runs=SimpleNamespace(create=self._create_run, get=self._get_run),
        )

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def get_agent(self, agent_id):
        return SimpleNamespace(id=agent_id, name="smoke-agent")

    async def _list_agents(self):
        # Return an empty async iterator for list_agents (not needed for this test)
        if False:
            yield

    def _create_message(self, thread_id, role, content):
        self._messages.append({"role": role, "content": content})

    def _create_run(self, thread_id, agent_id):
        # Return an object with id and status
        return SimpleNamespace(id=self._run_id, status="queued")

    def _get_run(self, thread_id, run_id):
        # Immediately return a completed run for the test
        return SimpleNamespace(id=run_id, status="completed", last_error=None)

    def _list_messages(self, thread_id, order=None):
        # Return a fake assistant message with the expected text
        text_obj = SimpleNamespace(text=SimpleNamespace(value="No smoke found"))
        msg = SimpleNamespace(text_messages=[text_obj])
        return [msg]


def test_smoke_agent_reply(monkeypatch, capsys):
    # Ensure chat connects to our dummy project endpoint
    monkeypatch.setenv(tui.PROJECT_ENDPOINT_ENV, "https://example.invalid")

    # Patch AIProjectClient and DefaultAzureCredential used in the module
    monkeypatch.setattr(tui, "AIProjectClient", lambda credential, endpoint: DummyClient())
    monkeypatch.setattr(tui, "DefaultAzureCredential", lambda **kwargs: DummyCredential())

    # Prepare a minimal agent entry with AGENT_ID to skip name lookup
    entry = {
        "AGENT_ID": "agent_smoke",
        "AGENT_NAME": "smoke-agent",
        "AGENT_DESCRIPTION": "A simple smoke test agent",
    }

    # Patch input to send one message ('hello') then '/exit'
    inputs = iter(["hello", "/exit"])
    monkeypatch.setattr("builtins.input", lambda prompt=None: next(inputs))

    # Run chat loop for the single entry
    tui.chat_with_agent(entry)

    # Capture printed output and assert the assistant reply appears
    captured = capsys.readouterr()
    assert "No smoke found" in captured.out
