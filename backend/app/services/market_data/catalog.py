import logging
from typing import Optional
import httpx

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
}

# Curated catalog of marquee Indian stocks across key sectors & indices
NSE_SECTOR_CATALOG: dict[str, list[dict[str, str]]] = {
    "NIFTY 50": [
        {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "sector": "Energy & Retail"},
        {"symbol": "TCS", "name": "Tata Consultancy Services Ltd", "sector": "Information Technology"},
        {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "sector": "Banking & Finance"},
        {"symbol": "INFY", "name": "Infosys Ltd", "sector": "Information Technology"},
        {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "sector": "Banking & Finance"},
        {"symbol": "ITC", "name": "ITC Ltd", "sector": "FMCG & Conglomerate"},
        {"symbol": "BHARTIARTL", "name": "Bharti Airtel Ltd", "sector": "Telecommunications"},
        {"symbol": "SBIN", "name": "State Bank of India", "sector": "Banking & Finance"},
        {"symbol": "LT", "name": "Larsen & Toubro Ltd", "sector": "Engineering & Infra"},
        {"symbol": "HINDUNILVR", "name": "Hindustan Unilever Ltd", "sector": "FMCG"},
        {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank Ltd", "sector": "Banking & Finance"},
        {"symbol": "AXISBANK", "name": "Axis Bank Ltd", "sector": "Banking & Finance"},
        {"symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd", "sector": "Financial Services"},
        {"symbol": "MARUTI", "name": "Maruti Suzuki India Ltd", "sector": "Automobile"},
        {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical Industries Ltd", "sector": "Pharma"},
        {"symbol": "TITAN", "name": "Titan Company Ltd", "sector": "Consumer Goods & Jewelry"},
    ],
    "Automobile": [
        {"symbol": "TATAMOTORS", "name": "Tata Motors Passenger Vehicles Ltd", "sector": "Automobile"},
        {"symbol": "M&M", "name": "Mahindra & Mahindra Ltd", "sector": "Automobile"},
        {"symbol": "MARUTI", "name": "Maruti Suzuki India Ltd", "sector": "Automobile"},
        {"symbol": "BAJAJ-AUTO", "name": "Bajaj Auto Ltd", "sector": "Automobile"},
        {"symbol": "HEROMOTOCO", "name": "Hero MotoCorp Ltd", "sector": "Automobile"},
        {"symbol": "EICHERMOT", "name": "Eicher Motors Ltd", "sector": "Automobile"},
        {"symbol": "TVSMOTOR", "name": "TVS Motor Company Ltd", "sector": "Automobile"},
        {"symbol": "MOTHERSON", "name": "Samvardhana Motherson International", "sector": "Auto Components"},
        {"symbol": "BOSCHLTD", "name": "Bosch Ltd", "sector": "Auto Components"},
    ],
    "Banking & Finance": [
        {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "sector": "Banking & Finance"},
        {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "sector": "Banking & Finance"},
        {"symbol": "SBIN", "name": "State Bank of India", "sector": "Banking & Finance"},
        {"symbol": "KOTAKBANK", "name": "Kotak Mahindra Bank Ltd", "sector": "Banking & Finance"},
        {"symbol": "AXISBANK", "name": "Axis Bank Ltd", "sector": "Banking & Finance"},
        {"symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd", "sector": "Financial Services"},
        {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv Ltd", "sector": "Financial Services"},
        {"symbol": "INDUSINDBK", "name": "IndusInd Bank Ltd", "sector": "Banking & Finance"},
        {"symbol": "BANKBARODA", "name": "Bank of Baroda", "sector": "Banking & Finance"},
        {"symbol": "CHOLAFIN", "name": "Cholamandalam Investment", "sector": "Financial Services"},
    ],
    "Information Technology": [
        {"symbol": "TCS", "name": "Tata Consultancy Services Ltd", "sector": "Information Technology"},
        {"symbol": "INFY", "name": "Infosys Ltd", "sector": "Information Technology"},
        {"symbol": "HCLTECH", "name": "HCL Technologies Ltd", "sector": "Information Technology"},
        {"symbol": "WIPRO", "name": "Wipro Ltd", "sector": "Information Technology"},
        {"symbol": "TECHM", "name": "Tech Mahindra Ltd", "sector": "Information Technology"},
        {"symbol": "LTIM", "name": "LTIMindtree Ltd", "sector": "Information Technology"},
        {"symbol": "PERSISTENT", "name": "Persistent Systems Ltd", "sector": "Information Technology"},
        {"symbol": "COFORGE", "name": "Coforge Ltd", "sector": "Information Technology"},
    ],
    "FMCG & Retail": [
        {"symbol": "ITC", "name": "ITC Ltd", "sector": "FMCG & Conglomerate"},
        {"symbol": "HINDUNILVR", "name": "Hindustan Unilever Ltd", "sector": "FMCG"},
        {"symbol": "NESTLEIND", "name": "Nestle India Ltd", "sector": "FMCG"},
        {"symbol": "BRITANNIA", "name": "Britannia Industries Ltd", "sector": "FMCG"},
        {"symbol": "TRENT", "name": "Trent Ltd (Tata Retail)", "sector": "Retail & Fashion"},
        {"symbol": "DMART", "name": "Avenue Supermarts Ltd (DMart)", "sector": "Retail"},
        {"symbol": "TATACONSUM", "name": "Tata Consumer Products Ltd", "sector": "FMCG"},
        {"symbol": "DABUR", "name": "Dabur India Ltd", "sector": "FMCG"},
        {"symbol": "GODREJCP", "name": "Godrej Consumer Products Ltd", "sector": "FMCG"},
    ],
    "Energy & Metals": [
        {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "sector": "Energy & Retail"},
        {"symbol": "ONGC", "name": "Oil & Natural Gas Corporation Ltd", "sector": "Energy"},
        {"symbol": "NTPC", "name": "NTPC Ltd", "sector": "Power & Energy"},
        {"symbol": "POWERGRID", "name": "Power Grid Corporation of India", "sector": "Power & Energy"},
        {"symbol": "TATASTEEL", "name": "Tata Steel Ltd", "sector": "Metals & Mining"},
        {"symbol": "JSWSTEEL", "name": "JSW Steel Ltd", "sector": "Metals & Mining"},
        {"symbol": "COALINDIA", "name": "Coal India Ltd", "sector": "Metals & Mining"},
        {"symbol": "HINDALCO", "name": "Hindalco Industries Ltd", "sector": "Metals & Mining"},
        {"symbol": "ADANIENT", "name": "Adani Enterprises Ltd", "sector": "Commodities & Energy"},
    ],
    "Pharma & Healthcare": [
        {"symbol": "SUNPHARMA", "name": "Sun Pharmaceutical Industries Ltd", "sector": "Pharmaceuticals"},
        {"symbol": "CIPLA", "name": "Cipla Ltd", "sector": "Pharmaceuticals"},
        {"symbol": "DRREDDY", "name": "Dr. Reddy's Laboratories Ltd", "sector": "Pharmaceuticals"},
        {"symbol": "APOLLOHOSP", "name": "Apollo Hospitals Enterprise Ltd", "sector": "Healthcare"},
        {"symbol": "DIVISLAB", "name": "Divi's Laboratories Ltd", "sector": "Pharmaceuticals"},
        {"symbol": "MANKIND", "name": "Mankind Pharma Ltd", "sector": "Pharmaceuticals"},
        {"symbol": "TORNTPHARM", "name": "Torrent Pharmaceuticals Ltd", "sector": "Pharmaceuticals"},
    ],
    "Consumer Internet": [
        {"symbol": "ZOMATO", "name": "Eternal Ltd (Zomato / Blinkit)", "sector": "Consumer Internet"},
        {"symbol": "ETERNAL", "name": "Eternal Ltd (Zomato)", "sector": "Consumer Internet"},
        {"symbol": "NAUKRI", "name": "Info Edge (India) Ltd (Naukri)", "sector": "Consumer Internet"},
        {"symbol": "NYKAA", "name": "FSN E-Commerce Ventures (Nykaa)", "sector": "Consumer Internet"},
        {"symbol": "POLICYBZR", "name": "PB Fintech Ltd (PolicyBazaar)", "sector": "Fintech"},
        {"symbol": "PAYTM", "name": "One97 Communications Ltd (Paytm)", "sector": "Fintech"},
        {"symbol": "DELHIVERY", "name": "Delhivery Ltd", "sector": "Logistics & Supply Chain"},
    ],
}


class StockCatalogService:
    """Service providing categorized stock lists and dynamic Yahoo search for Indian equities"""

    def __init__(self):
        self._http_client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._http_client is None or self._http_client.is_closed:
            self._http_client = httpx.AsyncClient(timeout=6.0, headers=HEADERS)
        return self._http_client

    def get_categories(self) -> dict[str, list[dict[str, str]]]:
        """Return all categorized stock lists for exploration"""
        return NSE_SECTOR_CATALOG

    def get_curated_stocks(self, category: Optional[str] = None) -> list[dict[str, str]]:
        """Return stocks for a specific sector category, or all unique curated stocks"""
        if category and category in NSE_SECTOR_CATALOG:
            return NSE_SECTOR_CATALOG[category]

        # Flatten all unique stocks
        seen_symbols = set()
        all_stocks = []
        for cat_stocks in NSE_SECTOR_CATALOG.values():
            for item in cat_stocks:
                if item["symbol"] not in seen_symbols:
                    seen_symbols.add(item["symbol"])
                    all_stocks.append(item)
        return all_stocks

    async def search_stocks(self, query: str) -> list[dict[str, str]]:
        """
        Search for Indian stocks using:
        1. Exact and partial matches from the curated catalog.
        2. Dynamic Yahoo Finance autocomplete search for any of the 2,000+ Indian equities.
        """
        q = query.strip().upper()
        if not q:
            return self.get_curated_stocks("NIFTY 50")

        results: list[dict[str, str]] = []
        seen: set[str] = set()

        # 1. Search local curated catalog
        all_curated = self.get_curated_stocks()
        for item in all_curated:
            sym = item["symbol"].upper()
            name = item["name"].upper()
            sector = item["sector"].upper()
            if q in sym or q in name or q in sector:
                results.append(item)
                seen.add(sym)

        # 2. Query Yahoo Finance search endpoint if query is between 2 and 50 chars
        if 2 <= len(q) <= 50:
            try:
                client = await self._get_client()
                url = "https://query2.finance.yahoo.com/v1/finance/search"
                params = {
                    "q": query.strip()[:50],
                    "quotesCount": 15,
                    "newsCount": 0,
                }
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    data = resp.json()
                    quotes = data.get("quotes", [])
                    for quote in quotes:
                        raw_sym = quote.get("symbol", "")
                        # Filter strictly for Indian market listings
                        if raw_sym.endswith(".NS") or raw_sym.endswith(".BO"):
                            clean_sym = raw_sym.replace(".NS", "").replace(".BO", "").upper()
                            if clean_sym not in seen:
                                name = quote.get("shortname") or quote.get("longname") or clean_sym
                                sector = quote.get("sector") or quote.get("industry") or "Indian Equity"
                                exchange = "NSE" if raw_sym.endswith(".NS") else "BSE"
                                results.append({
                                    "symbol": clean_sym,
                                    "name": name,
                                    "sector": sector,
                                    "exchange": exchange,
                                })
                                seen.add(clean_sym)
            except Exception as e:
                logger.debug("Live Yahoo search failed for query %s: %s", query, e)

        return results


# Global singleton instance
stock_catalog = StockCatalogService()
