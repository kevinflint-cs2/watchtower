#!/usr/bin/env python3
# scripts/chat_with_agent_file.py
import os
import sys
import time
import argparse
from dotenv import load_dotenv, find_dotenv
import random
import re
from azure.core.exceptions import HttpResponseError
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.agents.models import (
    CodeInterpreterTool,
    MessageAttachment,
)


# --- add this helper above main() ---
def run_with_retry(project, thread_id, agent_id, max_attempts=5, base_wait=15):
    """
    Tries to run the agent and handles rate limits with exponential backoff + jitter.
    Returns the final run object (completed or last failure).
    """
    attempt = 1
    wait = base_wait

    while True:
        try:
            # Preferred path
            run = project.agents.runs.create_and_process(
                thread_id=thread_id, agent_id=agent_id
            )
        except HttpResponseError as e:
            # Immediate 429 during call
            msg = str(e)
            if (
                "rate" in msg.lower()
                and "limit" in msg.lower()
                and attempt < max_attempts
            ):
                sleep_for = wait + random.uniform(0, wait / 2)
                time.sleep(sleep_for)
                attempt += 1
                wait *= 2
                continue
            raise

        status = getattr(run, "status", "")
        if status in {"failed", "cancelled", "expired"}:
            err = getattr(run, "last_error", None)
            # err may be dict-like: {'code': 'rate_limit_exceeded', 'message': '... 60 seconds ...'}
            code = None
            message = ""
            if isinstance(err, dict):
                code = err.get("code")
                message = err.get("message") or ""
            else:
                code = getattr(err, "code", None)
                message = getattr(err, "message", "") or ""

            if (code == "rate_limit_exceeded") and attempt < max_attempts:
                # Respect server hint if present
                m = re.search(r"(\d+)\s*seconds?", message)
                hint = int(m.group(1)) if m else None
                sleep_for = hint or (wait + random.uniform(0, wait / 2))
                time.sleep(sleep_for)
                attempt += 1
                wait *= 2
                continue

        return run


def extract_text_from_message(msg):
    # Tries several common shapes for agent message payloads
    content = getattr(msg, "content", None)
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        for part in content:
            txt = None
            if hasattr(part, "get"):
                t = part.get("text")
                if isinstance(t, dict):
                    txt = t.get("value") or t.get("content")
                elif isinstance(t, str):
                    txt = t
                if not txt and isinstance(part.get("content"), str):
                    txt = part.get("content")
            elif isinstance(part, str):
                txt = part
            if isinstance(txt, str) and txt.strip():
                return txt
    for attr in ("text", "value"):
        v = getattr(msg, attr, None)
        if isinstance(v, str) and v.strip():
            return v
    return None


