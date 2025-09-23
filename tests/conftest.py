import os
import pytest
from dotenv import load_dotenv, find_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


@pytest.fixture(scope="session")
def env():
    # Load .env from repo root (or nearest up the tree)
    load_dotenv(find_dotenv(), override=False)

    endpoint = os.getenv("AIFOUNDRY_PROJECT_ENDPOINT")
    agent_name = os.getenv("AGENT_NAME_SMOKETEST")
    agent_multi_name = os.getenv("AGENT_NAME_MULTIAGENT")
    agent_multi_logger = os.getenv("AGENT_NAME_LOGGER")
    model_name = os.getenv("MODEL_CHATGPT4O_MINI")  # optional for assertions/logging

    if not endpoint:
        pytest.skip("AIFOUNDRY_PROJECT_ENDPOINT is not set in environment/.env")
    if not agent_name:
        pytest.skip("AGENT_NAME_SMOKETEST is not set in environment/.env")
    if not model_name:
        pytest.skip("MODEL_CHATGPT4O_MINI is not set in environment/.env")
    if not agent_multi_name:
        pytest.skip("AGENT_NAME_MULTIAGENT is not set in environment/.env")
    if not agent_multi_logger:
        pytest.skip("AGENT_NAME_LOGGER is not set in environment/.env")

    return {
        "endpoint": endpoint,
        "agent_name": agent_name,
        "agent_multi_name": agent_multi_name,
        "agent_multi_logger": agent_multi_logger,
        "model_name": model_name,
    }


@pytest.fixture(scope="session")
def project_client(env):
    client = AIProjectClient(
        endpoint=env["endpoint"],
        credential=DefaultAzureCredential(),
    )
    yield client
    # AIProjectClient supports context management; close explicitly in tests
    try:
        client.close()
    except Exception:
        pass
