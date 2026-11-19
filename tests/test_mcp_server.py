"""Protocol-level tests for MCP tool discovery and invocation."""

from __future__ import annotations

import asyncio
from typing import Any, Coroutine

from mcp import Client

from app.mcp_server import create_mcp_server

EXPECTED_TOOLS = {
    "read_ad_data",
    "calculate_ad_metrics",
    "campaign_summary",
    "list_campaigns",
}


def run(coro: Coroutine[Any, Any, Any]) -> Any:
    """Run an async MCP session and return its result."""

    return asyncio.run(coro)


def test_discovers_required_tools() -> None:
    async def scenario() -> list[str]:
        async with Client(create_mcp_server()) as client:
            result = await client.list_tools()
            return [tool.name for tool in result.tools]

    names = run(scenario())

    assert set(names) == EXPECTED_TOOLS
    assert len(names) == len(EXPECTED_TOOLS)


def test_tool_schemas_expose_validation() -> None:
    async def scenario() -> dict[str, Any]:
        async with Client(create_mcp_server()) as client:
            result = await client.list_tools()
            return {tool.name: tool for tool in result.tools}

    tools = run(scenario())
    calculate = tools["calculate_ad_metrics"]

    assert calculate.input_schema["required"] == [
        "spend",
        "impressions",
        "clicks",
        "conversions",
    ]
    spend_schema = calculate.input_schema["properties"]["spend"]
    assert spend_schema["minimum"] == 0
    assert calculate.output_schema is not None


def test_reads_ad_data() -> None:
    async def scenario() -> Any:
        async with Client(create_mcp_server()) as client:
            return await client.call_tool(
                "read_ad_data", {"campaign_id": "CMP_1001"}
            )

    result = run(scenario())

    assert result.is_error is False
    assert result.structured_content is not None
    assert result.structured_content["campaign_id"] == "cmp_1001"
    assert result.structured_content["spend"] == 12_500.0
    assert result.structured_content["impressions"] == 1_250_000
    assert result.structured_content["clicks"] == 18_750
    assert result.structured_content["conversions"] == 1_125


def test_calculates_metrics() -> None:
    async def scenario() -> Any:
        async with Client(create_mcp_server()) as client:
            return await client.call_tool(
                "calculate_ad_metrics",
                {
                    "spend": 1000,
                    "impressions": 100_000,
                    "clicks": 2000,
                    "conversions": 40,
                },
            )

    result = run(scenario())

    assert result.is_error is False
    assert result.structured_content == {
        "ctr": 2.0,
        "cpc": 0.5,
        "cpa": 25.0,
        "cpm": 10.0,
    }


def test_returns_campaign_summary() -> None:
    async def scenario() -> Any:
        async with Client(create_mcp_server()) as client:
            return await client.call_tool(
                "campaign_summary", {"campaign_id": "cmp_1002"}
            )

    result = run(scenario())

    assert result.is_error is False
    assert result.structured_content is not None
    assert result.structured_content["performance"] == "Strong"
    assert result.structured_content["metrics"]["ctr"] == 3.0
    assert "Cart Abandoner Retargeting" in result.structured_content["summary"]


def test_unknown_campaign_is_a_tool_error() -> None:
    async def scenario() -> Any:
        async with Client(create_mcp_server()) as client:
            return await client.call_tool(
                "read_ad_data", {"campaign_id": "cmp_9999"}
            )

    result = run(scenario())

    assert result.is_error is True
    assert result.content
    assert "was not found" in result.content[0].text
    assert "cmp_1001" in result.content[0].text


def test_invalid_metric_combination_is_a_tool_error() -> None:
    async def scenario() -> Any:
        async with Client(create_mcp_server()) as client:
            return await client.call_tool(
                "calculate_ad_metrics",
                {
                    "spend": 100,
                    "impressions": 10,
                    "clicks": 11,
                    "conversions": 1,
                },
            )

    result = run(scenario())

    assert result.is_error is True
    assert result.content
    assert "clicks cannot exceed impressions" in result.content[0].text


def test_negative_input_is_rejected_by_schema() -> None:
    async def scenario() -> Any:
        async with Client(create_mcp_server()) as client:
            return await client.call_tool(
                "calculate_ad_metrics",
                {
                    "spend": -5,
                    "impressions": 10,
                    "clicks": 1,
                    "conversions": 1,
                },
            )

    result = run(scenario())

    assert result.is_error is True
    assert result.content
    assert "greater than or equal to 0" in result.content[0].text