def main():
    load_dotenv(find_dotenv(), override=False)

    p = argparse.ArgumentParser(
        description="Upload a file, attach it to a thread, and ask an agent a question."
    )
    p.add_argument(
        "--endpoint",
        default=os.environ.get("AIFOUNDRY_PROJECT_ENDPOINT"),
        help="Project endpoint.",
    )
    p.add_argument(
        "--agent-name",
        default=os.environ.get("AGENT_NAME_SUSPECT_PROCS")
        or os.environ.get("AGENT_NAME_SMOKETEST"),
        help="Agent name to use.",
    )
    p.add_argument(
        "--file",
        required=True,
        help="Path to the file to upload (e.g., your Process Events CSV).",
    )
    p.add_argument(
        "--prompt", help="Question for the agent. If omitted, you will be prompted."
    )
    p.add_argument("--timeout-sec", type=int, default=180)
    args = p.parse_args()

    if not args.endpoint:
        sys.exit("Missing --endpoint or AIFOUNDRY_PROJECT_ENDPOINT.")
    if not args.agent_name:
        sys.exit(
            "Missing --agent-name (AGENT_NAME_SUSPECT_PROCS / AGENT_NAME_SMOKETEST)."
        )
    if not os.path.exists(args.file):
        sys.exit(f"File not found: {args.file}")

    prompt = args.prompt or input("Enter your question for the agent: ").strip()
    if not prompt:
        sys.exit("Empty prompt; nothing to do.")

    cred = DefaultAzureCredential()
    with AIProjectClient(endpoint=args.endpoint, credential=cred) as project:
        # 1) Upload the file and capture file_id
        #    Some SDK versions use an enum; others accept the string "assistants".
        try:
            from azure.ai.agents.models import FilePurpose  # newer SDKs

            uploaded = project.agents.files.upload_and_poll(
                file_path=args.file, purpose=FilePurpose.AGENTS
            )
        except Exception:
            uploaded = project.agents.files.upload_and_poll(
                file_path=args.file, purpose="assistants"
            )

        file_id = getattr(uploaded, "id", None)
        fname = getattr(uploaded, "filename", None) or getattr(uploaded, "name", None)
        print(
            f"[OK] Uploaded file: name={fname} id={file_id} bytes={getattr(uploaded, 'bytes', None)}"
        )
        if not file_id:
            sys.exit("Upload succeeded but no file id was returned.")

        # 2) Resolve agent by name
        agents = list(project.agents.list_agents())
        agent = next(
            (
                a
                for a in agents
                if str(a.name).strip().lower() == args.agent_name.strip().lower()
            ),
            None,
        )
        if not agent:
            names = ", ".join(a.name for a in agents)
            sys.exit(f"Agent '{args.agent_name}' not found. Available: {names}")

        # 3) Create a thread, attach the newly uploaded file for Code Interpreter, send the prompt
        thread = project.agents.threads.create()

        attachment = MessageAttachment(
            file_id=file_id,
            tools=CodeInterpreterTool().definitions,  # allow Code Interpreter to access the attachment
        )

        project.agents.messages.create(
            thread_id=thread.id,
            role="user",
            content=prompt,
            attachments=[attachment],
        )

        # 4) Run to completion
        # start = time.time()
        # try:
        #     run = project.agents.runs.create_and_process(thread_id=thread.id, agent_id=agent.id)
        # except AttributeError:
        #     # Fallback for older SDKs
        #     run = project.agents.create_and_start_run(thread_id=thread.id, agent_id=agent.id)
        #     while getattr(run, "status", "") in {"queued", "in_progress"} and (time.time() - start) < args.timeout_sec:
        #         time.sleep(2)
        #         run = project.agents.get_run(thread_id=thread.id, run_id=run.id)

        # status = getattr(run, "status", "")
        # if status in {"failed", "cancelled", "expired"}:
        #     err = getattr(run, "last_error", "") or ""
        #     sys.exit(f"Run ended with status={status}. {err}")
        # if status not in {"completed", "succeeded"}:
        #     sys.exit(f"Run did not complete (status={status}).")

        # --- replace your run section in main() with this ---
        # start = time.time()
        try:
            run = run_with_retry(
                project, thread.id, agent.id, max_attempts=5, base_wait=20
            )
        except Exception as e:
            sys.exit(f"Run error: {e}")

        status = getattr(run, "status", "")
        if status in {"failed", "cancelled", "expired"}:
            err = getattr(run, "last_error", "") or ""
            sys.exit(f"Run ended with status={status}. {err}")

        # 5) Print the latest agent reply
        msgs = list(project.agents.messages.list(thread_id=thread.id))
        replies = [
            m
            for m in msgs
            if str(getattr(m, "role", "")).lower() in {"assistant", "agent"}
        ]
        text = extract_text_from_message(replies[-1]) if replies else None

        print("\n--- Agent Reply ---")
        print(text or "(no text found)")

        print("\nIDs:")
        print(f"  agent_id:  {agent.id}")
        print(f"  thread_id: {thread.id}")
        print(f"  file_id:   {file_id}")


if __name__ == "__main__":
    main()
