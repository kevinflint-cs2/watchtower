import os
from dotenv import load_dotenv
from azure.ai.projects import AIProjectClient
from azure.identity import DefaultAzureCredential


load_dotenv()
name_model = os.environ["MODEL_DEPLOYMENT_NAME"]
name_agent = os.environ["AGENT_NAME"]
project_endpoint = os.environ["PROJECT_ENDPOINT"]


# Create an AIProjectClient instance
project_client = AIProjectClient(
    endpoint=project_endpoint,
    credential=DefaultAzureCredential(),  # Use Azure Default Credential for authentication
)


with project_client:
    # Create an agent with the Code Interpreter tool
    agent = project_client.agents.create_agent(
        model=name_model,  # Model deployment name
        name=name_agent,  # Name of the agent
        instructions="You are a helpful agent for CI smoke tests.",  # Instructions for the agent
    )
    print(f"Created agent, ID: {agent.id}")
