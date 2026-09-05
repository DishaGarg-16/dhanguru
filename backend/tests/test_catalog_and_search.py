import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.market_data.catalog import stock_catalog, NSE_SECTOR_CATALOG
from backend.app.services.market_data.store import central_store
from backend.app.services.watchlist.store import watchlist_store


@pytest.fixture
def client():
    return TestClient(app)


def test_catalog_categories_and_curated():
    categories = stock_catalog.get_categories()
    assert "NIFTY 50" in categories
    assert "Automobile" in categories
    assert "Banking & Finance" in categories
    assert "Information Technology" in categories

    auto_stocks = stock_catalog.get_curated_stocks("Automobile")
    symbols = [s["symbol"] for s in auto_stocks]
    assert "M&M" in symbols
    assert "MARUTI" in symbols
    assert "TATAMOTORS" in symbols

    all_stocks = stock_catalog.get_curated_stocks()
    assert len(all_stocks) > 30


@pytest.mark.asyncio
async def test_catalog_search_local_match():
    # Search for "mahi" should match Mahindra & Mahindra
    results = await stock_catalog.search_stocks("mahi")
    symbols = [r["symbol"] for r in results]
    assert "M&M" in symbols

    # Search for "tcs"
    results_tcs = await stock_catalog.search_stocks("tcs")
    symbols_tcs = [r["symbol"] for r in results_tcs]
    assert "TCS" in symbols_tcs


@pytest.mark.asyncio
async def test_catalog_search_yahoo_api_integration():
    mock_yahoo_data = {
        "quotes": [
            {
                "symbol": "MAHINDCIE.NS",
                "shortname": "CIE AUTOMOTIVE INDIA",
                "sector": "Auto Components",
                "quoteType": "EQUITY",
            },
            {
                "symbol": "AAPL",
                "shortname": "Apple Inc.",
                "quoteType": "EQUITY",
            },
            {
                "symbol": "MHRIL.BO",
                "shortname": "Mahindra Holidays & Resorts",
                "sector": "Hospitality",
                "quoteType": "EQUITY",
            },
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = mock_yahoo_data

    mock_client = AsyncMock()
    mock_client.get.return_value = mock_resp

    with patch.object(stock_catalog, "_get_client", AsyncMock(return_value=mock_client)):
        results = await stock_catalog.search_stocks("mahind")

    symbols = [r["symbol"] for r in results]
    # Local match M&M should be there
    assert "M&M" in symbols
    # External NSE quote MAHINDCIE should be included (stripped of .NS)
    assert "MAHINDCIE" in symbols
    # External BSE quote MHRIL should be included
    assert "MHRIL" in symbols
    # AAPL (US stock) should be filtered out
    assert "AAPL" not in symbols


def test_api_stocks_endpoints(client):
    # 1. Categories endpoint
    resp = client.get("/api/stocks/categories")
    assert resp.status_code == 200
    data = resp.json()
    assert "categories" in data
    assert "NIFTY 50" in data["categories"]

    # 2. Curated endpoint
    resp_curated = client.get("/api/stocks/curated?category=Automobile")
    assert resp_curated.status_code == 200
    curated_data = resp_curated.json()
    assert curated_data["category"] == "Automobile"
    assert any(s["symbol"] == "M&M" for s in curated_data["stocks"])

    # 3. Search endpoint
    resp_search = client.get("/api/stocks/search?q=mahi")
    assert resp_search.status_code == 200
    search_data = resp_search.json()
    assert search_data["count"] >= 1
    assert any(s["symbol"] == "M&M" for s in search_data["results"])


def test_dynamic_watchlist_add_symbol(client):
    # Add a stock not originally in SEED_UNIVERSE
    test_sym = "TCS"
    resp = client.post("/api/watchlist/symbols", json={"symbol": test_sym})
    assert resp.status_code == 200
    data = resp.json()
    assert test_sym in data["symbols"]

    # Verify central_store now holds the snapshot
    snap = central_store.get_latest(test_sym)
    assert snap is not None
    assert snap.symbol == test_sym


def test_symbol_sanitization_rejects_malicious_characters(client):
    # Reject XSS or script tags
    resp = client.post("/api/watchlist/symbols", json={"symbol": "<script>alert(1)</script>"})
    assert resp.status_code == 422

    # Reject whitespace or SQL chars
    resp2 = client.post("/api/watchlist/symbols", json={"symbol": "DROP TABLE;"})
    assert resp2.status_code == 422


def test_search_query_max_length_constrained(client):
    # Over 50 chars should be rejected by validation
    resp = client.get(f"/api/stocks/search?q={'A' * 60}")
    assert resp.status_code == 422


def test_bot_throttle_sliding_window(client):
    # Mock register_symbol so test doesn't hammer Yahoo Finance over internet
    with patch("backend.app.services.market_data.factory.get_market_provider") as mock_get_provider:
        mock_provider = AsyncMock()
        mock_snap = MagicMock(symbol="TEST")
        mock_provider.register_symbol.return_value = mock_snap
        mock_get_provider.return_value = mock_provider

        # Rapidly adding 20 symbols
        for i in range(20):
            resp = client.post("/api/watchlist/symbols?user_id=test_bot", json={"symbol": f"SYM{i}"})
            assert resp.status_code == 200

        # 21st addition triggers 429 Too Many Requests
        blocked_resp = client.post("/api/watchlist/symbols?user_id=test_bot", json={"symbol": "SYM_OVERFLOW"})
        assert blocked_resp.status_code == 429
        assert "Too many symbols" in blocked_resp.json()["detail"]
