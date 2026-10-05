"""
02 — A bare MCP client. No Claude, no agent — just proof that the
Host <-> Client <-> Server handshake from the theory session actually works.

Run:
    python 02_mcp_client_test.py

This launches 01_mcp_server.py as a subprocess, connects to it over stdio,
lists the tools it advertises, and calls one of them.
"""

import asyncio

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER_PARAMS = StdioServerParameters(
    command="python",
    args=["01_mcp_server.py"],
)


async def main():
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()  # the MCP handshake

            tools = (await session.list_tools()).tools
            print("Available tools on this server:")
            for t in tools:
                print(f"  - {t.name}: {t.description}")

            result = await session.call_tool(
                "get_weather", arguments={"city": "Indore"}
            )
            print("\nget_weather('Indore') ->", result.content[0].text)


if __name__ == "__main__":
    asyncio.run(main())
