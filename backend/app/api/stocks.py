from typing import Optional
from fastapi import APIRouter, Query
from backend.app.services.market_data.catalog import stock_catalog

router = APIRouter(prefix="/api/stocks", tags=["stocks"])


@router.get("/search")
async def search_stocks(q: str = Query(default="", max_length=50, description="Search symbol, company name, or sector")):
    """Typeahead search matching curated catalog and live Yahoo Finance search"""
    results = await stock_catalog.search_stocks(q)
    return {
        "query": q,
        "count": len(results),
        "results": results,
    }


@router.get("/categories")
async def get_categories():
    """Return all stock categories and sector groupings for zero-typing exploration"""
    return {
        "categories": stock_catalog.get_categories()
    }


@router.get("/curated")
async def get_curated_stocks(category: Optional[str] = Query(default=None, description="Optional sector filter")):
    """Return curated stocks for a category, or all curated stocks if no category specified"""
    stocks = stock_catalog.get_curated_stocks(category)
    return {
        "category": category or "ALL",
        "count": len(stocks),
        "stocks": stocks,
    }
