# PROMPTS

## Prompt: determine best strategy for different envs using bicep and python

Tech Stack:
- GitHub for repository
- azd/bicep for infra
- azd for .env files
- python 3.12 for code, specifically ai agent creation, deletion, and queries
- azure.yaml file kicks off the ai agent creation script
- poetry for dependcies and virtual environment
- poe the poet for tasks
- ruff for lint, formatting
- mypy for type checking
- commitizen for commits

Currently I am using a single env named dev, but I will want to allow for dev, preprod, and prod. My primary method of maintaining my env vars is azd, but I also feed the .env file into python, right now it is hard coded. 

What is the best strategy for multiple environments for both azd and python?

### Result: Over complicated things, simplified things using poe taskers

## Prompt: build env creation python file

Ok, took your advice. 

Now I have the issue of the first fresh run with no .env files. I would like to use python to ask a series of questions to then build the .env file and place in the proper location. 

- I want the python file to exist as ./scripts/set_envs.py
- I want a poe task created called set-envs
- I want the poe task added to each tool.poe.tasks.up-* dev/preprod/prod so that it can create the necessary env
- Python Code Requirements:
- Ask for Input:
    - Ask for environment allow me to choose from selection: dev/preprod/prod, but default to dev this will be AZURE_ENV_NAME
- Based on selection, identify if .env file already exists, if so end, else continue
- Ask for input: 
    - Ask for string input for name prefix, this will be envar NAME_PREFIX
    - Ask for location, string input, but default to eastus2, this will be the envar AZURE_LOCATION
    - Ask for subscription id, this will be envar AZURE_SUBSCRIPTION_ID
    - Ask for azure storage account sku, provide a selection of all valid types to choose from but default to STANDARD_LRS, envar is STORAGE_SKU
    = Ask for model type, but default to gpt-4o-mini, make note that it only supports this for now
- We now have what we need to build the other envars as they follow a strict format of [NAME_PREFIX]-[SHORTHAND_SERVICEID]-[AZURE_ENV_NAME], example for AIFOUNDRY_ACCOUNT is "wt-aifa-dev"
- Build these environmental vars
    - AGENT_NAME = [NAME_PREFIX]-smoketest-[AZURE_ENV_NAME]
    - AIFOUNDRY_ACCOUNT = [NAME_PREFIX]-aifa-[AZURE_ENV_NAME]
    - AIFOUDNRY_PROJECT = [NAME_PREFIX]-aifp-[AZURE_ENV_NAME]
    - PROJECT_ENDPOINT="https://[AIFOUDNRY_PROJECT].services.ai.azure.com/api/projects/[AIFOUDNRY_PROJECT]"
- Based on AZURE_ENV_NAME, use azd to set the envinrment
    - Example: if AZURE_ENV_NAME = dev, then run "azd set env dev"
- Based on AZURE_ENV_NAME, write all the gather envars to a .env file. 
    - Example: if AZURE_ENV_NAME = dev, then write to .azure/dev/.env
- At this point, Azure Developer CLI environment has been set, and the .env has then neccesary envars to run bicep and python files. 

Here is an example of a working .env file
[REDACTED]

Review my steps, and identify any missed steps, if needed ask for input as needed for missed steps or additonal functionality. Once done, provide the python code.  

### Result: Actually created a decent env file, later I added code to update root .env so I could reduce my poe tasks from 3 to 1

## Prompt: create readme.md

Write a proper readme.md using the information below as you see fit. 

What is this?
Simple automated setup of Azure AI Foundry to use a single AI Agent. Good Azure Agentic AI starter kit.

Tech Stack:
- GitHub for repository
- azd/bicep for infra
- azd for environment 
- python 3.12 for code, specifically ai agent creation, deletion, and queries
- azure.yaml file kicks off the ai agent creation script
- poetry for dependcies and virtual environment
- poe the poet for tasks
- ruff for lint, formatting
- mypy for type checking
- commitizen for commits
- detect-secrets to detect exposed secrets
- pre-commits to block commits with secrets

General setup
- Run "poetry run poe up", follow prompts, it does the rest to build Azure AI Foundry infra and an AI Agent, even runs a post creation test
- Run "poetry run python ./scripts/ask_question.py 'what is 1+1, answer only'"
- Run "poetry run poe down" to tear everything down

Make this a proper well documented repository using the readme.md you build. Output so that I can paste in my readme. 