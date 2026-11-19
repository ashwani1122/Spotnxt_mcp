"""Unit tests for metric formulas, validation, and summaries."""

from __future__ import annotations

import math

import pytest

from app.data import (
    CampaignNotFoundError,
    InvalidCampaignIdError,
    get_campaign,
    list_campaigns,
)
from app.metrics import (
    InvalidMetricsError,
    build_campaign_summary,
    calculate_metrics,
)


def test_calculates_standard_metrics() -> None:
    metrics = calculate_metrics(
        spend=1_000.0,
        impressions=100_000,
        clicks=2_000,
        conversions=40,
    )

    assert metrics.ctr == pytest.approx(2.0)
    assert metrics.cpc == pytest.approx(0.5)
    assert metrics.cpa == pytest.approx(25.0)
    assert metrics.cpm == pytest.approx(10.0)


def test_matches_campaign_totals() -> None:
    campaign = get_campaign("cmp_1001")
    metrics = calculate_metrics(
        spend=campaign.spend,
        impressions=campaign.impressions,
        clicks=campaign.clicks,
        conversions=campaign.conversions,
    )

    assert metrics.model_dump() == {
        "ctr": 1.5,
        "cpc": 0.6667,
        "cpa": 11.1111,
        "cpm": 10.0,
    }


def test_zero_denominators_return_none() -> None:
    metrics = calculate_metrics(
        spend=250.0,
        impressions=0,
        clicks=0,
        conversions=0,
    )

    assert metrics.ctr is None
    assert metrics.cpc is None
    assert metrics.cpa is None
    assert metrics.cpm is None


def test_zero_clicks_and_conversions_only_undefine_their_metrics() -> None:
    metrics = calculate_metrics(
        spend=100.0,
        impressions=10_000,
        clicks=0,
        conversions=0,
    )

    assert metrics.ctr == 0.0
    assert metrics.cpc is None
    assert metrics.cpa is None
    assert metrics.cpm == 10.0


def test_rounds_to_four_decimal_places() -> None:
    metrics = calculate_metrics(
        spend=10.0,
        impressions=3,
        clicks=3,
        conversions=3,
    )

    assert metrics.ctr == 100.0
    assert metrics.cpc == 3.3333
    assert metrics.cpa == 3.3333
    assert metrics.cpm == 3333.3333


@pytest.mark.parametrize(
    "kwargs",
    [
        {"spend": -1.0, "impressions": 100, "clicks": 1, "conversions": 0},
        {"spend": 1.0, "impressions": -1, "clicks": 0, "conversions": 0},
        {"spend": 1.0, "impressions": 100, "clicks": -1, "conversions": 0},
        {"spend": 1.0, "impressions": 100, "clicks": 1, "conversions": -1},
        {"spend": math.nan, "impressions": 100, "clicks": 1, "conversions": 1},
        {"spend": math.inf, "impressions": 100, "clicks": 1, "conversions": 1},
        # Clicks cannot exceed impressions.
        {"spend": 1.0, "impressions": 10, "clicks": 11, "conversions": 1},
    ],
)
def test_rejects_invalid_inputs(kwargs: dict[str, float | int]) -> None:
    with pytest.raises(InvalidMetricsError):
        calculate_metrics(**kwargs)  # type: ignore[arg-type]


def test_summary_contains_metrics_and_insights() -> None:
    summary = build_campaign_summary(get_campaign("cmp_1002"))

    assert summary.campaign_id == "cmp_1002"
    assert summary.metrics.ctr == 3.0
    assert summary.performance == "Strong"
    assert "Cart Abandoner Retargeting" in summary.summary
    assert len(summary.insights) == 4


def test_summary_flags_underperforming_campaign() -> None:
    summary = build_campaign_summary(get_campaign("cmp_1004"))

    assert summary.performance == "Needs improvement"
    assert "in need of improvement" in summary.summary
    assert any("above the $30.00 target" in insight for insight in summary.insights)


def test_campaign_lookup_is_case_insensitive() -> None:
    campaign = get_campaign("  CMP_1001 ")

    assert campaign.campaign_id == "cmp_1001"
    assert campaign.name == "Summer Sale - Prospecting"


@pytest.mark.parametrize("campaign_id", ["", "   ", "../etc/passwd", "cmp 1001", "x" * 33])
def test_rejects_malformed_campaign_ids(campaign_id: str) -> None:
    with pytest.raises(InvalidCampaignIdError):
        get_campaign(campaign_id)


def test_unknown_campaign_lists_available_ids() -> None:
    with pytest.raises(CampaignNotFoundError, match="Available campaign IDs"):
        get_campaign("cmp_9999")


def test_mock_dataset_is_consistent() -> None:
    campaigns = list_campaigns()

    assert len(campaigns) == 5
    for campaign in campaigns:
        assert campaign.clicks <= campaign.impressions
        assert campaign.conversions <= campaign.clicks
        assert campaign.spend >= 0
