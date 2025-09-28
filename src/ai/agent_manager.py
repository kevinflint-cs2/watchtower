"""Agent and index creation helpers moved under src.ai for modularity.

This module contains functions previously living in `src/gunicorn.conf.py`.
"""
from typing import List
import asyncio
import os
import logging

from azure.ai.projects.aio import AIProjectClient
from azure.ai.projects.models import ConnectionType, ApiKeyCredentials
from azure.identity.aio import DefaultAzureCredential
from azure.core.credentials_async import AsyncTokenCredential

from .search_index_manager import SearchIndexManager

logger = logging.getLogger(__name__)

from contextlib import asynccontextmanager
from azure.ai.projects.aio import AIProjectClient
from azure.identity.aio import DefaultAzureCredential


@asynccontextmanager
async def get_project_and_agent(proj_endpoint: str, enable_trace: bool = False):
    """Async context manager that yields (ai_project, agent).

    This centralizes the agent lookup/creation logic so callers don't need to
    duplicate it. The AIProjectClient is created and closed inside this
    context manager.

    :param proj_endpoint: Project endpoint to connect to.
    :param enable_trace: Whether to fetch App Insights connection string and configure tracing.
    """
    agent = None
    ai_project = None
    try:
        async with DefaultAzureCredential(exclude_shared_token_cache_credential=True) as creds:
            async with AIProjectClient(
                credential=creds,
                endpoint=proj_endpoint,
                api_version = "2025-05-15-preview"
            ) as ai_project:
                logger.info("Created AIProjectClient")

                if enable_trace:
                    application_insights_connection_string = ""
                    try:
                        application_insights_connection_string = await ai_project.telemetry.get_connection_string()
                    except Exception as e:
                        e_string = str(e)
                        logger.error("Failed to get Application Insights connection string, error: %s", e_string)
                    if not application_insights_connection_string:
                        logger.error("Application Insights was not enabled for this project.")
                        logger.error("Enable it via the 'Tracing' tab in your AI Foundry project page.")
                        raise RuntimeError("Application Insights not enabled for project")
                    else:
                        try:
                            from azure.monitor.opentelemetry import configure_azure_monitor
                            configure_azure_monitor(connection_string=application_insights_connection_string)
                            logger.info("Configured Application Insights for tracing.")
                        except Exception:
                            logger.exception("Failed to configure azure monitor opentelemetry")

                agent_id = os.environ.get("AZURE_EXISTING_AGENT_ID")
                if agent_id:
                    try:
                        agent = await ai_project.agents.get_agent(agent_id)
                        logger.info("Agent already exists, skipping creation")
                        logger.info(f"Fetched agent, agent ID: {agent.id}")
                        logger.info(f"Fetched agent, model name: {agent.model}")
                    except Exception as e:
                        logger.error(f"Error fetching agent: {e}", exc_info=True)

                if not agent:
                    # Fallback to searching by name
                    agent_name = os.environ.get("AZURE_AI_AGENT_NAME")
                    if agent_name:
                        agent_list = ai_project.agents.list_agents()
                        if agent_list:
                            async for agent_object in agent_list:
                                if agent_object.name == agent_name:
                                    agent = agent_object
                                    logger.info(f"Found agent by name '{agent_name}', ID={agent_object.id}")
                                    break

                if not agent:
                    raise RuntimeError("No agent found. Ensure an agent exists or AZURE_EXISTING_AGENT_ID is set.")

                yield ai_project, agent
    except Exception:
        raise


@asynccontextmanager
async def get_project_and_agent_with_app(app, proj_endpoint: str, enable_trace: bool = False):
    """Like get_project_and_agent, but also configures tracing into the FastAPI `app` state.

    This avoids having `main` duplicate tracing setup logic and guarantees the
    application object receives the Application Insights connection string.
    """
    # Use the non-tracing version of the underlying helper to avoid double configuration
    async with get_project_and_agent(proj_endpoint, enable_trace=False) as (ai_project, agent):
        if enable_trace:
            try:
                application_insights_connection_string = ""
                try:
                    application_insights_connection_string = await ai_project.telemetry.get_connection_string()
                except Exception as e:
                    logger.error("Failed to get Application Insights connection string, error: %s", str(e))
                if not application_insights_connection_string:
                    logger.error("Application Insights was not enabled for this project.")
                else:
                    try:
                        from azure.monitor.opentelemetry import configure_azure_monitor
                        configure_azure_monitor(connection_string=application_insights_connection_string)
                        app.state.application_insights_connection_string = application_insights_connection_string
                        logger.info("Configured Application Insights for tracing and attached to app.state.")
                    except Exception:
                        logger.exception("Failed to configure azure monitor opentelemetry")
            except Exception:
                logger.exception("Unexpected error while configuring tracing")

        yield ai_project, agent



def _get_file_path(base_dir: str, file_name: str) -> str:
    return os.path.abspath(os.path.join(base_dir, 'files', file_name))


def list_files_in_files_directory(base_dir: str) -> List[str]:
    files_directory = os.path.abspath(os.path.join(base_dir, 'files'))
    files = [f for f in os.listdir(files_directory) if os.path.isfile(os.path.join(files_directory, f))]
    return files


