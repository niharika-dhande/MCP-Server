"""
01 — A minimal MCP server, built with the official Python MCP SDK.

This exposes 3 tools that any MCP-speaking client (Claude Desktop, Claude
Code, or your own agent code below) can discover and call:
  - add_numbers   : pure calculation
  - get_weather   : mocked "external API"
  - search_notes  : mocked internal knowledge base

Install:
    pip install "mcp[cli]"

Run it standalone to poke at it with the MCP Inspector:
    mcp dev 01_mcp_server.py

You won't normally run this file by hand otherwise — 02/03/04 launch it
for you as a subprocess over stdio (that's how MCP's stdio transport works:
the client starts the server process and talks to it over stdin/stdout).
"""

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("demo-tools")


# ---- Tool 1: pure calculation, no external system involved ----
@mcp.tool()
def add_numbers(a: float, b: float) -> float:
    """Add two numbers and return the sum."""
    return a + b


# ---- Tool 2: stands in for "call some external API" ----
@mcp.tool()
def get_weather(city: str) -> str:
    """Get the current weather for a city (mocked data for this demo)."""
    fake_data = {
        "indore": "32°C, clear skies",
        "mumbai": "29°C, humid, light rain",
        "delhi": "27°C, hazy",
    }
    return fake_data.get(city.lower(), f"No weather data found for {city}")


# ---- Tool 3: stands in for "search a private knowledge base" ----
NOTES = {
    "mcp": "MCP standardizes how AI apps connect to external tools and data.",
    "agent": "An agent is an LLM that can plan, call tools, and act in a loop.",
    "orchestration": "Orchestration means one agent coordinating several others.",
}


@mcp.tool()
def search_notes(query: str) -> str:
    """Search a small internal notes database for a keyword."""
    query = query.lower()
    hits = [v for k, v in NOTES.items() if query in k]
    return " | ".join(hits) if hits else "No matching notes found."


if __name__ == "__main__":
    # stdio transport: whoever launches this process talks to it over
    # stdin/stdout using the MCP message format (JSON-RPC 2.0 under the hood)
    mcp.run(transport="stdio")
