import os
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ConnectedAgentTool, MessageRole
from azure.identity import DefaultAzureCredential

load_dotenv()
name_model = os.environ["MODEL_DEPLOYMENT_NAME"]
name_agent = os.environ["AGENT_NAME_MULTIAGENT"]
project_endpoint = os.environ["PROJECT_ENDPOINT"]


# Create an AIProjectClient instance
project_client = AIProjectClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential(),  # Use Azure Default Credential for authentication
)

# Create an agent that will be connected to a "main" agent.
stock_price_agent = project_client.agents.create_agent(
    model=name_model,
    name="stock_price_bot",
    instructions="Your job is to get the stock price of a company. If you don't know the realtime stock price, return the last known stock price.",
    #tools=... # tools to help the agent get stock prices
)

# Initialize the connected agent tool with the agent ID, name, and description
connected_agent = ConnectedAgentTool(
    id=stock_price_agent.id, name=stock_price_agent.name, description="Gets the stock price of a company"
)

# Create the "main" agent that will use the connected agent.
agent = project_client.agents.create_agent(
    model=name_model,
    name=name_agent,
    instructions="You are a helpful agent, and use the available tools to get stock prices.",
    tools=connected_agent.definitions,
)

print(f"Created agent, ID: {agent.id}")