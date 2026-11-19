"""FastAPI endpoint tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_service_info() -> None:
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["mcp_endpoint"] == "/mcp"
    assert "campaign_summary" in body["tools"]


def test_health_check() -> None:
    assert client.get("/healthz").json() == {"status": "ok"}


def test_lists_campaigns() -> None:
    response = client.get("/api/campaigns")

    assert response.status_code == 200
    campaigns = response.json()
    assert len(campaigns) == 5
    assert campaigns[0]["campaign_id"] == "cmp_1001"
    assert "spend" in campaigns[0]


def test_reads_one_campaign() -> None:
    response = client.get("/api/campaigns/cmp_1001")

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Summer Sale - Prospecting"
    assert body["clicks"] == 18_750


def test_unknown_campaign_returns_404() -> None:
    response = client.get("/api/campaigns/cmp_9999")

    assert response.status_code == 404
    assert "not found" in response.json()["detail"]


def test_malformed_campaign_id_returns_422() -> None:
    response = client.get("/api/campaigns/bad%20id")

    assert response.status_code == 422
    assert "Campaign ID" in response.json()["detail"]


def test_calculates_metrics() -> None:
    response = client.post(
        "/api/metrics/calculate",
        json={
            "spend": 1000,
            "impressions": 100_000,
            "clicks": 2000,
            "conversions": 40,
        },
    )

    assert response.status_code == 200
    assert response.json() == {
        "ctr": 2.0,
        "cpc": 0.5,
        "cpa": 25.0,
        "cpm": 10.0,
    }


def test_zero_denominators_serialize_as_null() -> None:
    response = client.post(
        "/api/metrics/calculate",
        json={"spend": 0, "impressions": 0, "clicks": 0, "conversions": 0},
    )

    assert response.status_code == 200
    assert response.json() == {"ctr": None, "cpc": None, "cpa": None, "cpm": None}


def test_rejects_inconsistent_metrics() -> None:
    response = client.post(
        "/api/metrics/calculate",
        json={"spend": 100, "impressions": 10, "clicks": 11, "conversions": 1},
    )

    assert response.status_code == 422


def test_campaign_summary() -> None:
    response = client.get("/api/campaigns/cmp_1002/summary")

    assert response.status_code == 200
    body = response.json()
    assert body["performance"] == "Strong"
    assert body["metrics"]["cpa"] == 6.25
    assert len(body["insights"]) == 4


def test_openapi_docs_are_available() -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    paths = response.json()["paths"]
    assert "/api/campaigns/{campaign_id}/summary" in paths
    assert "/api/metrics/calculate" in paths
