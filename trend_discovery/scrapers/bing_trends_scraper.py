"""
Bing Trends / Bing Autosuggest scraper.

Bing's autosuggest gives different signals than Google and
helps triangulate demand. Also scrapes Bing News for trending topics.
No API key required for basic usage.
Optional: Bing Search API (free tier: 1000 queries/month).
"""
import json
import logging
import random
import time
from typing import Dict, List, Optional

import requests

from trend_discovery.config import DEFAULT_HEADERS, SCRAPER_DELAYS

logger = logging.getLogger(__name__)

BING_AUTOSUGGEST_URL = "https://api.bing.com/osjson.aspx"
BING_NEWS_TRENDING = "https://www.bing.com/news/search"


class BingTrendsScraper:
    """Collects search volume signals from Bing autocomplete."""

    def __init__(self, bing_api_key: Optional[str] = None):
        self._delays = SCRAPER_DELAYS.get("bing", {"min": 1, "max": 3})
        self._api_key = bing_api_key
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    def _sleep(self):
        time.sleep(random.uniform(self._delays["min"], self._delays["max"]))

    def get_autosuggest(self, query: str, market: str = "en-US") -> List[str]:
        """
        Fetch Bing autosuggest for a query.
        Works without an API key via the public endpoint.
        """
        params = {"query": query, "mkt": market, "form": "EDGEAR"}
        try:
            self._sleep()
            resp = self._session.get(BING_AUTOSUGGEST_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if isinstance(data, list) and len(data) >= 2:
                return [str(s) for s in data[1]]
            return []
        except Exception as exc:
            logger.warning("Bing autosuggest error for '%s': %s", query, exc)
            return []

    def get_pod_suggestions(self, niches: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """Get Bing autosuggest for POD niches."""
        queries = niches or [
            "seamless pattern", "botanical pattern", "cottagecore pattern",
            "mushroom pattern", "celestial pattern", "gothic pattern",
            "vintage pattern", "geometric pattern", "art nouveau pattern",
        ]
        results: Dict[str, List[str]] = {}
        for q in queries:
            suggestions = self.get_autosuggest(q)
            if suggestions:
                results[q] = suggestions
        return results

    def get_trending_news_topics(self, category: str = "art_design") -> List[str]:
        """
        Fetch trending news topics — art/design news indicates
        emerging aesthetic movements.
        """
        params = {"q": "pattern design trends OR surface design trends", "format": "RSS"}
        try:
            self._sleep()
            resp = self._session.get(BING_NEWS_TRENDING, params=params, timeout=15)
            resp.raise_for_status()
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "lxml-xml")
            titles = [item.title.get_text() for item in soup.find_all("item")[:20]]
            return titles
        except Exception as exc:
            logger.warning("Bing news trending error: %s", exc)
            return []
