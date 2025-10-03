ok, we now have an text-embedding model deployed and we have an ai search deployed. 

- I have a file that is previously embedded at ./src/data/contoso_ais/embeddings.csv
- I have code that is in ./src/ai/archive that created an index and created an agent to query that data, please review to understand how that process works
- Now what I need, is to mimic that process but in a single stand alone script, that performs the actions needed to create the index and the agent
- Ensure you use the new environmental variables created, review ./src/.env if needed
- Use and output the variables below to the ./src/ai/agents/ai_state.json file
- Use ./src/ai/agents/create_agent_simple.py as an example, even copy the code if needed
- Do not use async
- Do not enable logging or trace logging
- Python file path ./src/ai/agents/create_agent_contoso_ais.py

AGENT_ID
AGENT_NAME
AGENT_MODEL
AGENT_DESCRIPTION
AGENT_INSTRUCTIONS

Don't write code yet, provide a plan of action that I can approve or adjust as necessary. 

Ask addtional questions if needed. 


Questions:
Index Name: Should I use the AZURE_AI_SEARCH_INDEX_NAME from .env (index_sample) or create a new index specifically for Contoso AIS data (e.g., contoso_ais_index)?

Embeddings Data: The CSV has columns token, embedding, title. Should I assume:

token = the text content to be searchable
embedding = pre-computed embedding vector (as JSON array string)
title = document source/reference
Agent Instructions: What specific instructions should the agent have for querying Contoso data? Should it be generic or specific to the product/customer information domain?

Response to questions
1. Use existing index_sample in AZURE_AI_SEARCH_INDEX_NAME
2. I think your assumptions are correct, if we have problems, we can pull them out of ./src/ai/archive/*.py
3. Instructions are: "You are a helpful AI Search Asssitant for Contoso Products. Use AI Search data only to answer questions"