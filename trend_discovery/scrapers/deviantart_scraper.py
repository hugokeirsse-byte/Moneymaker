"""
DeviantArt scraper — trending art tags and popular deviations.

DeviantArt is where visual artists post work — trending tags here
are leading indicators for design aesthetics that will enter POD.
Uses public browse pages (no API key). Optional: DA API v1.
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

DA_BASE = "https://www.deviantart.com"


class DeviantArtScraper:
    """Extracts trending visual art tags and themes from DeviantArt."""

    def __init__(self):
        self._delays = SCRAPER_DELAYS.get("deviantart", {"min": 3, "max": 6})
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
            logger.error("DeviantArt error [%s]: %s", url, exc)
            return None

    def get_trending_tags(self) -> List[str]:
        """Scrape trending tags from DeviantArt daily popular page."""
        soup = self._get(f"{DA_BASE}/dailydeviations")
        if soup is None:
            return []
        tags = []
        for sel in ["a[href*='/tag/']", ".tag", "[data-hook='tag']"]:
            for el in soup.select(sel):
                text = el.get_text(strip=True)
                if text and 2 < len(text) < 40:
                    tags.append(text.lower())
        return list(dict.fromkeys(tags))[:50]

    def search_tag_popularity(self, tag: str) -> int:
        """Estimate how many deviations exist for a tag."""
        soup = self._get(f"{DA_BASE}/search/deviations", {"q": f"tag:{tag}"})
        if soup is None:
            return 0
        for sel in [".search-result-count", "h1 span"]:
            el = soup.select_one(sel)
            if el:
                numbers = re.findall(r"[\d,]+", el.get_text())
                if numbers:
                    return int(numbers[0].replace(",", ""))
        return 0

    def get_pattern_design_trending(self) -> List[str]:
        """Get trending items specifically in pattern/surface design."""
        soup = self._get(f"{DA_BASE}/browse/popular", {"catpath": "/resources/patterns"})
        if soup is None:
            return []
        titles = []
        for sel in ["span.title", "a.title", "[data-hook='deviation-title']"]:
            for el in soup.select(sel):
                text = el.get_text(strip=True)
                if text and len(text) > 3:
                    titles.append(text.lower())
        return list(dict.fromkeys(titles))[:30]
