import os
import pytest
from dotenv import load_dotenv, find_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient


@pytest.fixture(scope="session")
def env():
    # Load .env from repo root (or nearest up the tree)
    load_dotenv(find_dotenv(), override=False)

    endpoint = os.getenv("PROJECT_ENDPOINT")
    agent_name = os.getenv("AGENT_NAME")
    model_name = os.getenv("MODEL_DEPLOYMENT_NAME")  # optional for assertions/logging

    if not endpoint:
        pytest.skip("PROJECT_ENDPOINT is not set in environment/.env")
    if not agent_name:
        pytest.skip("AGENT_NAME is not set in environment/.env")

    return {
        "endpoint": endpoint,
        "agent_name": agent_name,
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
