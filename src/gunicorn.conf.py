# Copyright (c) Microsoft. All rights reserved.
# Licensed under the MIT license.
# See LICENSE file in the project root for full license information.
from typing import Dict, List

import asyncio
import csv
import json
import logging
import multiprocessing
import os
import sys

from azure.ai.projects.aio import AIProjectClient
from azure.ai.agents.models import (
    Agent,
    AsyncToolSet,
    AzureAISearchTool,
    FilePurpose,
    FileSearchTool,
    Tool,
)
from azure.ai.projects.models import ConnectionType, ApiKeyCredentials
from azure.identity.aio import DefaultAzureCredential
from azure.core.credentials_async import AsyncTokenCredential

from dotenv import load_dotenv

from logging_config import configure_logging
from ai import agent_manager as agent_manager

load_dotenv()

logger = configure_logging(os.getenv("APP_LOG_FILE", ""))


agentID = os.environ.get("AZURE_EXISTING_AGENT_ID") if os.environ.get(
    "AZURE_EXISTING_AGENT_ID") else os.environ.get(
        "AZURE_AI_AGENT_ID")
    
proj_endpoint = os.environ.get("AZURE_EXISTING_AIPROJECT_ENDPOINT")

def list_files_in_files_directory() -> List[str]:    
    # Get the absolute path of the 'files' directory
    files_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), 'files'))
    
    # List all files in the 'files' directory
    files = [f for f in os.listdir(files_directory) if os.path.isfile(os.path.join(files_directory, f))]
    
    return files

FILES_NAMES = list_files_in_files_directory()


async def create_index_maybe(ai_client: AIProjectClient, creds: AsyncTokenCredential) -> None:
    """Delegate to ai.agent_manager.create_index_maybe.

    Kept for compatibility with callers in this module.
    """
    await agent_manager.create_index_maybe(ai_client, creds, os.path.dirname(__file__))


def _get_file_path(file_name: str) -> str:
    """
    Get absolute file path.

    :param file_name: The file name.
    """
    return os.path.abspath(
        os.path.join(os.path.dirname(__file__),
                     'files',
                     file_name))


async def get_available_tool(
    project_client: AIProjectClient,
    creds: AsyncTokenCredential) -> Tool:
    """
    Get the toolset and tool definition for the agent.

    :param ai_client: The project client to be used to create an index.
    :param creds: The credentials, used for the index.
    :return: The tool set, available based on the environment.
    """
    # File name -> {"id": file_id, "path": file_path}
    file_ids: List[str] = []
    # First try to get an index search.
    conn_id = ""
    if os.environ.get('AZURE_AI_SEARCH_INDEX_NAME'):
        conn_list = project_client.connections.list()
        async for conn in conn_list:
            if conn.type == ConnectionType.AZURE_AI_SEARCH:
                conn_id = conn.id
                break

    # Delegate to the agent_manager implementation which handles both search and file fallback
    return await agent_manager.get_available_tool(project_client, creds, os.path.dirname(__file__))


def on_starting(server):
    """This code runs once before the workers will start."""
    # No agent creation or initialization here. App expects existing agent(s) only.


max_requests = 1000
max_requests_jitter = 50
log_file = "-"
bind = "0.0.0.0:50505"

if not os.getenv("RUNNING_IN_PRODUCTION"):
    reload = True

# Load application code before the worker processes are forked.
# Needed to execute on_starting.
# Please see the documentation on gunicorn
# https://docs.gunicorn.org/en/stable/settings.html
preload_app = True
num_cpus = multiprocessing.cpu_count()
workers = (num_cpus * 2) + 1
worker_class = "uvicorn.workers.UvicornWorker"

timeout = 120
