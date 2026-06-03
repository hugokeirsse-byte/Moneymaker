"""
Creative Market scraper — bestselling design assets and patterns.

Creative Market is where professional designers sell assets.
Trending items here indicate what buyers are paying for right now.
Also a good source of B2B potential signals.
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

CM_BASE = "https://creativemarket.com"


class CreativeMarketScraper:
    """
    Scrapes Creative Market for:
    - Bestselling pattern/surface design assets
    - Popular tags and keywords
    - Price points (commercial viability signal)
    """

    def __init__(self):
        self._delays = SCRAPER_DELAYS.get("creative_market", {"min": 4, "max": 8})
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    def _sleep(self):
        time.sleep(random.uniform(self._delays["min"], self._delays["max"]))

    def _get(self, url: str, params: Optional[Dict] = None) -> Optional[BeautifulSoup]:
        try:
            self._sleep()
            resp = self._session.get(url, params=params, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except Exception as exc:
            logger.error("Creative Market error [%s]: %s", url, exc)
            return None

    def get_bestselling_patterns(self) -> List[Dict]:
        """Scrape bestselling seamless patterns."""
        url = f"{CM_BASE}/category/patterns"
        soup = self._get(url, {"sort": "sales"})
        if soup is None:
            return []
        products = []
        for card in soup.select(".product-card, [data-testid='product-card']")[:30]:
            title_el = card.select_one("h3, .title, .product-title")
            price_el = card.select_one(".price, .product-price")
            title = title_el.get_text(strip=True) if title_el else ""
            price = price_el.get_text(strip=True) if price_el else ""
            if title:
                products.append({"title": title.lower(), "price": price})
        return products

    def get_popular_tags(self) -> List[str]:
        """Extract popular tags from pattern/texture category."""
        soup = self._get(f"{CM_BASE}/category/patterns")
        if soup is None:
            return []
        tags = []
        for sel in ["a[href*='/search/patterns/']", ".tag-link", ".facet-option"]:
            for el in soup.select(sel):
                text = el.get_text(strip=True)
                if text and 2 < len(text) < 50:
                    tags.append(text.lower())
        return list(dict.fromkeys(tags))[:40]

    def search_count(self, keyword: str) -> int:
        """Get number of pattern products for a keyword on Creative Market."""
        soup = self._get(f"{CM_BASE}/search/patterns", {"q": keyword})
        if soup is None:
            return 0
        for sel in [".search-result-count", "h1 em", ".results-count"]:
            el = soup.select_one(sel)
            if el:
                numbers = re.findall(r"[\d,]+", el.get_text())
                if numbers:
                    return int(numbers[0].replace(",", ""))
        # Count cards as fallback
        cards = soup.select(".product-card")
        return len(cards) * 5
