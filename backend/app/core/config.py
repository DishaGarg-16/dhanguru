import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env
env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


class Settings:
    PROJECT_NAME: str = "Dhanguru"
    VERSION: str = "0.1.0"
    DEBUG: bool = os.getenv("DEBUG", "True").lower() in ("true", "1")
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))

    # Market Data
    MARKET_DATA_PROVIDER: str = os.getenv("MARKET_DATA_PROVIDER", "MOCK").upper()
    MOCK_UPDATE_INTERVAL_SEC: float = float(os.getenv("MOCK_UPDATE_INTERVAL_SEC", "1.0"))
    LIVE_POLL_INTERVAL_SEC: float = float(os.getenv("LIVE_POLL_INTERVAL_SEC", "5.0"))

    # Indian Market Constants (IST)
    MARKET_OPEN_HOUR: int = 9
    MARKET_OPEN_MINUTE: int = 15
    MARKET_CLOSE_HOUR: int = 15
    MARKET_CLOSE_MINUTE: int = 30
    DEFAULT_BENCHMARK: str = "NIFTY50"

    # Default Core Universe
    CORE_SYMBOLS: list[str] = [
        "ZOMATO",
        "TRENT",
        "TATAMOTORS",
        "RELIANCE",
        "HDFCBANK",
        "INFY",
        "ITC",
    ]


settings = Settings()
