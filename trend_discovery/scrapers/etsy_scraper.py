"""
Etsy scraper — trending searches, popular tags, and bestseller signals.
Uses the public search pages (no API key) + optional Etsy API v3.
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

ETSY_BASE = "https://www.etsy.com"


class EtsyScraper:
    """
    Scrapes Etsy for:
    - Trending searches / popular tags
    - Bestselling items in fabric/patterns categories
    - Search result counts (competition proxy)
    """

    def __init__(self):
        self._delays = SCRAPER_DELAYS.get("etsy", {"min": 4, "max": 8})
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    def _sleep(self):
        time.sleep(random.uniform(self._delays["min"], self._delays["max"]))

    def _get(self, url: str, params: Optional[Dict] = None) -> Optional[BeautifulSoup]:
        try:
            self._sleep()
            resp = self._session.get(url, params=params, timeout=20)
            if resp.status_code == 429:
                logger.warning("Etsy rate limited — waiting 45s")
                time.sleep(45)
                resp = self._session.get(url, params=params, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except requests.exceptions.RequestException as exc:
            logger.error("Etsy request error [%s]: %s", url, exc)
            return None

    def get_trending_searches(self) -> List[str]:
        """Extract trending searches from Etsy's trending page."""
        soup = self._get(f"{ETSY_BASE}/trending")
        if soup is None:
            return []
        terms = []
        # Trending cards / links
        for sel in ["a[href*='/search?q=']", ".trending-term", "[data-search-query]"]:
            els = soup.select(sel)
            for el in els:
                text = el.get_text(strip=True) or el.get("data-search-query", "")
                if text and 2 < len(text) < 60:
                    terms.append(text.lower())
        return list(dict.fromkeys(terms))[:40]

    def search_count(self, keyword: str) -> int:
        """Return approximate number of Etsy listings for a keyword."""
        url = f"{ETSY_BASE}/search"
        soup = self._get(url, params={"q": keyword, "type": "handmade"})
        if soup is None:
            return 0
        for selector in [
            "[data-search-pagination-results-count]",
            ".search-pagination-results-count",
            "p.wt-text-body-01 strong",
        ]:
            el = soup.select_one(selector)
            if el:
                text = el.get("data-search-pagination-results-count") or el.get_text()
                numbers = re.findall(r"[\d,]+", text)
                if numbers:
                    return int(numbers[0].replace(",", ""))
        return 0

    def get_popular_pod_tags(self) -> Dict[str, int]:
        """
        Search POD-relevant categories and extract popular tags/keywords.
        """
        searches = [
            "seamless pattern fabric",
            "surface pattern design",
            "print on demand fabric",
            "spoonflower fabric",
        ]
        tag_counts: Dict[str, int] = {}
        for query in searches:
            url = f"{ETSY_BASE}/search"
            soup = self._get(url, params={"q": query})
            if soup is None:
                continue
            # Extract tags from listing titles
            for title_el in soup.select("h3.v2-listing-card__title, .listing-card-title")[:20]:
                title = title_el.get_text(strip=True).lower()
                words = re.findall(r"[a-z]{3,}", title)
                for w in words:
                    tag_counts[w] = tag_counts.get(w, 0) + 1
        # Sort by frequency
        return dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)[:50])

    def analyze_competition(self, keyword: str) -> Dict:
        """Competition analysis for a keyword on Etsy."""
        count = self.search_count(keyword)
        if count < 500:
            level, opp = "low", min(100.0, 100 - count / 10)
        elif count < 5000:
            level, opp = "medium", 70 - (count - 500) / 450 * 30
        else:
            level, opp = "high", max(10.0, 40 - (count - 5000) / 10000 * 30)
        comp = 100 - opp
        return {
            "keyword": keyword,
            "platform": "etsy",
            "result_count": count,
            "competition_score": round(comp, 1),
            "opportunity_score": round(opp, 1),
            "competition_level": level,
        }
