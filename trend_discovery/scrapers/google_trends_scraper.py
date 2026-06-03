"""
Google Trends scraper using pytrends.
Returns normalized 0-100 scores without requiring an API key.
"""
import logging
import random
import time
from typing import Dict, List, Optional

import pandas as pd

from trend_discovery.config import SCRAPER_DELAYS

logger = logging.getLogger(__name__)

try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False
    logger.warning("pytrends not installed. Google Trends scraper will return empty data.")


class GoogleTrendsScraper:
    """Scrapes trend data from Google Trends via pytrends (no API key needed)."""

    def __init__(self, hl: str = "en-US", tz: int = 360):
        self.hl = hl
        self.tz = tz
        self._delays = SCRAPER_DELAYS["google_trends"]
        self._pytrends: Optional[object] = None

    def _get_client(self):
        """Lazily initialize the pytrends client."""
        if not PYTRENDS_AVAILABLE:
            return None
        if self._pytrends is None:
            self._pytrends = TrendReq(hl=self.hl, tz=self.tz, timeout=(10, 25))
        return self._pytrends

    def _sleep(self):
        """Respectful delay between requests."""
        delay = random.uniform(self._delays["min"], self._delays["max"])
        time.sleep(delay)

    def _normalize_series(self, series: pd.Series) -> float:
        """Return the mean of a 0-100 pandas series, or 0 on empty."""
        if series is None or series.empty:
            return 0.0
        return float(series.mean())

    def get_interest_over_time(self, keywords: List[str], timeframe: str = "today 3-m") -> Dict:
        """
        Fetch interest-over-time for a list of keywords (max 5 per pytrends call).

        Returns:
            {
                "keyword": {
                    "mean_score": float,       # 0-100
                    "max_score": float,        # 0-100
                    "last_score": float,       # most recent data point
                    "values": List[float],
                    "timestamps": List[str],
                }
            }
        """
        client = self._get_client()
        if client is None:
            return {}

        result = {}
        # pytrends accepts at most 5 keywords per request
        chunks = [keywords[i:i + 5] for i in range(0, len(keywords), 5)]
        for chunk in chunks:
            try:
                client.build_payload(chunk, timeframe=timeframe)
                self._sleep()
                df = client.interest_over_time()
                if df.empty:
                    continue
                for kw in chunk:
                    if kw in df.columns:
                        series = df[kw]
                        result[kw] = {
                            "mean_score": float(series.mean()),
                            "max_score": float(series.max()),
                            "last_score": float(series.iloc[-1]) if len(series) else 0.0,
                            "values": series.tolist(),
                            "timestamps": [str(ts) for ts in df.index.tolist()],
                        }
            except Exception as exc:
                logger.error("get_interest_over_time error for %s: %s", chunk, exc)
                self._sleep()
        return result

    def get_related_queries(self, keyword: str) -> Dict:
        """
        Fetch rising and top related queries for a single keyword.

        Returns:
            {
                "rising": [{"query": str, "value": str}, ...],
                "top":    [{"query": str, "value": int}, ...],
            }
        """
        client = self._get_client()
        if client is None:
            return {"rising": [], "top": []}

        try:
            client.build_payload([keyword], timeframe="today 3-m")
            self._sleep()
            related = client.related_queries()
            kw_data = related.get(keyword, {})
            rising_df = kw_data.get("rising")
            top_df = kw_data.get("top")
            return {
                "rising": rising_df.to_dict("records") if rising_df is not None else [],
                "top": top_df.to_dict("records") if top_df is not None else [],
            }
        except Exception as exc:
            logger.error("get_related_queries error for '%s': %s", keyword, exc)
            return {"rising": [], "top": []}

    def get_related_topics(self, keyword: str) -> Dict:
        """
        Fetch rising and top related topics for a single keyword.

        Returns:
            {
                "rising": [{"topic_title": str, "topic_type": str, "value": ...}, ...],
                "top":    [...],
            }
        """
        client = self._get_client()
        if client is None:
            return {"rising": [], "top": []}

        try:
            client.build_payload([keyword], timeframe="today 3-m")
            self._sleep()
            topics = client.related_topics()
            kw_data = topics.get(keyword, {})
            rising_df = kw_data.get("rising")
            top_df = kw_data.get("top")
            return {
                "rising": rising_df.to_dict("records") if rising_df is not None else [],
                "top": top_df.to_dict("records") if top_df is not None else [],
            }
        except Exception as exc:
            logger.error("get_related_topics error for '%s': %s", keyword, exc)
            return {"rising": [], "top": []}

    def compare_keywords(self, keywords_list: List[str], timeframe: str = "today 3-m") -> Dict:
        """
        Compare multiple keywords and return their relative interest scores.

        Returns:
            {
                keyword: {"mean": float, "max": float, "last": float}
            }
        """
        data = self.get_interest_over_time(keywords_list, timeframe=timeframe)
        comparison = {}
        for kw, info in data.items():
            comparison[kw] = {
                "mean": info["mean_score"],
                "max": info["max_score"],
                "last": info["last_score"],
            }
        return comparison

    def get_trending_searches(self, pn: str = "united_states") -> List[str]:
        """Return today's trending searches (realtime) as a flat list of strings."""
        client = self._get_client()
        if client is None:
            return []

        try:
            self._sleep()
            df = client.trending_searches(pn=pn)
            return df[0].tolist() if not df.empty else []
        except Exception as exc:
            logger.error("get_trending_searches error: %s", exc)
            return []
