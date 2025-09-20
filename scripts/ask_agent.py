# ./scripts/ask_agent.py
import os
import sys
import time
from typing import Iterable, List, Optional, Tuple

from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import ListSortOrder  # for ordering messages

POLL_SECONDS = 1.5


def load_env():
    # Load .env first, then let real env override
    load_dotenv(override=False)


def get_available_agent_names() -> List[str]:
    """
    Collect agent names from env variables AGENT_NAME_*.
    Example: AGENT_NAME_SMOKETEST="wt-smoketest-dev"
    Returns the env values (the actual agent names), sorted.
    """
    names = []
    for k, v in os.environ.items():
        if k.startswith("AGENT_NAME_") and v.strip():
            names.append(v.strip())
    # Legacy single name support
    if os.getenv("AGENT_NAME"):
        names.append(os.environ["AGENT_NAME"].strip())
    return sorted(set(names), key=str.lower)


def prompt_select(prompt: str, options: List[str]) -> str:
    """
    Simple TTY selector. Accepts number or exact/unique prefix match.
    """
    if not options:
        raise SystemExit("No agents found in environment (AGENT_NAME_*).")

    if len(options) == 1:
        print(f"Using only available agent: {options[0]}")
        return options[0]

    print(prompt)
    for i, opt in enumerate(options, 1):
        print(f"  {i}) {opt}")

    while True:
        choice = input("> ").strip()
        # number
        if choice.isdigit():
            idx = int(choice)
            if 1 <= idx <= len(options):
                return options[idx - 1]
        # exact match
        for opt in options:
            if choice == opt:
                return opt
        # unique prefix match
        matches = [o for o in options if o.lower().startswith(choice.lower())]
        if len(matches) == 1:
            return matches[0]
        print("Please enter a number, exact name, or a unique prefix.")


def coerce_cli_args(argv: List[str]) -> Tuple[Optional[str], List[str]]:
    """
    Supports an optional agent override:
      --agent "<agent name>"  (before or after the question)
    Returns (agent_override, remaining_args_as_question_tokens)
    """
    agent = None
    args = []
    skip = False
    for i, token in enumerate(argv):
        if skip:
            skip = False
            continue
        if token == "--agent" and i + 1 < len(argv):
            agent = argv[i + 1]
            skip = True
        else:
            args.append(token)
    return agent, args


def get_agent_id_by_name(project_client: AIProjectClient, name: str) -> Optional[str]:
    """
    Look up an agent by its 'name' via list_agents().
    Returns the id if found, else None.
    """
    try:
        for a in project_client.agents.list_agents():
            if getattr(a, "name", None) == name:
                return a.id
    except Exception as e:
        raise SystemExit(f"Failed to list agents from service: {e}")
    return None


def resolve_agent_id_strict(project_client: AIProjectClient, selected_name: Optional[str]) -> str:
    """
    Strict resolver:
      - If AGENT_ID is set, use it (no service check).
      - Else require selected_name and it must exist on the service.
      - If not found, exit with error. Never create an agent.
    """
    if os.getenv("AGENT_ID"):
        return os.environ["AGENT_ID"]

    if not selected_name:
        raise SystemExit("No agent name selected and AGENT_ID not set. Aborting.")

    agent_id = get_agent_id_by_name(project_client, selected_name)
    if not agent_id:
        # Show what the service *does* have to aid troubleshooting
        try:
            service_names = [getattr(a, "name", "") for a in project_client.agents.list_agents()]
        except Exception:
            service_names = []
        msg = [
            f"Agent named '{selected_name}' not found on the service. Aborting.",
            "Tip: ensure your AGENT_NAME_* value matches the agent's name exactly.",
        ]
        if service_names:
            msg.append("Agents available on the service:")
            for n in sorted(set(filter(None, service_names)), key=str.lower):
                msg.append(f"  - {n}")
        raise SystemExit("\n".join(msg))

    return agent_id


