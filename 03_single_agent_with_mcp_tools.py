"""
03 — A single Claude agent that can use tools from your MCP server.

Why "manual bridging"? Claude's API has a native `mcp_servers` parameter,
but it currently only talks to REMOTE MCP servers reachable over https
(the docs call this the "MCP connector"). Our server runs locally over
stdio — so to use it with the raw Messages API, you bridge it yourself:

  1. Connect to the MCP server, ask it what tools it has (list_tools)
  2. Convert each MCP tool's schema into Anthropic's tool-use schema
  3. Run the standard agent loop:
        send messages -> Claude asks for a tool -> you call it via the
        MCP session -> send the result back -> repeat until Claude
        stops asking for tools and gives a final text answer

This loop is exactly what frameworks like the Claude Agent SDK do for you
automatically (see 05) — here you can see every step.

Install:
    pip install "mcp[cli]" anthropic
Env:
    export ANTHROPIC_API_KEY=your-key

Run:
    python 03_single_agent_with_mcp_tools.py
"""

import asyncio

from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MODEL = "claude-sonnet-5"
SERVER_PARAMS = StdioServerParameters(command="python", args=["01_mcp_server.py"])

client = Anthropic()  # reads ANTHROPIC_API_KEY from the environment


def mcp_tool_to_anthropic_schema(mcp_tool) -> dict:
    """Convert one MCP tool definition into the shape Claude's API expects."""
    return {
        "name": mcp_tool.name,
        "description": mcp_tool.description or "",
        "input_schema": mcp_tool.inputSchema,
    }


async def run_agent(user_prompt: str) -> str:
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            mcp_tools = (await session.list_tools()).tools
            claude_tools = [mcp_tool_to_anthropic_schema(t) for t in mcp_tools]

            messages = [{"role": "user", "content": user_prompt}]

            # ---- the agent loop ----
            while True:
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=1024,
                    tools=claude_tools,
                    messages=messages,
                )
                messages.append({"role": "assistant", "content": response.content})

                if response.stop_reason != "tool_use":
                    # Claude is done reasoning/acting -- return its final text
                    return "".join(
                        block.text
                        for block in response.content
                        if block.type == "text"
                    )

                # Claude wants to call one or more tools before continuing
                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    print(f"[tool call] {block.name}({block.input})")
                    result = await session.call_tool(block.name, arguments=block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": result.content[0].text,
                        }
                    )

                # feed the tool results back in as a user turn, and loop again
                messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    answer = asyncio.run(
        run_agent("What's the weather in Mumbai, and what is 42 + 58?")
    )
    print("\nFinal answer:\n", answer)
