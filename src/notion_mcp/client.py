import os
from contextlib import AsyncExitStack
from typing import List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_core.tools import BaseTool

class NotionMCPManager:
    """Manages the lifecycle of the Notion MCP server and provides LangChain tools."""
    
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def initialize(self) -> List[BaseTool]:
        notion_token = os.getenv("NOTION_TOKEN")
        if not notion_token:
            raise ValueError("NOTION_TOKEN is not set in the environment.")

        # Initialize the Notion MCP server using stdio transport
        server_params = StdioServerParameters(
            command="npx",
            args=["-y", "@notionhq/notion-mcp-server"],
            env={**os.environ, "NOTION_TOKEN": notion_token}
        )

        stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
        self.stdio, self.write = stdio_transport
        
        self.session = await self.exit_stack.enter_async_context(ClientSession(self.stdio, self.write))
        await self.session.initialize()

        # Load tools and convert to LangChain format
        tools = await load_mcp_tools(self.session)
        return tools

    async def cleanup(self):
        await self.exit_stack.aclose()
