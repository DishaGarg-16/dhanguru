import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import List, Literal
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from backend.app.models.ticker import TickerSnapshot
from backend.app.services.market_data.store import central_store
from backend.app.services.market_data.simulator import IndianMarketSimulator

router = APIRouter(tags=["streaming"])

# IST Timezone (UTC + 5:30)
IST_TZ = timezone(timedelta(hours=5, minutes=30))


def get_market_session_status() -> dict:
    """Determine current Indian Market session phase (IST 9:15 AM - 3:30 PM, Mon-Fri)"""
    now_ist = datetime.now(IST_TZ)
    weekday = now_ist.weekday()  # 0=Monday, 4=Friday, 5=Saturday, 6=Sunday

    if weekday >= 5:
        return {
            "status": "CLOSED",
            "reason": "Weekend (Markets Closed)",
            "ist_time": now_ist.strftime("%H:%M:%S IST"),
            "is_open": False,
        }

    hour = now_ist.hour
    minute = now_ist.minute
    total_minutes = hour * 60 + minute

    # 9:00 - 9:15 Pre-market
    if 9 * 60 <= total_minutes < 9 * 60 + 15:
        return {
            "status": "PRE_MARKET",
            "reason": "Pre-Market Session (09:00 - 09:15 IST)",
            "ist_time": now_ist.strftime("%H:%M:%S IST"),
            "is_open": False,
        }
    # 9:15 - 15:30 Normal Live Trading
    elif 9 * 60 + 15 <= total_minutes <= 15 * 60 + 30:
        return {
            "status": "LIVE",
            "reason": "Normal Market Hours (09:15 - 15:30 IST)",
            "ist_time": now_ist.strftime("%H:%M:%S IST"),
            "is_open": True,
        }
    else:
        return {
            "status": "CLOSED",
            "reason": "Post-Market Hours (Closes at 15:30 IST)",
            "ist_time": now_ist.strftime("%H:%M:%S IST"),
            "is_open": False,
        }


class ConnectionManager:
    """Manages active client WebSocket connections and tick broadcasts"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return

        payload = json.dumps(message, default=str)
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(payload)
            except Exception:
                dead_connections.append(connection)

        for dead in dead_connections:
            self.disconnect(dead)


stream_manager = ConnectionManager()


@router.websocket("/ws/live")
async def websocket_endpoint(websocket: WebSocket):
    """
    Real-time WebSocket connection for streaming live Indian market ticks
    and attention alerts to connected clients.
    """
    await stream_manager.connect(websocket)
    try:
        # Send initial snapshot upon connection
        bench = central_store.get_benchmark()
        initial_data = {
            "type": "INITIAL_SNAPSHOT",
            "session": get_market_session_status(),
            "benchmark": bench.model_dump(mode="json") if bench else None,
            "tickers": {
                sym: t.model_dump(mode="json")
                for sym, t in central_store.get_all_latest().items()
            },
        }
        await websocket.send_text(json.dumps(initial_data, default=str))

        # Keep connection open for client heartbeats or messages
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        stream_manager.disconnect(websocket)
    except Exception:
        stream_manager.disconnect(websocket)


@router.get("/api/market/session")
async def get_session_info():
    """Get Indian market session phase (LIVE, CLOSED, PRE_MARKET)"""
    return get_market_session_status()


@router.post("/api/market/simulate/trigger")
async def trigger_test_anomaly(
    symbol: str,
    anomaly_type: Literal["SURGE", "CIRCUIT_APPROACH", "BREAKOUT_52W"] = "SURGE",
):
    """
    Demo / Testing endpoint: Force-trigger a market anomaly on demand
    so evaluators can witness live real-time detection immediately.
    """
    from backend.app.main import simulator
    from backend.app.services.analytics.anomaly_detector import AnomalyDetector

    sym = symbol.upper()
    if sym not in simulator._tickers:
        return {"error": f"Symbol {sym} not found"}

    if anomaly_type == "CIRCUIT_APPROACH":
        updated_snap = simulator.trigger_circuit_approach(sym, upper=True)
    elif anomaly_type == "BREAKOUT_52W":
        updated_snap = simulator.trigger_52w_breakout(sym)
    else:
        updated_snap = simulator.trigger_volume_surge(sym, multiplier=3.4)

    # Store and broadcast to all connected WebSocket clients
    central_store.update_ticker(updated_snap)
    bench = central_store.get_benchmark()
    eval_res = AnomalyDetector.evaluate(updated_snap, bench)

    await stream_manager.broadcast(
        {
            "type": "TICK_UPDATE",
            "ticker": updated_snap.model_dump(mode="json"),
            "anomaly": eval_res.model_dump(mode="json"),
            "benchmark": bench.model_dump(mode="json") if bench else None,
        }
    )

    return {
        "status": "success",
        "symbol": sym,
        "anomaly_type": anomaly_type,
        "urgency_score": eval_res.urgency_score,
        "signals": eval_res.signals,
    }
