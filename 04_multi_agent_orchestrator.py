"""
04 — Multi-step agent orchestration: an orchestrator-workers pattern,
built from raw API calls so every step is visible.

Shape:
    Orchestrator agent (plans, has ONE meta-tool: dispatch_to_worker)
        -> delegates subtask -> "research" worker (its own MCP tool slice)
        -> delegates subtask -> "math" worker (its own MCP tool slice)
    Orchestrator collects both results and writes the final combined answer.

This is the same orchestrator-workers shape used in production multi-agent
systems (and the one the Claude Agent SDK's subagent feature automates —
see 05). Building it by hand once makes the SDK version make sense.

Install:
    pip install "mcp[cli]" anthropic
Env:
    export ANTHROPIC_API_KEY=your-key

Run:
    python 04_multi_agent_orchestrator.py
"""

import asyncio

from anthropic import Anthropic
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MODEL = "claude-sonnet-5"
SERVER_PARAMS = StdioServerParameters(command="python", args=["01_mcp_server.py"])
client = Anthropic()

# Which MCP tools each specialist worker is allowed to see and use.
# (In a bigger system each worker would usually talk to its own MCP
# server entirely; here they share one server and we just filter tools.)
WORKER_TOOLS = {
    "research": ["get_weather", "search_notes"],
    "math": ["add_numbers"],
}
WORKER_SYSTEM_PROMPTS = {
    "research": "You are a research specialist. Use your tools to look up facts. Be concise.",
    "math": "You are a calculation specialist. Use your tools to compute exact numbers. Be concise.",
}


def to_anthropic_schema(mcp_tool) -> dict:
    return {
        "name": mcp_tool.name,
        "description": mcp_tool.description or "",
        "input_schema": mcp_tool.inputSchema,
    }


async def run_worker(session: ClientSession, worker_name: str, subtask: str) -> str:
    """Run one specialist agent, restricted to its own tool slice, to completion."""
    all_tools = (await session.list_tools()).tools
    allowed = WORKER_TOOLS[worker_name]
    tools = [to_anthropic_schema(t) for t in all_tools if t.name in allowed]

    messages = [{"role": "user", "content": subtask}]
    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=WORKER_SYSTEM_PROMPTS[worker_name],
            tools=tools,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason != "tool_use":
            return "".join(b.text for b in response.content if b.type == "text")

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            print(f"    [{worker_name} calls] {block.name}({block.input})")
            result = await session.call_tool(block.name, arguments=block.input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result.content[0].text,
                }
            )
        messages.append({"role": "user", "content": tool_results})


# The orchestrator doesn't get the real MCP tools at all -- its only
# "tool" is the ability to hand a subtask to a worker.
DISPATCH_TOOL = {
    "name": "dispatch_to_worker",
    "description": "Send a subtask to a specialist worker agent and get its answer back.",
    "input_schema": {
        "type": "object",
        "properties": {
            "worker": {"type": "string", "enum": ["research", "math"]},
            "subtask": {"type": "string", "description": "The exact subtask for that worker"},
        },
        "required": ["worker", "subtask"],
    },
}

ORCHESTRATOR_SYSTEM = (
    "You are an orchestrator. Break the user's request into subtasks and "
    "dispatch each one to the right specialist worker using the "
    "dispatch_to_worker tool. 'research' knows weather and internal notes. "
    "'math' does calculations. Once you have every piece you need, "
    "give one final combined answer in plain text -- do not call any more tools."
)


async def run_orchestrator(user_prompt: str) -> str:
    async with stdio_client(SERVER_PARAMS) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            messages = [{"role": "user", "content": user_prompt}]

            while True:
                response = client.messages.create(
                    model=MODEL,
                    max_tokens=1024,
                    system=ORCHESTRATOR_SYSTEM,
                    tools=[DISPATCH_TOOL],
                    messages=messages,
                )
                messages.append({"role": "assistant", "content": response.content})

                if response.stop_reason != "tool_use":
                    return "".join(b.text for b in response.content if b.type == "text")

                tool_results = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue
                    worker = block.input["worker"]
                    subtask = block.input["subtask"]
                    print(f"[orchestrator dispatches -> {worker}] {subtask}")
                    answer = await run_worker(session, worker, subtask)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": answer,
                        }
                    )
                messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    result = asyncio.run(
        run_orchestrator(
            "What's the weather in Delhi, and separately, what is 15 + 27? "
            "Give me both answers together."
        )
    )
    print("\n=== FINAL ANSWER ===\n", result)
