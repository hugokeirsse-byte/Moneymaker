"""
Pinterest scraper — trending topics, popular search suggestions, viral pins.

Pinterest is a gold mine for visual trend detection in POD.
Uses the public autocomplete/suggest API (no key needed) and
trends page scraping. Falls back to Pinterest API if credentials are provided.
"""
import json
import logging
import random
import time
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from trend_discovery.config import DEFAULT_HEADERS, SCRAPER_DELAYS

logger = logging.getLogger(__name__)

PINTEREST_BASE = "https://www.pinterest.com"
PINTEREST_SUGGEST_URL = "https://www.pinterest.com/resource/SearchBoxSuggestionsResource/get/"


class PinterestScraper:
    """
    Extracts trend signals from Pinterest:
    - Autocomplete suggestions (no API key)
    - Trending topics from Pinterest Trends page
    - Popular search terms in relevant categories
    """

    def __init__(self):
        self._delays = SCRAPER_DELAYS.get("pinterest", {"min": 3, "max": 7})
        self._session = requests.Session()
        self._session.headers.update({
            **DEFAULT_HEADERS,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://www.pinterest.com/",
        })

    def _sleep(self):
        time.sleep(random.uniform(self._delays["min"], self._delays["max"]))

    def get_autocomplete_suggestions(self, query: str) -> List[str]:
        """
        Fetch Pinterest autocomplete suggestions for a query.
        Uses the public suggest endpoint — no API key needed.
        """
        params = {
            "source_url": f"/search/pins/?q={query}",
            "data": json.dumps({
                "options": {
                    "query": query,
                    "scope": "pins",
                    "hidden_fields": ["page_info"],
                },
                "context": {},
            }),
        }
        try:
            self._sleep()
            resp = self._session.get(PINTEREST_SUGGEST_URL, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = (
                data.get("resource_response", {})
                    .get("data", {})
                    .get("items", [])
            )
            return [item.get("display_name", "") or item.get("query", "") for item in items if item]
        except Exception as exc:
            logger.warning("Pinterest autocomplete error for '%s': %s", query, exc)
            return []

    def get_trending_topics(self) -> List[str]:
        """
        Scrape Pinterest trends page for top trending topics.
        """
        url = f"{PINTEREST_BASE}/ideas/"
        try:
            self._sleep()
            resp = self._session.get(url, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            topics = []
            for sel in [
                "a[href*='/search/pins/']",
                "[data-test-id='trending-search']",
                ".trendingSearchCard",
            ]:
                for el in soup.select(sel):
                    text = el.get_text(strip=True)
                    if text and 2 < len(text) < 60:
                        topics.append(text.lower())
            return list(dict.fromkeys(topics))[:50]
        except Exception as exc:
            logger.warning("Pinterest trending topics error: %s", exc)
            return []

    def analyze_pod_trends(self, seed_keywords: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        For each seed keyword, fetch Pinterest autocomplete suggestions.
        Returns {keyword: [suggestions]}.
        """
        if seed_keywords is None:
            seed_keywords = [
                "seamless pattern",
                "surface pattern design",
                "fabric print",
                "repeat pattern",
                "textile pattern",
                "pattern design",
            ]
        results: Dict[str, List[str]] = {}
        for kw in seed_keywords:
            suggestions = self.get_autocomplete_suggestions(kw)
            if suggestions:
                results[kw] = suggestions
        return results

    def get_niche_suggestions(self, niche: str) -> List[str]:
        """Get Pinterest suggestions for a specific niche + 'pattern'."""
        queries = [f"{niche} pattern", f"{niche} design", niche]
        all_suggestions = []
        for q in queries:
            suggestions = self.get_autocomplete_suggestions(q)
            all_suggestions.extend(suggestions)
        return list(dict.fromkeys(all_suggestions))[:20]
