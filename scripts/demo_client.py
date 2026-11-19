"""Demonstrate MCP discovery and tool invocation against the Spotnxt server.

By default the script launches the server over stdio, exactly like a local
Claude Desktop MCP server. It can also connect to a running FastAPI instance:

    python scripts/demo_client.py
    python scripts/demo_client.py --transport http --url http://127.0.0.1:8000/mcp

The output is intentionally verbose so it can be copied into a README or demo
transcript as proof of discovery and invocation.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp import Client
from mcp.client.stdio import StdioServerParameters

ROOT = Path(__file__).resolve().parents[1]


def _clean(value: Any) -> Any:
    """Return a JSON-serializable representation of an MCP tool result."""

    if hasattr(value, "is_error") and value.is_error:
        messages = [getattr(block, "text", str(block)) for block in value.content]
        return {"is_error": True, "message": " ".join(messages)}

    if hasattr(value, "structured_content") and value.structured_content is not None:
        return value.structured_content

    if hasattr(value, "content"):
        texts = [getattr(block, "text", str(block)) for block in value.content]
        if len(texts) == 1:
            try:
                return json.loads(texts[0])
            except json.JSONDecodeError:
                return texts[0]
        return texts

    return value


def _print(title: str, value: Any) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(value, indent=2, default=str))


async def run_demo(client: Client) -> None:
    tools = await client.list_tools()
    _print(
        "MCP tools discovered",
        [
            {
                "name": tool.name,
                "description": tool.description,
                "input": tool.input_schema,
            }
            for tool in tools.tools
        ],
    )

    result = await client.call_tool("list_campaigns", {})
    _print("list_campaigns", _clean(result))

    result = await client.call_tool(
        "read_ad_data", {"campaign_id": "cmp_1001"}
    )
    _print("read_ad_data(cmp_1001)", _clean(result))

    result = await client.call_tool(
        "calculate_ad_metrics",
        {
            "spend": 1_000,
            "impressions": 100_000,
            "clicks": 2_000,
            "conversions": 40,
        },
    )
    _print("calculate_ad_metrics(1000, 100000, 2000, 40)", _clean(result))

    result = await client.call_tool(
        "campaign_summary", {"campaign_id": "cmp_1002"}
    )
    _print("campaign_summary(cmp_1002)", _clean(result))

    result = await client.call_tool(
        "read_ad_data", {"campaign_id": "cmp_9999"}
    )
    _print("read_ad_data error handling(cmp_9999)", _clean(result))


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--transport",
        choices=("stdio", "http"),
        default="stdio",
        help="MCP transport to demonstrate (default: stdio).",
    )
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000/mcp",
        help="Streamable HTTP endpoint when --transport http is used.",
    )
    args = parser.parse_args()

    if args.transport == "http":
        async with Client(args.url) as client:
            await run_demo(client)
        return

    params = StdioServerParameters(
        command=sys.executable,
        args=[str(ROOT / "app" / "mcp_server.py")],
        cwd=ROOT,
    )
    async with Client(params) as client:
        await run_demo(client)


if __name__ == "__main__":
    asyncio.run(main())
