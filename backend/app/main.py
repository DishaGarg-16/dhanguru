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
