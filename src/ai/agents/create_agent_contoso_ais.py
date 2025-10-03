"""
create_agent_contoso_ais.py - Create AI agent with Contoso AIS data search capabilities.

This script creates text files from the embeddings CSV data and creates an AI agent 
with FileSearchTool to query that data effectively.
"""

import os
import json
import csv
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import FileSearchTool, FilePurpose

# Load environment variables
load_dotenv()

# Extract configuration from environment
endpoint = os.environ["AZURE_EXISTING_AIPROJECT_ENDPOINT"].strip('"').strip("'")

# Agent configuration
AGENT_NAME = "contoso-ais-agent"
AGENT_MODEL = "gpt-4o-mini"
AGENT_DESCRIPTION = "AI agent with access to Contoso customer and product information via FileSearch"
AGENT_INSTRUCTIONS = "You are a helpful AI Search Assistant for Contoso Products. Use the file search tool to find and provide information about Contoso products and services. Always use the search tool to find relevant information before responding."

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

def create_text_files_from_embeddings():
    """Convert embeddings CSV to individual text files for FileSearchTool"""
    # Load embeddings from CSV
    embeddings_path = os.path.join(os.path.dirname(__file__), "../../data/contoso_ais/embeddings.csv")
    
    # Create temporary directory for text files
    temp_dir = os.path.join(os.path.dirname(__file__), "temp_contoso_files")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
    
    file_paths = []
    
    try:
        with open(embeddings_path, "r", encoding="utf-8") as f:
            csv_reader = csv.DictReader(f)
            for i, row in enumerate(csv_reader):
                if row.get("token") and row.get("title"):
                    # Create a text file for each row
                    filename = f"contoso_product_{i+1}.txt"
                    file_path = os.path.join(temp_dir, filename)
                    
                    # Write the content to file
                    with open(file_path, "w", encoding="utf-8") as text_file:
                        text_file.write(f"Title: {row['title']}\n\n")
                        text_file.write(f"Content: {row['token']}\n")
                    
                    file_paths.append(file_path)
                    
        print(f"Created {len(file_paths)} text files from embeddings data")
        return file_paths
        
    except Exception as e:
        print(f"Error creating text files: {e}")
        return []

def cleanup_temp_files(file_paths):
    """Clean up temporary text files"""
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Warning: Could not remove {file_path}: {e}")
    
    # Remove temp directory if empty
    temp_dir = os.path.dirname(file_paths[0]) if file_paths else None
    if temp_dir and os.path.exists(temp_dir):
        try:
            os.rmdir(temp_dir)
        except Exception:
            pass  # Directory not empty or other issue

def main():
    """Main execution function"""
    print("Starting Contoso AIS Agent Creation with FileSearch...")
    print()
    
    # Step 1: Create text files from embeddings
    print("Step 1: Creating text files from embeddings data...")
    file_paths = create_text_files_from_embeddings()
    if not file_paths:
        print("Failed to create text files. Exiting.")
        return
    
    try:
        # Step 2: Create client
        print("\nStep 2: Creating AI Project client...")
        credential = DefaultAzureCredential()
        client = AIProjectClient(credential=credential, endpoint=endpoint)
        
        # Step 3: Upload files
        print("\nStep 3: Uploading files to AI Project...")
        file_ids = []
        for file_path in file_paths:
            file = client.agents.files.upload_and_poll(file_path=file_path, purpose=FilePurpose.AGENTS)
            file_ids.append(file.id)
            print(f"Uploaded {os.path.basename(file_path)}: {file.id}")
        
        # Step 4: Create vector store
        print("\nStep 4: Creating vector store...")
        vector_store = client.agents.vector_stores.create_and_poll(
            file_ids=file_ids, 
            name="contoso_ais_vectorstore"
        )
        print(f"Created vector store: {vector_store.id}")
        
        # Step 5: Create file search tool
        print("\nStep 5: Creating FileSearch tool...")
        file_search = FileSearchTool(vector_store_ids=[vector_store.id])
        
        # Step 6: Create agent with file search tool
        print("\nStep 6: Creating AI agent with FileSearch capabilities...")
        agent = client.agents.create_agent(
            model=AGENT_MODEL,
            name=AGENT_NAME,
            instructions=AGENT_INSTRUCTIONS,
            tools=file_search.definitions,
            tool_resources=file_search.resources
        )
        
        print(f"Agent created: {agent.id}")
        
        # Step 7: Save agent state
        print("\nStep 7: Saving agent state...")
        save_agent_to_state(agent.id, AGENT_NAME, AGENT_MODEL, AGENT_DESCRIPTION, AGENT_INSTRUCTIONS)
        
        print("\n✅ Contoso AIS Agent Creation Complete!")
        print(f"Agent ID: {agent.id}")
        print(f"Agent Name: {AGENT_NAME}")
        print(f"Vector Store: {vector_store.id}")
        print(f"Files Processed: {len(file_ids)}")
        
    except Exception as e:
        print(f"Error during agent creation: {e}")
    
    finally:
        # Step 8: Cleanup temporary files
        print("\nStep 8: Cleaning up temporary files...")
        cleanup_temp_files(file_paths)
        print("Cleanup complete.")

if __name__ == "__main__":
    main()