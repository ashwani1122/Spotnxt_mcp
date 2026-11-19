"""Advertising metric calculations and campaign performance summaries.

Formulas
--------
CTR  = clicks / impressions * 100       (reported as a percentage)
CPC  = spend / clicks
CPA  = spend / conversions
CPM  = spend / impressions * 1000

A metric is returned as ``None`` when its denominator is zero; a zero would be
mathematically undefined rather than a real performance result.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from pydantic import BaseModel, Field, ValidationError, model_validator

from .data import Campaign

MetricRating = Literal["good", "okay", "poor", "unavailable"]

# Quantize calculated values to four decimal places. This keeps API/tool output
# clean while retaining enough precision for downstream analysis.
_PRECISION = Decimal("0.0001")


class AdMetrics(BaseModel):
    """Calculated advertising efficiency metrics."""

    ctr: float | None = Field(
        description="Click-through rate as a percentage: clicks / impressions * 100."
    )
    cpc: float | None = Field(
        description="Cost per click in the campaign currency: spend / clicks."
    )
    cpa: float | None = Field(
        description="Cost per acquisition: spend / conversions."
    )
    cpm: float | None = Field(
        description="Cost per 1,000 impressions: spend / impressions * 1000."
    )


class MetricsInput(BaseModel):
    """Validated raw inputs for metric calculations."""

    spend: float = Field(
        ge=0,
        le=1_000_000_000,
        allow_inf_nan=False,
        description="Total spend. Must be zero or greater.",
    )
    impressions: int = Field(
        ge=0,
        le=1_000_000_000_000,
        description="Total impressions. Must be zero or greater.",
    )
    clicks: int = Field(
        ge=0,
        le=1_000_000_000_000,
        description="Total clicks. Must be zero or greater.",
    )
    conversions: int = Field(
        ge=0,
        le=1_000_000_000_000,
        description="Total conversions. Must be zero or greater.",
    )

    @model_validator(mode="after")
    def _clicks_cannot_exceed_impressions(self) -> "MetricsInput":
        if self.clicks > self.impressions:
            raise ValueError("clicks cannot exceed impressions")
        return self


class InvalidMetricsError(ValueError):
    """Raised when raw metric inputs are invalid."""


class CampaignSummary(BaseModel):
    """A ready-to-relay campaign performance summary."""

    campaign_id: str
    name: str
    platform: str
    status: str
    currency: str
    spend: float
    impressions: int
    clicks: int
    conversions: int
    metrics: AdMetrics
    performance: Literal["Strong", "On track", "Needs improvement"]
    summary: str
    insights: list[str]


def _divide(numerator: float | int, denominator: float | int) -> Decimal | None:
    """Divide with Decimal arithmetic, returning None for a zero denominator."""

    if denominator == 0:
        return None
    return Decimal(str(numerator)) / Decimal(str(denominator))


def _rounded(value: Decimal | None, multiplier: int = 1) -> float | None:
    if value is None:
        return None
    return float(
        (value * Decimal(multiplier)).quantize(_PRECISION, rounding=ROUND_HALF_UP)
    )


def calculate_metrics(
    spend: float,
    impressions: int,
    clicks: int,
    conversions: int,
) -> AdMetrics:
    """Validate raw numbers and calculate CTR, CPC, CPA, and CPM.

    Raises:
        InvalidMetricsError: If values are negative, non-finite, exceed the
            supported range, or clicks exceed impressions.
    """

    try:
        validated = MetricsInput(
            spend=spend,
            impressions=impressions,
            clicks=clicks,
            conversions=conversions,
        )
    except ValidationError as exc:
        details = []
        for error in exc.errors():
            field = ".".join(str(part) for part in error["loc"]) or "input"
            details.append(f"{field}: {error['msg']}")
        raise InvalidMetricsError("Invalid ad metrics - " + "; ".join(details)) from exc

    return AdMetrics(
        ctr=_rounded(_divide(validated.clicks, validated.impressions), multiplier=100),
        cpc=_rounded(_divide(validated.spend, validated.clicks)),
        cpa=_rounded(_divide(validated.spend, validated.conversions)),
        cpm=_rounded(_divide(validated.spend, validated.impressions), multiplier=1000),
    )


def _rate_ctr(ctr: float | None) -> MetricRating:
    if ctr is None:
        return "unavailable"
    if ctr >= 2.0:
        return "good"
    if ctr >= 1.0:
        return "okay"
    return "poor"


def _rate_cpc(cpc: float | None) -> MetricRating:
    if cpc is None:
        return "unavailable"
    if cpc <= 1.50:
        return "good"
    if cpc <= 3.00:
        return "okay"
    return "poor"


def _rate_cpa(cpa: float | None) -> MetricRating:
    if cpa is None:
        return "unavailable"
    if cpa <= 15.00:
        return "good"
    if cpa <= 30.00:
        return "okay"
    return "poor"


def _rate_cpm(cpm: float | None) -> MetricRating:
    if cpm is None:
        return "unavailable"
    if cpm <= 12.00:
        return "good"
    if cpm <= 25.00:
        return "okay"
    return "poor"


def _money(value: float | None, currency: str) -> str:
    if value is None:
        return "unavailable"
    symbol = "$" if currency.upper() == "USD" else f"{currency} "
    return f"{symbol}{value:,.2f}"


def _percent(value: float | None) -> str:
    return "unavailable" if value is None else f"{value:.2f}%"


def _build_insights(
    metrics: AdMetrics, ratings: dict[str, MetricRating], currency: str
) -> list[str]:
    """Turn metric ratings into concise, human-readable observations."""

    insights: list[str] = []

    if ratings["ctr"] == "unavailable":
        insights.append("CTR is unavailable because there were no impressions.")
    else:
        comparisons = {
            "good": "above the 2.00% benchmark",
            "okay": "within the 1.00-2.00% benchmark range",
            "poor": "below the 1.00% benchmark",
        }
        insights.append(
            f"CTR of {_percent(metrics.ctr)} is {comparisons[ratings['ctr']]}."
        )

    if ratings["cpc"] == "unavailable":
        insights.append("CPC is unavailable because there were no clicks.")
    else:
        comparisons = {
            "good": "below the $1.50 target",
            "okay": "within the $1.50-$3.00 range",
            "poor": "above the $3.00 target",
        }
        insights.append(
            f"CPC of {_money(metrics.cpc, currency)} is {comparisons[ratings['cpc']]}."
        )

    if ratings["cpa"] == "unavailable":
        insights.append("CPA is unavailable because there were no conversions.")
    else:
        comparisons = {
            "good": "within the $15.00 target",
            "okay": "within the $15.00-$30.00 range",
            "poor": "above the $30.00 target",
        }
        insights.append(
            f"CPA of {_money(metrics.cpa, currency)} is {comparisons[ratings['cpa']]}."
        )

    if ratings["cpm"] == "unavailable":
        insights.append("CPM is unavailable because there were no impressions.")
    else:
        comparisons = {
            "good": "below the $12.00 target",
            "okay": "within the $12.00-$25.00 range",
            "poor": "above the $25.00 target",
        }
        insights.append(
            f"CPM of {_money(metrics.cpm, currency)} is {comparisons[ratings['cpm']]}."
        )

    return insights


def _overall_performance(
    ratings: dict[str, MetricRating],
) -> Literal["Strong", "On track", "Needs improvement"]:
    poor_count = sum(rating == "poor" for rating in ratings.values())
    good_count = sum(rating == "good" for rating in ratings.values())
    available_count = sum(rating != "unavailable" for rating in ratings.values())

    if available_count == 0:
        return "Needs improvement"
    if poor_count >= 2:
        return "Needs improvement"
    if good_count >= 3 and poor_count == 0:
        return "Strong"
    return "On track"


def build_campaign_summary(campaign: Campaign) -> CampaignSummary:
    """Calculate metrics and produce a simple performance summary."""

    metrics = calculate_metrics(
        spend=campaign.spend,
        impressions=campaign.impressions,
        clicks=campaign.clicks,
        conversions=campaign.conversions,
    )
    ratings: dict[str, MetricRating] = {
        "ctr": _rate_ctr(metrics.ctr),
        "cpc": _rate_cpc(metrics.cpc),
        "cpa": _rate_cpa(metrics.cpa),
        "cpm": _rate_cpm(metrics.cpm),
    }
    performance = _overall_performance(ratings)
    performance_phrase = {
        "Strong": "strong",
        "On track": "on track",
        "Needs improvement": "in need of improvement",
    }[performance]

    summary = (
        f"{campaign.name} is {campaign.status} and has spent "
        f"{_money(campaign.spend, campaign.currency)}, delivering "
        f"{campaign.impressions:,} impressions, {campaign.clicks:,} clicks, and "
        f"{campaign.conversions:,} conversions. CTR is {_percent(metrics.ctr)}, "
        f"CPC is {_money(metrics.cpc, campaign.currency)}, CPA is "
        f"{_money(metrics.cpa, campaign.currency)}, and CPM is "
        f"{_money(metrics.cpm, campaign.currency)}. Overall performance is "
        f"{performance_phrase} against the included benchmark."
    )

    return CampaignSummary(
        campaign_id=campaign.campaign_id,
        name=campaign.name,
        platform=campaign.platform,
        status=campaign.status,
        currency=campaign.currency,
        spend=campaign.spend,
        impressions=campaign.impressions,
        clicks=campaign.clicks,
        conversions=campaign.conversions,
        metrics=metrics,
        performance=performance,
        summary=summary,
        insights=_build_insights(metrics, ratings, campaign.currency),
    )
