"""
05 — The "production" way to get the same result as 04 (an orchestrator
delegating to specialist workers) using Anthropic's own Claude Agent SDK.

The SDK gives you the agent loop, tool wiring, and subagent hand-off for
free -- you just describe the subagents and let Claude decide when to
call each one via the built-in Agent tool. Compare this file to 04 to
see exactly what the SDK is doing under the hood.

Install:
    pip install claude-agent-sdk
Env:
    export ANTHROPIC_API_KEY=your-key

Run:
    python 05_agent_sdk_subagents.py

Note: to give a subagent access to YOUR OWN MCP server (like
01_mcp_server.py) instead of the SDK's built-in tools, wire it in via
the mcp_servers option on ClaudeAgentOptions -- check the current
Claude Agent SDK docs for the exact config shape, since this is an
actively evolving part of the SDK.
"""

import asyncio

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions, query


async def main():
    options = ClaudeAgentOptions(
        # The orchestrator needs the Agent tool to be able to hand off
        # work to a subagent at all.
        allowed_tools=["Agent"],
        agents={
            "research": AgentDefinition(
                description="Looks up weather and internal notes. Use for factual lookups.",
                prompt="You are a research specialist. Be concise.",
            ),
            "math": AgentDefinition(
                description="Performs exact calculations.",
                prompt="You are a calculation specialist. Be concise.",
            ),
        },
    )

    async for message in query(
        prompt=(
            "What's the weather in Delhi, and separately, what is 15 + 27? "
            "Give me both answers together."
        ),
        options=options,
    ):
        if message.type == "assistant":
            print(message.content)


if __name__ == "__main__":
    asyncio.run(main())
