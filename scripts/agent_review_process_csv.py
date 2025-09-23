# scripts/create_agent_only.py
import os
from dotenv import load_dotenv, find_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import CodeInterpreterToolDefinition


def main():
    load_dotenv(find_dotenv(), override=False)

    endpoint = os.environ["AIFOUNDRY_PROJECT_ENDPOINT"]
    model_name = os.environ[
        "MODEL_CHATGPT4O_MINI"
    ]  # adjust if you use a different env var
    agent_name = os.environ.get("AGENT_NAME_SUSPECT_PROCS", "wt-agent-procs")

    instructions = (
        "You are a SOC analyst whose job is to analyze the file for any suspicious process activity. "
        "Use the Code Interpreter to parse and evaluate the data; be precise and cite the exact rows "
        "or features that support any findings."
    )

    with AIProjectClient(
        endpoint=endpoint, credential=DefaultAzureCredential()
    ) as project:
        agent = project.agents.create_agent(
            model=model_name,
            name=agent_name,
            instructions=instructions,
            tools=[
                CodeInterpreterToolDefinition()
            ],  # enable Code Interpreter on the agent
        )
        print(f"[OK] Created agent: name={agent.name}  id={agent.id}")


if __name__ == "__main__":
    main()
