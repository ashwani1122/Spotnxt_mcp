"""Official MCP Python SDK server exposing the Spotnxt advertising tools.

Run this module directly to speak MCP over stdio (the transport Claude Desktop
uses for local servers)::

    python app/mcp_server.py

The FastAPI application in ``app.main`` mounts the same tools over MCP
Streamable HTTP at ``/mcp``.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Annotated

# Allow ``python app/mcp_server.py`` without requiring the repository root to be
# on sys.path or the project to be installed as a package.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from app import __version__
from app.data import (
    Campaign,
    CampaignListItem,
    CampaignNotFoundError,
    InvalidCampaignIdError,
    get_campaign,
    list_campaign_summaries,
)
from app.metrics import (
    AdMetrics,
    CampaignSummary,
    InvalidMetricsError,
    build_campaign_summary,
    calculate_metrics,
)

SpendAmount = Annotated[
    float,
    Field(
        ge=0,
        le=1_000_000_000,
        allow_inf_nan=False,
        description="Total ad spend in USD. Must be zero or greater.",
    ),
]
ImpressionCount = Annotated[
    int,
    Field(
        ge=0,
        le=1_000_000_000_000,
        description="Number of ad impressions. Must be zero or greater.",
    ),
]
ClickCount = Annotated[
    int,
    Field(
        ge=0,
        le=1_000_000_000_000,
        description="Number of clicks. Must be zero or greater.",
    ),
]
ConversionCount = Annotated[
    int,
    Field(
        ge=0,
        le=1_000_000_000_000,
        description="Number of conversions. Must be zero or greater.",
    ),
]

SERVER_INSTRUCTIONS = """
Spotnxt provides mock advertising campaign analytics. Spend values are in USD.

- Use read_ad_data when the user supplies a campaign ID and wants the raw
  spend, impressions, clicks, and conversions.
- Use calculate_ad_metrics when the user supplies raw numbers directly. CTR is
  returned as a percentage. Metrics with a zero denominator are null.
- Use campaign_summary when the user asks how a campaign is performing; it
  fetches the campaign, calculates metrics, and returns a summary plus insights.
- Use list_campaigns if the user needs to discover a valid campaign ID.

All data is fictional and no real advertising platform is called.
""".strip()


def _campaign_or_tool_error(campaign_id: str) -> Campaign:
    """Translate domain validation errors into MCP tool errors."""

    try:
        return get_campaign(campaign_id)
    except (InvalidCampaignIdError, CampaignNotFoundError) as exc:
        raise ToolError(str(exc)) from exc


def create_mcp_server() -> MCPServer:
    """Create and configure a fresh MCP server instance."""

    mcp = MCPServer(
        name="spotnxt-ad-metrics",
        title="Spotnxt Ad Metrics",
        description=(
            "Mock advertising campaign data plus CTR, CPC, CPA, and CPM "
            "calculations."
        ),
        instructions=SERVER_INSTRUCTIONS,
        version=__version__,
    )

    read_only = ToolAnnotations(
        readOnlyHint=True,
        destructiveHint=False,
        idempotentHint=True,
        openWorldHint=False,
    )

    @mcp.tool(
        title="Read Ad Data",
        description=(
            "Fetch mock advertising data for one campaign ID. Returns spend "
            "(USD), impressions, clicks, conversions, and campaign metadata. "
            "Use a campaign ID such as cmp_1001."
        ),
        annotations=read_only,
    )
    def read_ad_data(campaign_id: str) -> Campaign:
        """Read raw campaign performance data by campaign ID."""

        return _campaign_or_tool_error(campaign_id)

    @mcp.tool(
        title="Calculate Ad Metrics",
        description=(
            "Calculate advertising metrics from raw totals: CTR as a "
            "percentage, CPC, CPA, and CPM in USD. Each calculation is based "
            "on spend, impressions, clicks, and conversions. Metrics whose "
            "denominator is zero are returned as null."
        ),
        annotations=read_only,
    )
    def calculate_ad_metrics(
        spend: SpendAmount,
        impressions: ImpressionCount,
        clicks: ClickCount,
        conversions: ConversionCount,
    ) -> AdMetrics:
        """Calculate CTR, CPC, CPA, and CPM from raw advertising totals."""

        try:
            return calculate_metrics(
                spend=spend,
                impressions=impressions,
                clicks=clicks,
                conversions=conversions,
            )
        except InvalidMetricsError as exc:
            raise ToolError(str(exc)) from exc

    @mcp.tool(
        title="Campaign Summary",
        description=(
            "Fetch a campaign by ID, calculate its CTR, CPC, CPA, and CPM, "
            "and return a concise performance summary with benchmark-based "
            "insights. Use this for questions such as 'How is cmp_1002 doing?'"
        ),
        annotations=read_only,
    )
    def campaign_summary(campaign_id: str) -> CampaignSummary:
        """Return a calculated performance summary for one campaign."""

        campaign = _campaign_or_tool_error(campaign_id)
        return build_campaign_summary(campaign)

    @mcp.tool(
        title="List Campaigns",
        description=(
            "List the available mock campaigns with their IDs, names, status, "
            "platform, and total spend. Use this to discover a valid ID."
        ),
        annotations=read_only,
    )
    def list_campaigns() -> list[CampaignListItem]:
        """List all available mock campaigns."""

        return list_campaign_summaries()

    return mcp


def main() -> None:
    """Run the MCP server over stdio."""

    create_mcp_server().run(transport="stdio")


if __name__ == "__main__":
    main()
