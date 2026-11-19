"""FastAPI application hosting both REST endpoints and the MCP server.

REST is useful for quick manual checks and the OpenAPI docs. The assignment's
MCP tools are the primary interface and are mounted at ``/mcp`` using the
official MCP SDK's Streamable HTTP transport.

Run from the repository root::

    uvicorn app.main:app --reload
"""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import FastAPI, HTTPException

from app import __version__
from app.data import (
    Campaign,
    CampaignListItem,
    CampaignNotFoundError,
    InvalidCampaignIdError,
    get_campaign,
    list_campaign_summaries,
)
from app.mcp_server import create_mcp_server
from app.metrics import (
    AdMetrics,
    CampaignSummary,
    InvalidMetricsError,
    MetricsInput,
    build_campaign_summary,
    calculate_metrics,
)


def _get_campaign_or_http_error(campaign_id: str) -> Campaign:
    try:
        return get_campaign(campaign_id)
    except InvalidCampaignIdError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except CampaignNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


def create_app() -> FastAPI:
    """Create a FastAPI app with REST routes and an MCP Streamable HTTP mount."""

    mcp = create_mcp_server()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        # The MCP session manager owns the Streamable HTTP session lifecycle.
        async with mcp.session_manager.run():
            yield

    application = FastAPI(
        title="Spotnxt Ad Metrics MCP Server",
        description=(
            "Mock advertising analytics exposed through MCP tools and a small "
            "FastAPI REST API. MCP endpoint: /mcp"
        ),
        version=__version__,
        lifespan=lifespan,
    )

    @application.get("/", tags=["service"])
    def service_info() -> dict[str, object]:
        """Return service metadata and useful entry points."""

        return {
            "service": "Spotnxt Ad Metrics MCP Server",
            "version": __version__,
            "mcp_endpoint": "/mcp",
            "docs": "/docs",
            "health": "/healthz",
            "tools": [
                "read_ad_data",
                "calculate_ad_metrics",
                "campaign_summary",
                "list_campaigns",
            ],
        }

    @application.get("/healthz", tags=["service"])
    def healthz() -> dict[str, str]:
        """Liveness probe."""

        return {"status": "ok"}

    @application.get(
        "/api/campaigns",
        response_model=list[CampaignListItem],
        tags=["campaigns"],
    )
    def get_campaigns() -> list[CampaignListItem]:
        """List all mock campaigns."""

        return list_campaign_summaries()

    @application.get(
        "/api/campaigns/{campaign_id}",
        response_model=Campaign,
        tags=["campaigns"],
    )
    def get_campaign_by_id(campaign_id: str) -> Campaign:
        """Fetch raw campaign data by ID."""

        return _get_campaign_or_http_error(campaign_id)

    @application.get(
        "/api/campaigns/{campaign_id}/summary",
        response_model=CampaignSummary,
        tags=["campaigns"],
    )
    def get_campaign_summary(campaign_id: str) -> CampaignSummary:
        """Fetch a campaign and return its calculated performance summary."""

        campaign = _get_campaign_or_http_error(campaign_id)
        try:
            return build_campaign_summary(campaign)
        except InvalidMetricsError as exc:  # Defensive: mock data is valid.
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    @application.post(
        "/api/metrics/calculate",
        response_model=AdMetrics,
        tags=["metrics"],
    )
    def calculate_metrics_endpoint(payload: MetricsInput) -> AdMetrics:
        """Calculate CTR, CPC, CPA, and CPM from raw totals."""

        try:
            return calculate_metrics(
                spend=payload.spend,
                impressions=payload.impressions,
                clicks=payload.clicks,
                conversions=payload.conversions,
            )
        except InvalidMetricsError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Mount last: FastAPI/Starlette serves the explicit REST routes and docs
    # above, then delegates everything else (including /mcp) to the MCP app.
    mcp_app = mcp.streamable_http_app(streamable_http_path="/mcp")
    application.mount("/", mcp_app)

    return application


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
