# ./scripts/multiagent_with_tracing.py
import os
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ConnectedAgentTool
from azure.identity import DefaultAzureCredential

# <-- Import the bootstrap FIRST so it wires tracing/logging before any SDK calls
from scripts.otel_bootstrap import tracer
# from otel_bootstrap import tracer

load_dotenv()
name_model = os.environ["MODEL_CHATGPT4O_MINI"]
name_agent = os.environ["AGENT_NAME_LOGGER"]
project_endpoint = os.environ["AIFOUNDRY_PROJECT_ENDPOINT"]

with tracer.start_as_current_span(
    "create_project_client",
    attributes={
        "azure.endpoint": project_endpoint,
    },
):
    project_client = AIProjectClient(
        endpoint=project_endpoint,
        credential=DefaultAzureCredential(),
        logging_enable=True,  # extra HTTP logging if you want it
    )

with project_client, tracer.start_as_current_span("multiagent_setup"):
    with tracer.start_as_current_span(
        "create_connected_agent",
        attributes={
            "agent.role": "tool",
            "agent.purpose": "stock_price",
        },
    ):
        stock_price_agent = project_client.agents.create_agent(
            model=name_model,
            name="stock_price_bot_logger",
            instructions="Get the stock price of a company; if realtime unavailable, return last known.",
        )

    connected_agent = ConnectedAgentTool(
        id=stock_price_agent.id,
        name=stock_price_agent.name,
        description="Gets the stock price of a company",
    )

    with tracer.start_as_current_span(
        "create_main_agent",
        attributes={
            "agent.role": "main",
            "agent.name": name_agent,
        },
    ):
        agent = project_client.agents.create_agent(
            model=name_model,
            name=name_agent,
            instructions="You are a helpful agent; use the available tools to get stock prices.",
            tools=connected_agent.definitions,
        )

print(f"Created agent, ID: {agent.id}")
