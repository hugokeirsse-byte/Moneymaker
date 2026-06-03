"""
Society6 scraper — competition signal and trending tag extraction.
Society6 is a major POD platform for art prints, patterns, home decor.
"""
import logging
import random
import re
import time
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from trend_discovery.config import DEFAULT_HEADERS, SCRAPER_DELAYS

logger = logging.getLogger(__name__)

SOCIETY6_BASE = "https://society6.com"


class Society6Scraper:
    """Extracts trending designs and competition data from Society6."""

    def __init__(self):
        self._delays = SCRAPER_DELAYS.get("society6", {"min": 4, "max": 8})
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    def _sleep(self):
        time.sleep(random.uniform(self._delays["min"], self._delays["max"]))

    def _get(self, url: str, params: Optional[Dict] = None) -> Optional[BeautifulSoup]:
        try:
            self._sleep()
            resp = self._session.get(url, params=params, timeout=20)
            if resp.status_code == 429:
                time.sleep(30)
                resp = self._session.get(url, params=params, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except Exception as exc:
            logger.error("Society6 error [%s]: %s", url, exc)
            return None

    def get_trending_tags(self) -> List[str]:
        """Scrape Society6 trending/popular tags."""
        soup = self._get(f"{SOCIETY6_BASE}/popular")
        if soup is None:
            return []
        tags = []
        for sel in ["a[href*='/tag/']", ".tag-link", "[data-tag]"]:
            for el in soup.select(sel):
                text = el.get_text(strip=True) or el.get("data-tag", "")
                if text and 2 < len(text) < 50:
                    tags.append(text.lower())
        return list(dict.fromkeys(tags))[:50]

    def search_count(self, keyword: str) -> int:
        """Estimate competition for a keyword on Society6."""
        soup = self._get(f"{SOCIETY6_BASE}/search", {"q": keyword})
        if soup is None:
            return 0
        for sel in [".search-result-count", "[data-result-count]", "h1 strong"]:
            el = soup.select_one(sel)
            if el:
                text = el.get("data-result-count") or el.get_text()
                numbers = re.findall(r"[\d,]+", text)
                if numbers:
                    return int(numbers[0].replace(",", ""))
        # Count product cards as fallback
        cards = soup.select(".product-card, [data-testid='product-card']")
        return len(cards) * 10  # rough estimate

    def get_bestselling_categories(self) -> List[str]:
        """Return bestselling category names."""
        soup = self._get(f"{SOCIETY6_BASE}/best-sellers")
        if soup is None:
            return []
        cats = []
        for sel in ["a[href*='/shop/']", ".category-link", "nav a"]:
            for el in soup.select(sel):
                text = el.get_text(strip=True)
                if text and 2 < len(text) < 40:
                    cats.append(text.lower())
        return list(dict.fromkeys(cats))[:30]
