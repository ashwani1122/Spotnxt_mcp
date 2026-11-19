"""Mock advertising campaign data and campaign lookup helpers.

The assignment intentionally does not require the Meta Ads API, so this module
acts as the single source of truth for the in-memory campaign dataset.
"""

from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, ConfigDict, Field

# Campaign IDs are deliberately constrained so malformed input is rejected
# before a lookup is attempted.
CAMPAIGN_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")


class Campaign(BaseModel):
    """A single advertising campaign and its lifetime performance totals."""

    model_config = ConfigDict(frozen=True)

    campaign_id: str = Field(description="Stable campaign identifier, e.g. cmp_1001.")
    name: str = Field(description="Human-readable campaign name.")
    platform: str = Field(description="Advertising platform, e.g. Meta or Instagram.")
    status: str = Field(description="Campaign status: ACTIVE, PAUSED, or COMPLETED.")
    objective: str = Field(description="Primary campaign objective.")
    start_date: date = Field(description="Campaign start date (YYYY-MM-DD).")
    end_date: date = Field(description="Campaign end date (YYYY-MM-DD).")
    currency: str = Field(default="USD", description="ISO 4217 currency code.")
    spend: float = Field(ge=0, description="Total spend in the campaign currency.")
    impressions: int = Field(ge=0, description="Total ad impressions delivered.")
    clicks: int = Field(ge=0, description="Total link clicks.")
    conversions: int = Field(ge=0, description="Total attributed conversions.")


class CampaignListItem(BaseModel):
    """Compact campaign representation used by list endpoints/tools."""

    model_config = ConfigDict(frozen=True)

    campaign_id: str
    name: str
    platform: str
    status: str
    objective: str
    spend: float
    currency: str = "USD"


class CampaignNotFoundError(LookupError):
    """Raised when a syntactically valid campaign ID does not exist."""


class InvalidCampaignIdError(ValueError):
    """Raised when a campaign ID is empty or has an invalid format."""


# Five realistic mock campaigns. Numbers are lifetime totals and are internally
# consistent (clicks <= impressions, conversions <= clicks).
CAMPAIGNS: tuple[Campaign, ...] = (
    Campaign(
        campaign_id="cmp_1001",
        name="Summer Sale - Prospecting",
        platform="Meta",
        status="ACTIVE",
        objective="Sales",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 8, 31),
        spend=12_500.00,
        impressions=1_250_000,
        clicks=18_750,
        conversions=1_125,
    ),
    Campaign(
        campaign_id="cmp_1002",
        name="Cart Abandoner Retargeting",
        platform="Instagram",
        status="ACTIVE",
        objective="Sales",
        start_date=date(2026, 9, 1),
        end_date=date(2026, 12, 31),
        spend=4_800.00,
        impressions=320_000,
        clicks=9_600,
        conversions=768,
    ),
    Campaign(
        campaign_id="cmp_1003",
        name="Q3 Brand Awareness",
        platform="Meta",
        status="COMPLETED",
        objective="Awareness",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 9, 30),
        spend=8_000.00,
        impressions=2_000_000,
        clicks=6_000,
        conversions=240,
    ),
    Campaign(
        campaign_id="cmp_1004",
        name="B2B Demo Requests",
        platform="Meta",
        status="PAUSED",
        objective="Lead generation",
        start_date=date(2026, 8, 15),
        end_date=date(2026, 11, 15),
        spend=6_200.00,
        impressions=155_000,
        clicks=3_410,
        conversions=186,
    ),
    Campaign(
        campaign_id="cmp_1005",
        name="Holiday Video Teaser",
        platform="Instagram",
        status="ACTIVE",
        objective="Video views",
        start_date=date(2026, 11, 1),
        end_date=date(2026, 12, 31),
        spend=3_500.00,
        impressions=875_000,
        clicks=2_625,
        conversions=105,
    ),
)

_CAMPAIGNS_BY_ID: dict[str, Campaign] = {
    campaign.campaign_id: campaign for campaign in CAMPAIGNS
}


def normalize_campaign_id(campaign_id: str) -> str:
    """Validate and normalize a campaign ID.

    Lookup is case-insensitive and surrounding whitespace is ignored, while the
    ID itself must be 1-32 characters of letters, digits, ``_`` or ``-`` and
    start with a letter or digit.
    """

    if not isinstance(campaign_id, str):
        raise InvalidCampaignIdError("Campaign ID must be a string.")

    normalized = campaign_id.strip().lower()
    if not normalized:
        raise InvalidCampaignIdError("Campaign ID cannot be empty.")
    if not CAMPAIGN_ID_PATTERN.fullmatch(normalized):
        raise InvalidCampaignIdError(
            "Campaign ID must be 1-32 characters using letters, digits, "
            "underscores, or hyphens, and must start with a letter or digit."
        )
    return normalized


def get_campaign(campaign_id: str) -> Campaign:
    """Return a campaign by ID.

    Raises:
        InvalidCampaignIdError: If ``campaign_id`` is malformed.
        CampaignNotFoundError: If the ID is valid but no campaign exists.
    """

    normalized = normalize_campaign_id(campaign_id)
    try:
        return _CAMPAIGNS_BY_ID[normalized]
    except KeyError as exc:
        available = ", ".join(campaign.campaign_id for campaign in CAMPAIGNS)
        raise CampaignNotFoundError(
            f"Campaign '{normalized}' was not found. Available campaign IDs: {available}."
        ) from exc


def list_campaigns() -> list[Campaign]:
    """Return all mock campaigns."""

    return list(CAMPAIGNS)


def list_campaign_summaries() -> list[CampaignListItem]:
    """Return compact representations of every mock campaign."""

    return [
        CampaignListItem(
            campaign_id=campaign.campaign_id,
            name=campaign.name,
            platform=campaign.platform,
            status=campaign.status,
            objective=campaign.objective,
            spend=campaign.spend,
            currency=campaign.currency,
        )
        for campaign in CAMPAIGNS
    ]