def wait_for_run(project_client: AIProjectClient, thread_id: str, run_id: str):
    """Poll until run reaches a terminal state."""
    while True:
        run = project_client.agents.runs.get(thread_id=thread_id, run_id=run_id)
        status = (run.status or "").lower()
        if status in {"completed", "cancelled", "canceled", "failed", "expired"}:
            return run
        time.sleep(POLL_SECONDS)


def _extract_text_from_part(part) -> Optional[str]:
    """
    Handle varied SDK shapes for message content parts.
    Examples:
      - {'type': 'text', 'text': {'value': '...', 'annotations': []}}
      - {'type': 'text', 'text': '...'}
      - {'text': '...'} or {'text': {'value': '...'}}
      - plain string
    """
    # plain string
    if isinstance(part, str):
        return part

    if isinstance(part, dict):
        if part.get("type") == "text":
            t = part.get("text")
            if isinstance(t, dict):
                if isinstance(t.get("value"), str):
                    return t["value"]
                if isinstance(t.get("content"), str):
                    return t["content"]
            if isinstance(t, str):
                return t
        if "text" in part:
            t = part["text"]
            if isinstance(t, dict) and isinstance(t.get("value"), str):
                return t["value"]
            if isinstance(t, str):
                return t

    return None


def extract_latest_assistant_text(project_client: AIProjectClient, thread_id: str) -> Optional[str]:
    # Prefer ordered & limited listing when available
    try:
        msgs = project_client.agents.messages.list(
            thread_id=thread_id,
            order=ListSortOrder.DESCENDING,
            limit=20,
        )
    except TypeError:
        msgs = project_client.agents.messages.list(thread_id=thread_id)

    for m in msgs:
        if getattr(m, "role", "") == "assistant":
            content = getattr(m, "content", None)
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                texts: List[str] = []
                for part in content:
                    t = _extract_text_from_part(part)
                    if t:
                        texts.append(t.strip())
                if texts:
                    return "\n\n".join(texts)
            if content is not None:
                return str(content)
    return None


def main():
    load_env()

    # Parse optional agent override and question from argv
    agent_override, q_tokens = coerce_cli_args(sys.argv[1:])
    question_arg = " ".join(q_tokens).strip()

    endpoint = os.environ["PROJECT_ENDPOINT"]
    cred = DefaultAzureCredential()
    agents_from_env = get_available_agent_names()

    # Determine agent name (override → prompt)
    if agent_override:
        selected_agent_name = agent_override
        if agents_from_env and selected_agent_name not in agents_from_env:
            print(f"Warning: --agent '{selected_agent_name}' not found in AGENT_NAME_* list.")
    else:
        selected_agent_name = prompt_select("Select an agent to use:", agents_from_env)

    # Determine question (CLI → prompt)
    if not question_arg:
        question_arg = input("Ask your question: ").strip()
        if not question_arg:
            print('No question provided. Example usage:\n  poetry run python ./scripts/ask_agent.py --agent "wt-smoketest-dev" "What is 1+1?"')
            sys.exit(1)

    project_client = AIProjectClient(endpoint=endpoint, credential=cred)

    with project_client:
        # STRICT: never create; fail if not found
        agent_id = resolve_agent_id_strict(project_client, selected_agent_name)

        # 1) Create a thread
        thread = project_client.agents.threads.create()

        # 2) Add the user message
        project_client.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=question_arg,
        )

        # 3) Start a run
        run = project_client.agents.runs.create(
            thread_id=thread.id,
            agent_id=agent_id,
        )

        # 4) Poll until done
        done = wait_for_run(project_client, thread_id=thread.id, run_id=run.id)
        if (done.status or "").lower() != "completed":
            raise SystemExit(f"Run ended with status: {done.status}")

        # 5) Print only the assistant text
        answer = extract_latest_assistant_text(project_client, thread_id=thread.id)
        print("\n=== Answer ===\n")
        print(answer or "[No assistant text found]")


if __name__ == "__main__":
    main()