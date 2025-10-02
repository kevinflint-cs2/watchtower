"""
create_agent_contoso_fs.py - Simple AI agent with FileSearchTool for Contoso files.
"""

import os
import json
import glob
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import FileSearchTool, FilePurpose

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

# Load environment variables
load_dotenv()
endpoint = os.environ["AZURE_EXISTING_AIPROJECT_ENDPOINT"].strip('"').strip("'")

# Agent parameters
AGENT_NAME = "contoso-fs-agent"
AGENT_MODEL = "gpt-4o-mini"
AGENT_DESCRIPTION = "AI agent using FileSearchTool with access to Contoso customer and product information"
AGENT_INSTRUCTIONS = "You are a helpful assistant with access to Contoso customer and product information. Use the file search tool to answer questions about customers and products."

# Create client
credential = DefaultAzureCredential()
client = AIProjectClient(credential=credential, endpoint=endpoint)

# Get all files in contoso_fs directory
contoso_fs_dir = os.path.join(os.path.dirname(__file__), "../../data/contoso_fs")
file_paths = glob.glob(os.path.join(contoso_fs_dir, "*"))

print(f"Found {len(file_paths)} files to upload")

# Upload files
file_ids = []
for file_path in file_paths:
    if os.path.isfile(file_path):
        file = client.agents.files.upload_and_poll(file_path=file_path, purpose=FilePurpose.AGENTS)
        file_ids.append(file.id)
        print(f"Uploaded {os.path.basename(file_path)}: {file.id}")

# Create vector store with all files
vector_store = client.agents.vector_stores.create_and_poll(file_ids=file_ids, name="contoso_fs_vectorstore")
print(f"Created vector store: {vector_store.id}")

# Create file search tool
file_search = FileSearchTool(vector_store_ids=[vector_store.id])

# Create agent with file search tool
agent = client.agents.create_agent(
    model=AGENT_MODEL,
    name=AGENT_NAME,
    instructions=AGENT_INSTRUCTIONS,
    tools=file_search.definitions,
    tool_resources=file_search.resources
)

print(f"Agent created: {agent.id}")

# Save agent to state file
save_agent_to_state(agent.id, AGENT_NAME, AGENT_MODEL, AGENT_DESCRIPTION, AGENT_INSTRUCTIONS)