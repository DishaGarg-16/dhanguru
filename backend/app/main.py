from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.models.ticker import TickerSnapshot
from backend.app.services.market_data.simulator import IndianMarketSimulator
from backend.app.services.market_data.store import central_store


simulator = IndianMarketSimulator(update_interval=settings.MOCK_UPDATE_INTERVAL_SEC)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: seed store and start simulator feed
    initial_tickers = await simulator.get_all_tickers()
    for snap in initial_tickers.values():
        central_store.update_ticker(snap)
    central_store.update_benchmark(await simulator.get_benchmark())

    # Start simulation loop updating central store
    async def on_tick(updated_snap: TickerSnapshot):
        central_store.update_ticker(updated_snap)

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
app.include_router(analytics_router)


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
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "provider": settings.MARKET_DATA_PROVIDER,
        "tracked_symbols": len(central_store.get_all_latest()),
    }


@app.get("/api/market/tickers")
async def get_all_tickers():
    """Return all latest ticker snapshots from the central store"""
    return {
        "benchmark": central_store.get_benchmark(),
        "tickers": central_store.get_all_latest(),
    }
