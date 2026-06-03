"""
Spoonflower scraper — respectful scraping with delays, retry logic, and
realistic headers. No API key required.
"""
import logging
import random
import time
from typing import Dict, List, Optional
from collections import Counter
from urllib.parse import urlencode, quote_plus

import requests
from bs4 import BeautifulSoup

from trend_discovery.config import DEFAULT_HEADERS, PLATFORMS, SCRAPER_DELAYS

logger = logging.getLogger(__name__)

SPOONFLOWER_BASE = PLATFORMS["spoonflower"]


class SpoonflowerScraper:
    """
    Scrapes Spoonflower for trending, best-selling, and new designs.
    All public pages — no credentials needed.
    """

    def __init__(self):
        self._delays = SCRAPER_DELAYS["spoonflower"]
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sleep(self):
        """Polite delay between requests."""
        delay = random.uniform(self._delays["min"], self._delays["max"])
        time.sleep(delay)

    def _get(self, url: str, params: Optional[Dict] = None, retries: int = 3) -> Optional[BeautifulSoup]:
        """
        GET a URL with retry / exponential backoff on 429/503.

        Returns a BeautifulSoup object or None on failure.
        """
        for attempt in range(retries):
            try:
                self._sleep()
                response = self._session.get(url, params=params, timeout=20)
                if response.status_code in (429, 503):
                    wait = (2 ** attempt) * random.uniform(5, 10)
                    logger.warning(
                        "Spoonflower rate-limited (%s). Waiting %.1fs before retry %d/%d.",
                        response.status_code, wait, attempt + 1, retries,
                    )
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                return BeautifulSoup(response.text, "lxml")
            except requests.exceptions.RequestException as exc:
                logger.error("Spoonflower request error (attempt %d/%d): %s", attempt + 1, retries, exc)
                if attempt < retries - 1:
                    time.sleep(random.uniform(3, 6))
        return None

    def _parse_designs(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Parse design cards from a Spoonflower listing page.
        Returns a list of dicts with 'title' and 'tags'.
        """
        designs = []
        if soup is None:
            return designs

        # Spoonflower renders design cards with various class conventions;
        # we target both the legacy and current markup patterns.
        card_selectors = [
            "li[class*='DesignCard']",
            "li[class*='design-card']",
            "div[class*='DesignCard']",
            "div[class*='design-card']",
        ]
        cards = []
        for selector in card_selectors:
            cards = soup.select(selector)
            if cards:
                break

        # Fallback: grab any <img alt="..."> inside a product list
        if not cards:
            imgs = soup.select("ul img[alt]")
            for img in imgs:
                title = img.get("alt", "").strip()
                if title:
                    designs.append({"title": title, "tags": []})
            return designs

        for card in cards:
            title = ""
            tags: List[str] = []

            # Title from alt text or dedicated title element
            title_el = card.select_one("[class*='title'], [class*='Title']")
            if title_el:
                title = title_el.get_text(strip=True)
            else:
                img = card.select_one("img[alt]")
                if img:
                    title = img.get("alt", "").strip()

            # Tags from data attributes or anchor text in tag lists
            for tag_el in card.select("a[class*='tag'], [class*='Tag'] a, [data-tag]"):
                tag_text = tag_el.get_text(strip=True) or tag_el.get("data-tag", "")
                if tag_text:
                    tags.append(tag_text.lower().strip())

            if title or tags:
                designs.append({"title": title, "tags": tags})

        return designs

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_trending_designs(self) -> List[Dict]:
        """
        Scrape trending designs from Spoonflower.

        Returns:
            List of dicts with 'title' and 'tags'.
        """
        url = f"{SPOONFLOWER_BASE}/designs"
        soup = self._get(url, params={"sort": "trending"})
        designs = self._parse_designs(soup)
        logger.info("Spoonflower trending: fetched %d designs.", len(designs))
        return designs

    def get_bestseller_designs(self) -> List[Dict]:
        """
        Scrape best-selling designs from Spoonflower.

        Returns:
            List of dicts with 'title' and 'tags'.
        """
        url = f"{SPOONFLOWER_BASE}/designs"
        soup = self._get(url, params={"sort": "bestSelling"})
        designs = self._parse_designs(soup)
        logger.info("Spoonflower bestsellers: fetched %d designs.", len(designs))
        return designs

    def get_new_designs(self) -> List[Dict]:
        """
        Scrape the newest designs from Spoonflower.

        Returns:
            List of dicts with 'title' and 'tags'.
        """
        url = f"{SPOONFLOWER_BASE}/designs"
        soup = self._get(url, params={"sort": "date"})
        designs = self._parse_designs(soup)
        logger.info("Spoonflower new designs: fetched %d designs.", len(designs))
        return designs

    def search_designs(self, keyword: str) -> List[Dict]:
        """
        Search Spoonflower designs by keyword.

        Args:
            keyword: Search term.

        Returns:
            List of dicts with 'title' and 'tags'.
        """
        url = f"{SPOONFLOWER_BASE}/designs"
        soup = self._get(url, params={"q": keyword})
        designs = self._parse_designs(soup)
        logger.info("Spoonflower search '%s': fetched %d designs.", keyword, len(designs))
        return designs

    def extract_tags_from_designs(self, designs_list: List[Dict]) -> Counter:
        """
        Count all tags across a list of design dicts.

        Args:
            designs_list: Output of any scrape method.

        Returns:
            Counter mapping tag -> count.
        """
        tag_counter: Counter = Counter()
        for design in designs_list:
            for tag in design.get("tags", []):
                if tag:
                    tag_counter[tag] += 1
        return tag_counter

    def get_top_tags(self, limit: int = 50) -> Dict[str, int]:
        """
        Aggregate tags from trending, bestselling, and new pages.

        Args:
            limit: Return the top N tags.

        Returns:
            Dict {tag: count} sorted by count descending.
        """
        all_designs: List[Dict] = []
        all_designs.extend(self.get_trending_designs())
        all_designs.extend(self.get_bestseller_designs())
        all_designs.extend(self.get_new_designs())

        counter = self.extract_tags_from_designs(all_designs)
        top = counter.most_common(limit)
        return dict(top)
