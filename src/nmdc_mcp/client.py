import asyncio
import json
import logging
import os
import sys
from contextlib import AsyncExitStack

import openai
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from openai import AsyncOpenAI

logging.basicConfig(level=logging.INFO)

# Load environment variables from .env file
load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY")
model = os.getenv("MODEL", "gpt-4o")
BASE_URL = os.getenv("BASE_URL", "https://api.openai.com/v1")
client = openai.OpenAI(api_key=API_KEY, base_url=BASE_URL)


class MCPClient:
    def __init__(self):
        # Initialize session and client objects
        self.session: ClientSession | None = None
        self.exit_stack = AsyncExitStack()
        if API_KEY is None:
            raise Exception("API_KEY must be set in .env file.")
        self.client = AsyncOpenAI(base_url=BASE_URL, api_key=API_KEY)
        self.messages = []
        self.tool_to_session = {}
        self.available_tools = []

    async def connect_to_server(self, server_script_path: str):
        """Connect to an MCP server

        Args:
            server_script_path: Path to the server script (.py or .js)
        """
        logging.info(
            f"Attempting to connect to server with script: {server_script_path}"
        )
        is_python = server_script_path.endswith(".py")
        is_js = server_script_path.endswith(".js")
        if not (is_python or is_js):
            raise ValueError("Server script must be a .py or .js file")

        command = "python" if is_python else "node"
        server_params = StdioServerParameters(
            command=command, args=[server_script_path]
        )

        try:
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            logging.info("Successfully established stdio transport.")
        except Exception as e:
            logging.error(f"Failed to establish stdio transport: {e}")
            raise
        self.stdio, self.write = stdio_transport
        self.session = await self.exit_stack.enter_async_context(
            ClientSession(self.stdio, self.write)
        )

        try:
            await self.session.initialize()
            logging.info("Session initialized successfully.")
        except Exception as e:
            logging.error(f"Failed to initialize session: {e}")
            raise

        # List available tools
        try:
            response = await self.session.list_tools()
            logging.info("Successfully listed tools.")
        except Exception as e:
            logging.error(f"Failed to list tools: {e}")
            raise
        tools = response.tools
        print("\nConnected to server with tools:", [tool.name for tool in tools])
        # list available resources
        try:
            resources = await self.session.list_resources()
            logging.info("Successfully listed resources.")
        except Exception as e:
            logging.error(f"Failed to list resources: {e}")
            raise
        print(
            "\nAvailable resources:",
            [resource.name for resource in resources.resources],
        )

        # Discover and convert tools to OpenAI format
        response = await self.session.list_tools()
        for tool in response.tools:
            self.tool_to_session[tool.name] = self.session
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            self.available_tools.append(openai_tool)

    async def process_query(self, query: str):
        """Process a query using OpenAI with MCP tools."""
        self.messages += [{"role": "user", "content": query}]

        response = await self.client.chat.completions.create(
            model=model, messages=self.messages, tools=self.available_tools
        )

        # Handle tool calls in a loop
        while response.choices[0].message.tool_calls:
            message = response.choices[0].message
            self.messages.append(message)

            # Execute each tool call through MCP
            for tool_call in message.tool_calls:
                session = self.tool_to_session[tool_call.function.name]
                result = await session.call_tool(
                    tool_call.function.name,
                    arguments=json.loads(tool_call.function.arguments),
                )

                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": str(result.content),
                    }
                )

            # Get the final response with tool results
            response = await self.client.chat.completions.create(
                model=model, messages=self.messages, tools=self.available_tools
            )

        return response.choices[0].message.content

    async def chat_loop(self):
        """Run an interactive chat loop"""
        print("\nMCP Client Started!")
        print("Type your queries or 'quit' to exit.")

        while True:
            try:
                query = input("\nQuery: ").strip()

                if query.lower() == "quit":
                    break

                response = await self.process_query(query)
                print("\n" + response)

            except Exception as e:
                print(f"\nError in client: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        await self.exit_stack.aclose()


async def main():
    if len(sys.argv) < 2:
        print("Usage: python client.py <path_to_server_script>")
        sys.exit(1)

    client = MCPClient()
    try:
        await client.connect_to_server(sys.argv[1])
        await client.chat_loop()
    finally:
        await client.cleanup()


if __name__ == "__main__":
    import sys

    asyncio.run(main())
