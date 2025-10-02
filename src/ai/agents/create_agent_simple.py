"""
create_agent_simple.py - The simplest possible AI agent creation script.
"""

import os
import json
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient

# Load environment variables
load_dotenv()
endpoint = os.environ["AZURE_EXISTING_AIPROJECT_ENDPOINT"].strip('"').strip("'")

# Agent parameters
AGENT_NAME = "simple-agent"
AGENT_MODEL = "gpt-4o-mini"
AGENT_DESCRIPTION = "A simple AI agent for basic interactions"
AGENT_INSTRUCTIONS = "You are a simple AI agent. Respond briefly and helpfully."

def save_agent_to_state(agent_id, agent_name, agent_model, agent_description, agent_instructions):
    """Save agent info to ai_state.json"""
    ai_state_path = os.path.join(os.path.dirname(__file__), "ai_state.json")
    
    agent_info = {
        "AGENT_ID": agent_id,
        "AGENT_NAME": agent_name,
        "AGENT_MODEL": agent_model,
        "AGENT_DESCRIPTION": agent_description,
        "AGENT_INSTRUCTIONS": agent_instructions
    }
    
    # Read existing state or create new array
    if os.path.exists(ai_state_path):
        with open(ai_state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        if not isinstance(state, list):
            state = []
    else:
        state = []
    
    # Add agent info and save
    state.append(agent_info)
    with open(ai_state_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
    
    print(f"Agent info saved to {ai_state_path}")

# Create client and agent
credential = DefaultAzureCredential()
client = AIProjectClient(credential=credential, endpoint=endpoint)

agent = client.agents.create_agent(
    model=AGENT_MODEL,
    name=AGENT_NAME,
    instructions=AGENT_INSTRUCTIONS
)

print(f"Agent created: {agent.id}")

# Save agent to state file
save_agent_to_state(agent.id, AGENT_NAME, AGENT_MODEL, AGENT_DESCRIPTION, AGENT_INSTRUCTIONS)