"""
RedBubble scraper — extracts competition signals and trending search terms.
No API key required. Respectful delays between requests.
"""
import logging
import random
import re
import time
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from trend_discovery.config import DEFAULT_HEADERS, PLATFORMS, SCRAPER_DELAYS

logger = logging.getLogger(__name__)

BASE_URL = PLATFORMS["redbubble"]


class RedbubbleScraper:
    """Scrapes RedBubble to extract competition data and trending searches."""

    def __init__(self):
        self._delays = SCRAPER_DELAYS["redbubble"]
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    def _sleep(self):
        time.sleep(random.uniform(self._delays["min"], self._delays["max"]))

    def _get(self, url: str, params: Optional[Dict] = None) -> Optional[BeautifulSoup]:
        try:
            self._sleep()
            resp = self._session.get(url, params=params, timeout=20)
            if resp.status_code == 429:
                logger.warning("Rate limited by RedBubble, waiting 30s…")
                time.sleep(30)
                resp = self._session.get(url, params=params, timeout=20)
            resp.raise_for_status()
            return BeautifulSoup(resp.text, "lxml")
        except requests.exceptions.RequestException as exc:
            logger.error("RedBubble request error [%s]: %s", url, exc)
            return None

    def get_trending_searches(self) -> List[str]:
        """
        Attempt to extract trending/popular search terms from the RedBubble
        explore/trending page.
        """
        url = f"{BASE_URL}/explore/trending"
        soup = self._get(url)
        if soup is None:
            return []
        terms = []
        # Popular tags or trending pills
        for selector in [
            "a[href*='/shop/']",
            ".TrendingTag",
            "[data-testid='trending-tag']",
            ".PopularTag",
            "li.tag a",
        ]:
            elements = soup.select(selector)
            for el in elements:
                text = el.get_text(strip=True)
                if text and len(text) > 2:
                    terms.append(text.lower())
        return list(dict.fromkeys(terms))[:50]  # deduplicate, keep order

    def search_products(self, keyword: str) -> Dict:
        """
        Search RedBubble for a keyword and return metadata including an
        approximate result count (competition proxy).
        """
        url = f"{BASE_URL}/shop/"
        params = {"query": keyword, "ref": "search_box"}
        soup = self._get(url, params=params)
        result = {
            "keyword": keyword,
            "result_count": 0,
            "sample_titles": [],
        }
        if soup is None:
            return result

        # Try to find result count
        for selector in [
            "[data-testid='result-count']",
            ".ResultCount",
            "span.result-count",
            "h1.result",
        ]:
            el = soup.select_one(selector)
            if el:
                numbers = re.findall(r"[\d,]+", el.get_text())
                if numbers:
                    result["result_count"] = int(numbers[0].replace(",", ""))
                    break

        # Collect a few product titles for context
        title_els = soup.select(
            "[data-testid='product-title'], .productCard-title, h3.title"
        )[:10]
        result["sample_titles"] = [t.get_text(strip=True) for t in title_els if t.get_text(strip=True)]

        return result

    def get_popular_tags(self) -> List[str]:
        """Extract popular tags from the RedBubble homepage."""
        url = f"{BASE_URL}/"
        soup = self._get(url)
        if soup is None:
            return []
        tags = []
        for selector in ["a[href*='/shop/']", ".tag", ".Tag", "[data-testid='tag']"]:
            els = soup.select(selector)
            for el in els:
                text = el.get_text(strip=True)
                if text and 2 < len(text) < 50:
                    tags.append(text.lower())
        return list(dict.fromkeys(tags))[:60]

    def analyze_competition(self, keyword: str) -> Dict:
        """
        Return a competition analysis dict for a keyword.

        Returns:
            {
                "keyword": str,
                "result_count": int,
                "competition_score": float,   # 0-100, higher = more competition
                "opportunity_score": float,   # 0-100, higher = more opportunity
                "competition_level": str,     # "low" / "medium" / "high"
            }
        """
        data = self.search_products(keyword)
        count = data["result_count"]

        # Thresholds (empirically tuned for RedBubble):
        # < 1 000  → low competition
        # 1 000 – 10 000 → medium
        # > 10 000 → high
        if count == 0:
            competition_score = 0.0
        elif count < 1_000:
            competition_score = (count / 1_000) * 30  # 0-30
        elif count < 10_000:
            competition_score = 30 + ((count - 1_000) / 9_000) * 40  # 30-70
        else:
            competition_score = min(100.0, 70 + ((count - 10_000) / 90_000) * 30)  # 70-100

        opportunity_score = 100.0 - competition_score

        if competition_score < 35:
            level = "low"
        elif competition_score < 65:
            level = "medium"
        else:
            level = "high"

        return {
            "keyword": keyword,
            "result_count": count,
            "competition_score": round(competition_score, 1),
            "opportunity_score": round(opportunity_score, 1),
            "competition_level": level,
        }

    def batch_analyze_competition(self, keywords: List[str]) -> List[Dict]:
        """Analyze competition for a list of keywords."""
        results = []
        for kw in keywords:
            results.append(self.analyze_competition(kw))
        return results
