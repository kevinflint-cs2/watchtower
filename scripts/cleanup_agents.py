# ./scripts/cleanup_agents.py
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError


def main():
    load_dotenv()

    client = AIProjectClient(
        endpoint=os.environ["PROJECT_ENDPOINT"],
        credential=DefaultAzureCredential(),
    )

    with client:
        # 1) Snapshot all agents first to avoid pager invalidation after deletes
        try:
            agents = list(client.agents.list_agents())
        except Exception as e:
            print(f"Failed to list agents: {e}")
            return

        print(f"Found {len(agents)} agent(s).")
        deleted = 0
        skipped = 0

        # 2) Delete by ID; tolerate 404 (already gone) and keep going
        for a in agents:
            agent_id = getattr(a, "id", None)
            agent_name = getattr(a, "name", "<unnamed>")
            if not agent_id:
                skipped += 1
                continue
            try:
                client.agents.delete_agent(agent_id)
                deleted += 1
                print(f"Deleted agent: {agent_name} ({agent_id})")
            except ResourceNotFoundError:
                # race or it was removed elsewhere—treat as success
                print(f"Already gone: {agent_name} ({agent_id})")
            except HttpResponseError as e:
                print(f"Failed to delete {agent_name} ({agent_id}): {e}")

        print(f"\nDone. Deleted {deleted} agent(s). Skipped {skipped}.")


if __name__ == "__main__":
    main()
