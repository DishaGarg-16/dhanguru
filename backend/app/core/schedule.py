from datetime import datetime, date, time, timedelta, timezone
from typing import Optional

try:
    import zoneinfo
    IST_TZ = zoneinfo.ZoneInfo("Asia/Kolkata")
except Exception:
    IST_TZ = timezone(timedelta(hours=5, minutes=30))


class MarketScheduleManager:
    """
    Manages Indian equity market (NSE/BSE) trading hours and weekly session cycles
    based on Indian Standard Time (IST).

    Session definitions:
    - Monday - Friday:
      - 00:00 - 09:00 IST: PRE_MARKET
      - 09:00 - 09:15 IST: PRE_OPEN (NSE auction & discovery)
      - 09:15 - 15:30 IST: OPEN (Regular trading session)
      - 15:30 - 16:00 IST: POST_MARKET_CLOSING (Closing price discovery)
      - 16:00 - 23:59 IST: POST_MARKET_CLOSED
    - Saturday - Sunday:
      - WEEKEND (Exchanges closed)
    """

    # NSE Trading Session Times (IST)
    PRE_OPEN_START = time(9, 0)
    PRE_OPEN_END = time(9, 15)
    MARKET_OPEN = time(9, 15)
    MARKET_CLOSE = time(15, 30)
    POST_MARKET_CLOSE = time(16, 0)

    @classmethod
    def get_ist_now(cls) -> datetime:
        """Return current datetime localized to IST (Asia/Kolkata)"""
        return datetime.now(IST_TZ)

    @classmethod
    def is_trading_day(cls, dt: Optional[datetime] = None) -> bool:
        """Check if date is a standard Indian trading weekday (Monday - Friday)"""
        target = dt or cls.get_ist_now()
        # Monday is 0, Friday is 4, Saturday is 5, Sunday is 6
        return target.weekday() < 5

    @classmethod
    def get_session_status(cls, dt: Optional[datetime] = None) -> str:
        """
        Determine the current market session status based on IST clock and day of week:
        - "OPEN": Regular trading session (09:15 - 15:30 IST, Mon - Fri)
        - "PRE_OPEN": Pre-market auction session (09:00 - 09:15 IST, Mon - Fri)
        - "PRE_MARKET": Prior to 09:00 IST on a trading weekday
        - "POST_MARKET_CLOSING": 15:30 - 16:00 IST closing price determination
        - "POST_MARKET_CLOSED": After 16:00 IST until next trading day
        - "WEEKEND": Saturday or Sunday
        """
        target = dt or cls.get_ist_now()

        if target.weekday() >= 5:
            return "WEEKEND"

        current_time = target.time()

        if current_time < cls.PRE_OPEN_START:
            return "PRE_MARKET"
        elif current_time < cls.PRE_OPEN_END:
            return "PRE_OPEN"
        elif current_time < cls.MARKET_CLOSE:
            return "OPEN"
        elif current_time < cls.POST_MARKET_CLOSE:
            return "POST_MARKET_CLOSING"
        else:
            return "POST_MARKET_CLOSED"

    @classmethod
    def is_market_open(cls, dt: Optional[datetime] = None) -> bool:
        """Return True only if regular market trading is actively running"""
        return cls.get_session_status(dt) == "OPEN"

    @classmethod
    def get_last_market_close(cls, dt: Optional[datetime] = None) -> datetime:
        """
        Return the datetime of the most recent 15:30 IST market close.
        If called during a trading day before 15:30, returns previous trading day's close.
        """
        target = dt or cls.get_ist_now()
        cur_date = target.date()

        # If today is a weekday and time is already past 15:30, today's close is latest
        if cls.is_trading_day(target) and target.time() >= cls.MARKET_CLOSE:
            return datetime.combine(cur_date, cls.MARKET_CLOSE, tzinfo=target.tzinfo or IST_TZ)

        # Otherwise look backwards for the preceding trading weekday
        prev_date = cur_date - timedelta(days=1)
        while True:
            candidate_dt = datetime.combine(prev_date, cls.MARKET_CLOSE, tzinfo=target.tzinfo or IST_TZ)
            if cls.is_trading_day(candidate_dt):
                return candidate_dt
            prev_date -= timedelta(days=1)

    @classmethod
    def get_next_market_open(cls, dt: Optional[datetime] = None) -> datetime:
        """
        Return the datetime of the next upcoming 09:15 IST market open.
        """
        target = dt or cls.get_ist_now()
        cur_date = target.date()

        # If today is a weekday and time is before 09:15, today's open is next
        if cls.is_trading_day(target) and target.time() < cls.MARKET_OPEN:
            return datetime.combine(cur_date, cls.MARKET_OPEN, tzinfo=target.tzinfo or IST_TZ)

        # Otherwise advance to find the next trading weekday
        next_date = cur_date + timedelta(days=1)
        while True:
            candidate_dt = datetime.combine(next_date, cls.MARKET_OPEN, tzinfo=target.tzinfo or IST_TZ)
            if cls.is_trading_day(candidate_dt):
                return candidate_dt
            next_date += timedelta(days=1)
