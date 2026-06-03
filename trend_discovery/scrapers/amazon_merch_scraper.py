"""
Amazon Merch / Amazon search scraper.

Amazon is the largest product marketplace — search volumes and
bestseller ranks are highly predictive signals for POD niches.
Uses autocomplete + bestseller page scraping (no API key).
"""
import json
import logging
import random
import re
import time
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from trend_discovery.config import DEFAULT_HEADERS, SCRAPER_DELAYS

logger = logging.getLogger(__name__)

AMAZON_AUTOCOMPLETE_URL = "https://completion.amazon.com/api/2017/suggestions"
AMAZON_BASE = "https://www.amazon.com"


class AmazonMerchScraper:
    """
    Extracts demand signals from Amazon:
    - Autocomplete suggestions (search intent, high volume)
    - Bestseller ranks in clothing/home categories
    - "Customers also bought" patterns

    Note: Amazon aggressively blocks scrapers.
    Autocomplete endpoint is much more permissive.
    """

    def __init__(self):
        self._delays = SCRAPER_DELAYS.get("amazon", {"min": 3, "max": 6})
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    def _sleep(self):
        time.sleep(random.uniform(self._delays["min"], self._delays["max"]))

    def get_autocomplete(self, query: str, marketplace: str = "1") -> List[str]:
        """
        Fetch Amazon autocomplete suggestions.
        Marketplace 1 = amazon.com, 3 = amazon.co.uk
        """
        params = {
            "client": "amazon-search-ui",
            "mid": f"ATVPDKIKX0DER",
            "alias": "aps",
            "b2b": "0",
            "fresh": "0",
            "ks": "64",
            "prefix": query,
            "event": "onKeyPress",
            "limit": "11",
            "fb": "1",
            "_": str(int(time.time() * 1000)),
        }
        try:
            self._sleep()
            resp = self._session.get(AMAZON_AUTOCOMPLETE_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            suggestions = data.get("suggestions", [])
            return [s.get("value", "") for s in suggestions if s.get("value")]
        except Exception as exc:
            logger.warning("Amazon autocomplete error for '%s': %s", query, exc)
            return []

    def get_pod_demand_signals(self, niches: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        For each niche, get Amazon autocomplete suggestions.
        High suggestion count = high search demand.
        """
        if niches is None:
            niches = [
                "seamless pattern",
                "botanical print",
                "cottagecore pattern",
                "gothic pattern",
                "mushroom pattern",
                "celestial pattern",
                "floral pattern fabric",
                "art nouveau print",
            ]
        results: Dict[str, List[str]] = {}
        for niche in niches:
            suggestions = self.get_autocomplete(niche)
            if suggestions:
                results[niche] = suggestions
        return results

    def get_merch_bestsellers(self, category_url: Optional[str] = None) -> List[str]:
        """
        Scrape Amazon Merch on Demand bestseller tags/titles.
        Falls back to apparel bestsellers if no URL given.
        """
        url = category_url or f"{AMAZON_BASE}/Best-Sellers-Clothing-Accessories-Novelty/zgbs/fashion/4841698011"
        try:
            self._sleep()
            resp = self._session.get(url, timeout=20)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "lxml")
            titles = []
            for sel in ["span.p-size-medium", ".p-col-right span", "div.p-row a"]:
                for el in soup.select(sel):
                    text = el.get_text(strip=True)
                    if text and len(text) > 5:
                        titles.append(text.lower())
            return list(dict.fromkeys(titles))[:30]
        except Exception as exc:
            logger.warning("Amazon bestsellers error: %s", exc)
            return []
