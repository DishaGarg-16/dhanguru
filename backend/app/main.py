from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.models.ticker import TickerSnapshot
from backend.app.services.market_data.factory import get_market_provider
from backend.app.services.market_data.store import central_store


# Instantiate configured provider (MOCK, LIVE, or AUTO hybrid)
simulator = get_market_provider()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed store and start simulator feed
    initial_tickers = await simulator.get_all_tickers()
    for snap in initial_tickers.values():
        central_store.update_ticker(snap)
    central_store.update_benchmark(await simulator.get_benchmark())

    # Start simulation loop updating central store and broadcasting to WebSockets
    from backend.app.api.stream import stream_manager
    from backend.app.services.analytics.anomaly_detector import AnomalyDetector

    async def on_tick(updated_snap: TickerSnapshot):
        accepted = central_store.update_ticker(updated_snap)
        if not accepted:
            return

        try:
            bench = central_store.get_benchmark()
            eval_res = AnomalyDetector.evaluate(updated_snap, bench)
            await stream_manager.broadcast({
                "type": "TICK_UPDATE",
                "ticker": updated_snap.model_dump(mode="json"),
                "anomaly": eval_res.model_dump(mode="json"),
                "benchmark": bench.model_dump(mode="json") if bench else None,
            })
        except Exception:
            pass

    await simulator.start(on_tick_callback=on_tick)
    yield
    # Shutdown: stop simulator
    await simulator.stop()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    lifespan=lifespan,
)

# Enable CORS for local React/Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

import time
from collections import defaultdict, deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class InMemoryRateLimiterMiddleware(BaseHTTPMiddleware):
    """
    Lightweight in-memory IP rate limiter to protect public endpoints
    from automated abuse and DoS floods without external dependencies.
    """

    def __init__(self, app, max_requests: int = 120, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.clients: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        # Only rate-limit API routes (/api/*) - do not throttle WebSockets, static assets, or health checks
        if not path.startswith("/api/"):
            return await call_next(request)

        # Respect proxy/Railway client IP headers
        client_ip = request.headers.get("x-forwarded-for")
        if client_ip:
            client_ip = client_ip.split(",")[0].strip()
        else:
            client_ip = request.client.host if request.client else "unknown"

        now = time.time()
        queue = self.clients[client_ip]

        # Prune old timestamps
        while queue and queue[0] <= now - self.window_seconds:
            queue.popleft()

        if len(queue) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Rate limit is 120 requests per minute."},
                headers={"Retry-After": "5"},
            )

        queue.append(now)
        return await call_next(request)


app.add_middleware(InMemoryRateLimiterMiddleware, max_requests=120, window_seconds=60)


# Register API Routers
from backend.app.api.analytics import router as analytics_router
from backend.app.api.watchlist import router as watchlist_router
from backend.app.api.briefing import router as briefing_router
from backend.app.api.stream import router as stream_router
from backend.app.api.stocks import router as stocks_router

app.include_router(analytics_router)
app.include_router(watchlist_router)
app.include_router(briefing_router)
app.include_router(stream_router)
app.include_router(stocks_router)


import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Static frontend assets integration for single-container cloud deployment
_frontend_dist_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist"))

if os.path.isdir(_frontend_dist_dir):
    _assets_dir = os.path.join(_frontend_dist_dir, "assets")
    if os.path.isdir(_assets_dir):
        app.mount("/assets", StaticFiles(directory=_assets_dir), name="assets")

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(_frontend_dist_dir, "index.html"))
else:
    @app.get("/")
    async def root():
        return {
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "docs_url": "/docs",
            "health_url": "/health",
            "tickers_url": "/api/market/tickers",
        }



@app.get("/health")
async def health_check():
    from backend.app.core.schedule import MarketScheduleManager
    active_submode = getattr(simulator, "active_mode", settings.MARKET_DATA_PROVIDER)
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "provider": settings.MARKET_DATA_PROVIDER,
        "active_feed": active_submode,
        "session_status": MarketScheduleManager.get_session_status(),
        "is_market_open": MarketScheduleManager.is_market_open(),
        "is_store_frozen": central_store.is_frozen,
        "tracked_symbols": len(central_store.get_all_latest()),
    }


@app.get("/api/market/tickers")
async def get_all_tickers():
    """Return all latest ticker snapshots from the central store"""
    return {
        "benchmark": central_store.get_benchmark(),
        "tickers": central_store.get_all_latest(),
    }


if os.path.isdir(_frontend_dist_dir):
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        if full_path.startswith(("api/", "ws/", "health", "docs", "redoc", "openapi.json")):
            return {"detail": "Not Found"}
        target_path = os.path.join(_frontend_dist_dir, full_path)
        if os.path.isfile(target_path):
            return FileResponse(target_path)
        return FileResponse(os.path.join(_frontend_dist_dir, "index.html"))



