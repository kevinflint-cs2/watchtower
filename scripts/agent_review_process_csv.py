# scripts/agent_review_process_csv.py
import os, time
from pathlib import Path
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import CodeInterpreterTool, BingGroundingTool, MessageAttachment

PROJECT_ENDPOINT = os.environ["AIFOUNDRY_PROJECT_ENDPOINT"]
MODEL = os.environ.get("MODEL_DEPLOYMENT_NAME")

CSV_PATH = Path(os.environ.get("PROCESS_CSV", "sample_device_process_events.csv")).resolve()
PROMPT_PATH = Path(os.environ.get("HUNT_SHEET_PATH", "./prompts/HuntSheet.md")).resolve()
USE_BING = os.environ.get("USE_BING", "false").lower() == "true"

def read_prompt_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    txt = path.read_text(encoding="utf-8").strip()
    if not txt:
        raise ValueError(f"Prompt file is empty: {path}")
    return txt

def main():
    prompt_text = read_prompt_text(PROMPT_PATH)

    project = AIProjectClient(
        endpoint=PROJECT_ENDPOINT,
        credential=DefaultAzureCredential(),
    )
    with project:
        tools = [CodeInterpreterTool()]
        if USE_BING:
            tools.append(BingGroundingTool())

        agent = project.agents.create_agent(
            model=MODEL,
            name="process-review-agent",
            instructions=("You are a precise SOC analyst. Use the Code Interpreter for file analysis "
                          "and return crisp, verifiable outputs."),
            tools=tools,
        )

        thread = project.agents.create_thread()

        # Attach CSV for Code Interpreter
        attachment = MessageAttachment.from_file(
            filepath=str(CSV_PATH),
            tools=[CodeInterpreterTool()]
        )

        # The entire HuntSheet.md becomes the user message
        project.agents.create_message(
            thread_id=thread.id,
            role="user",
            content=prompt_text,
            attachments=[attachment],
        )

        run = project.agents.create_and_start_run(thread_id=thread.id, agent_id=agent.id)
        while run.status in ("queued", "in_progress"):
            time.sleep(2)
            run = project.agents.get_run(thread_id=thread.id, run_id=run.id)

        # Save the latest assistant response to a markdown file
        msgs = list(project.agents.list_messages(thread_id=thread.id))
        body = "\n\n".join([m.content for m in msgs if m.role == "assistant" and m.content]) or "(no response)"
        Path("agent_process_review.md").write_text(body, encoding="utf-8")
        print("Wrote agent_process_review.md")

if __name__ == "__main__":
    main()
