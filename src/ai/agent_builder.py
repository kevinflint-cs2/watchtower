"""AgentBuilder: class-based agent creation utilities.

This module exposes an AgentBuilder class that manages credentials and an
AIProjectClient for creating agents (file-search, smoke, etc). It also
keeps module-level convenience wrappers for backward compatibility.
"""

import os
import logging
from typing import List, Dict, Optional

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("agent_builder")


class AgentBuilder:
    def _get_agent_ids(self) -> list:
        """Read AGENT_IDS from .env and return as a list."""
        if not os.path.exists(self.env_path):
            return []
        with open(self.env_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("AGENT_IDS="):
                    ids = line.strip().split("=", 1)[1]
                    return [i for i in ids.split(",") if i]
        return []

    def _set_agent_ids(self, agent_ids: list):
        """Write the AGENT_IDS list to .env as a comma-separated string."""
        value = ",".join(agent_ids)
        self._env_write_key("AGENT_IDS", value, overwrite=True)

    def _add_agent_id(self, agent_id: str):
        ids = self._get_agent_ids()
        if agent_id not in ids:
            ids.append(agent_id)
            self._set_agent_ids(ids)

    def _remove_agent_id(self, agent_id: str):
        ids = self._get_agent_ids()
        if agent_id in ids:
            ids.remove(agent_id)
            self._set_agent_ids(ids)
    """Class that encapsulates Azure AI Project interactions for building agents.

    Usage:
        async with AgentBuilder.from_env() as builder:
            await builder.create_filesearch_agent(...)

    The class manages the DefaultAzureCredential and AIProjectClient lifecycle
    when used as an async context manager.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        base_dir: Optional[str] = None,
        model: Optional[str] = None,
        env_path: Optional[str] = None,
    ):
        self.endpoint = endpoint or os.environ.get("AZURE_EXISTING_AIPROJECT_ENDPOINT")
        self.base_dir = base_dir or os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.model = model or os.environ.get("AZURE_AI_AGENT_DEPLOYMENT_NAME")
        # Resolve root .env (three levels up from this file) as previous code used
        default_env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        self.env_path = env_path or default_env

        # Internal resources initialized in async context
        self._creds = None
        self._client = None

    @classmethod
    async def from_env(cls):
        """Create an AgentBuilder using environment defaults."""
        return cls()

    # Async context manager methods to manage credential & client lifecycle
    async def __aenter__(self):
        from azure.identity.aio import DefaultAzureCredential
        from azure.ai.projects.aio import AIProjectClient

        self._creds = DefaultAzureCredential(exclude_shared_token_cache_credential=True)
        await self._creds.__aenter__()

        self._client = AIProjectClient(credential=self._creds, endpoint=self.endpoint)
        await self._client.__aenter__()
        logger.info("AgentBuilder: connected to AI Project")
        return self

    async def __aexit__(self, exc_type, exc, tb):
        # Close AIProjectClient and credentials
        if self._client:
            await self._client.__aexit__(exc_type, exc, tb)
            self._client = None
        if self._creds:
            await self._creds.__aexit__(exc_type, exc, tb)
            self._creds = None

    # --- Private helpers ---
    def _env_write_key(self, key: str, value: str, overwrite: bool = True) -> bool:
        """Idempotent write to the root .env file. Returns True if written/updated.

        If overwrite is False and key exists, does nothing.
        """
        # Ensure .env exists
        if not os.path.exists(self.env_path):
            # Create containing dir if needed
            try:
                open(self.env_path, "w").close()
            except Exception:
                logger.exception("Failed to create .env file at %s", self.env_path)
                return False

        # Read existing lines
        with open(self.env_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        new_lines: List[str] = []
        found = False
        for ln in lines:
            if ln.strip().startswith(f"{key}="):
                found = True
                if overwrite:
                    new_lines.append(f"{key}={value}\n")
                else:
                    new_lines.append(ln)
            else:
                new_lines.append(ln)

        if not found:
            new_lines.append(f"{key}={value}\n")

        # Write atomically
        tmp_path = self.env_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as tf:
            tf.writelines(new_lines)
        os.replace(tmp_path, self.env_path)
        return True

    async def _upload_files(self, files_dir: str) -> List[str]:
        """Upload all files under files_dir to the project and return file ids."""
        from azure.ai.agents.models import FilePurpose

        file_ids: List[str] = []
        if not files_dir:
            files_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../files"))

        for fname in os.listdir(files_dir):
            fpath = os.path.join(files_dir, fname)
            if os.path.isfile(fpath):
                file = await self._client.agents.files.upload_and_poll(file_path=fpath, purpose=FilePurpose.AGENTS)
                logger.info("Uploaded file %s to Azure AI Project, id=%s", fname, file.id)
                file_ids.append(file.id)
        return file_ids

    async def _create_vector_store(self, file_ids: List[str], name: Optional[str] = None) -> str:
        if not name:
            name = "file_search_store"
        vs = await self._client.agents.vector_stores.create_and_poll(file_ids=file_ids, name=name)
        logger.info("Created vector store: %s", vs.id)
        return vs.id

    # --- Public creation methods ---
    async def create_filesearch_agent(
        self,
        name: str = "agent-file-search",
        files_dir: Optional[str] = None,
        vector_store_name: Optional[str] = None,
        instructions: Optional[str] = None,
        env_key: str = "FILE_AGENT_ID",
        overwrite_env: bool = True,
    ) -> Dict:
        """Create a FileSearch agent: upload files, create vector store, create tool and agent.

        Returns a dict with keys: id, name, vector_store_id, file_ids.
        """
        from azure.ai.agents.models import FileSearchTool, AsyncToolSet

        file_ids = await self._upload_files(files_dir or os.path.join(self.base_dir, "files"))
        vector_store_id = await self._create_vector_store(file_ids, name=vector_store_name)

        tool = FileSearchTool(vector_store_ids=[vector_store_id])
        toolset = AsyncToolSet()
        toolset.add(tool)

        agent = await self._client.agents.create_agent(
            model=self.model,
            name=name,
            instructions=instructions or "You are a helpful product and customer info assistant.",
            toolset=toolset,
        )
        logger.info("Created file search agent: %s (name: %s)", agent.id, agent.name)

        # Update env
        try:
            self._env_write_key(env_key, agent.id, overwrite=overwrite_env)
            self._add_agent_id(agent.id)
        except Exception:
            logger.exception("Failed to write env key %s", env_key)

        return {"id": agent.id, "name": agent.name, "vector_store_id": vector_store_id, "file_ids": file_ids}

    async def create_smoke_agent(
        self,
        name: Optional[str] = None,
        instructions: Optional[str] = None,
        env_key: str = "SMOKE_AGENT_ID",
        overwrite_env: bool = True,
    ) -> Dict:
        """Create a minimal smoke-test agent (no tools).

        Returns dict with id and name.
        """
        from azure.ai.agents.models import AsyncToolSet

        agent_name = name or os.environ.get("AZURE_AI_AGENT_NAME", "agent-smoke")
        toolset = AsyncToolSet()
        agent = await self._client.agents.create_agent(
            model=self.model,
            name=agent_name,
            instructions=instructions or "Smoke test agent.",
            toolset=toolset,
        )
        logger.info("Created smoke agent: %s (name: %s)", agent.id, agent.name)
        try:
            self._env_write_key(env_key, agent.id, overwrite=overwrite_env)
            self._add_agent_id(agent.id)
        except Exception:
            logger.exception("Failed to write env key %s", env_key)
        return {"id": agent.id, "name": agent.name}


# Module-level convenience wrappers for backwards compatibility
def _resolve_builder():
    return AgentBuilder()


async def create_filesearch_agent(**kwargs):
    """Module-level async convenience wrapper that constructs an AgentBuilder and creates a file-search agent."""
    async with _resolve_builder() as builder:
        return await builder.create_filesearch_agent(**kwargs)


async def create_smoke_agent(**kwargs):
    async with _resolve_builder() as builder:
        return await builder.create_smoke_agent(**kwargs)


if __name__ == "__main__":
    # Load root .env
    load_dotenv()
    import asyncio

    async def _main():
        builder = await AgentBuilder.from_env()
        async with builder as b:
            # default behavior: create file search agent
            await b.create_filesearch_agent()
            await b.create_smoke_agent()

    asyncio.run(_main())