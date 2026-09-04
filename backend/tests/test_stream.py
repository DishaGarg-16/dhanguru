import json
import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.api.stream import get_market_session_status


def test_market_session_status_ist():
    """Verify market session status computes correct IST time and valid phase"""
    session = get_market_session_status()
    assert "status" in session
    assert "ist_time" in session
    assert "is_open" in session
    assert session["status"] in ("LIVE", "CLOSED", "PRE_MARKET")


def test_websocket_live_stream_initial_handshake():
    """Verify WebSocket client can connect to /ws/live and receive initial snapshot"""
    client = TestClient(app)
    with client.websocket_connect("/ws/live") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "INITIAL_SNAPSHOT"
        assert "session" in data
        assert "tickers" in data
        assert "benchmark" in data


def test_demo_anomaly_trigger_endpoint():
    """Verify test anomaly simulation trigger endpoint functions properly"""
    client = TestClient(app)
    resp = client.post("/api/market/simulate/trigger?symbol=ZOMATO&anomaly_type=SURGE")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["symbol"] == "ZOMATO"
    assert "urgency_score" in data
    assert data["urgency_score"] >= 60  # Surge must trigger elevated attention