async def create_index_maybe(
        ai_client: AIProjectClient, creds: AsyncTokenCredential, base_dir: str) -> None:
    """Create the index and upload documents if the index does not exist.

    :param ai_client: The project client to be used to create an index.
    :param creds: The credentials, used for the index.
    :param base_dir: The directory root to locate data files.
    """
    endpoint = os.environ.get('AZURE_AI_SEARCH_ENDPOINT')
    embedding = os.getenv('AZURE_AI_EMBED_DEPLOYMENT_NAME')    
    if endpoint and embedding:
        try:
            aoai_connection = await ai_client.connections.get_default(
                connection_type=ConnectionType.AZURE_OPEN_AI, include_credentials=True)
        except ValueError as e:
            logger.error("Error creating index: {e}")
            return
        
        embed_api_key = None
        if aoai_connection.credentials and isinstance(aoai_connection.credentials, ApiKeyCredentials):
            embed_api_key = aoai_connection.credentials.api_key

        search_mgr = SearchIndexManager(
            endpoint=endpoint,
            credential=creds,
            index_name=os.getenv('AZURE_AI_SEARCH_INDEX_NAME'),
            dimensions=None,
            model=embedding,
            deployment_name=embedding,
            embedding_endpoint=aoai_connection.target,
            embed_api_key=embed_api_key
        )
        # If another application instance already have created the index,
        # do not upload the documents.
        if await search_mgr.create_index(
            vector_index_dimensions=int(
                os.getenv('AZURE_AI_EMBED_DIMENSIONS'))):
            embeddings_path = os.path.join(
                base_dir, 'data', 'embeddings.csv')

            assert embeddings_path, f'File {embeddings_path} not found.'
            await search_mgr.upload_documents(embeddings_path)
            await search_mgr.close()


async def get_available_tool(
        project_client: AIProjectClient,
        creds: AsyncTokenCredential,
        base_dir: str):
    """Get the toolset and tool definition for the agent.

    Returns an AzureAISearchTool when a search connection exists, otherwise falls back
    to creating a FileSearchTool using files under the `files` directory.
    """
    from azure.ai.agents.models import (
        AsyncToolSet,
        AzureAISearchTool,
        FilePurpose,
        FileSearchTool,
    )

    # File name -> {id, path}
    file_ids: List[str] = []
    conn_id = ""
    if os.environ.get('AZURE_AI_SEARCH_INDEX_NAME'):
        conn_list = project_client.connections.list()
        async for conn in conn_list:
            if conn.type == ConnectionType.AZURE_AI_SEARCH:
                conn_id = conn.id
                break

    toolset = AsyncToolSet()
    if conn_id:
        await create_index_maybe(project_client, creds, base_dir)

        return AzureAISearchTool(
            index_connection_id=conn_id,
            index_name=os.environ.get('AZURE_AI_SEARCH_INDEX_NAME'))
    else:
        logger.info("agent: index was not initialized, falling back to file search.")
        base = base_dir
        files = list_files_in_files_directory(base)
        for file_name in files:
            file_path = _get_file_path(base, file_name)
            file = await project_client.agents.files.upload_and_poll(
                file_path=file_path, purpose=FilePurpose.AGENTS)
            file_ids.append(file.id)

        vector_store = await project_client.agents.vector_stores.create_and_poll(
            file_ids=file_ids,
            name="sample_store"
        )
        logger.info("agent: file store and vector store success")

        return FileSearchTool(vector_store_ids=[vector_store.id])


async def create_agent(ai_client: AIProjectClient,
                       creds: AsyncTokenCredential, base_dir: str):
    logger.info("Creating new agent with resources")
    tool = await get_available_tool(ai_client, creds, base_dir)
    from azure.ai.agents.models import AsyncToolSet
    toolset = AsyncToolSet()
    toolset.add(tool)
    
    from azure.ai.agents.models import AzureAISearchTool
    instructions = "Use AI Search always. Avoid to use base knowledge." if isinstance(tool, AzureAISearchTool) else "Use File Search always.  Avoid to use base knowledge."
    
    agent = await ai_client.agents.create_agent(
        model=os.environ["AZURE_AI_AGENT_DEPLOYMENT_NAME"],
        name=os.environ["AZURE_AI_AGENT_NAME"],
        instructions=instructions,
        toolset=toolset
    )
    return agent


async def initialize_resources(base_dir: str):
    try:
        async with DefaultAzureCredential(
                exclude_shared_token_cache_credential=True) as creds:
            async with AIProjectClient(
                credential=creds,
                endpoint=os.environ.get('AZURE_EXISTING_AIPROJECT_ENDPOINT')
            ) as ai_client:
                agentID = os.environ.get("AZURE_EXISTING_AGENT_ID") if os.environ.get(
                    "AZURE_EXISTING_AGENT_ID") else os.environ.get(
                        "AZURE_AI_AGENT_ID")

                # If the environment already has AZURE_AI_AGENT_ID or AZURE_EXISTING_AGENT_ID, try
                # fetching that agent
                if agentID is not None:
                    try:
                        agent = await ai_client.agents.get_agent(agentID)
                        logger.info(f"Found agent by ID: {agent.id}")
                        return
                    except Exception as e:
                        logger.warning(
                            "Could not retrieve agent by AZURE_EXISTING_AGENT_ID = "
                            f"{agentID}, error: {e}")

                # Check if an agent with the same name already exists
                agent_list = ai_client.agents.list_agents()
                if agent_list:
                    async for agent_object in agent_list:
                        if agent_object.name == os.environ[
                                "AZURE_AI_AGENT_NAME"]:
                            logger.info(
                                "Found existing agent named "
                                f"'{agent_object.name}'"
                                f", ID: {agent_object.id}")
                            os.environ["AZURE_EXISTING_AGENT_ID"] = agent_object.id
                            return
                        
                # Create a new agent
                agent = await create_agent(ai_client, creds, base_dir)
                os.environ["AZURE_EXISTING_AGENT_ID"] = agent.id
                logger.info(f"Created agent, agent ID: {agent.id}")

    except Exception as e:
        logger.info("Error creating agent: {e}", exc_info=True)
        raise RuntimeError(f"Failed to create the agent: {e}")
