"""
Google Autocomplete scraper — no API key required.
Uses the public suggest endpoint to discover niche sub-keywords.
"""
import json
import logging
import random
import string
import time
from typing import Dict, List

import requests

from trend_discovery.config import DEFAULT_HEADERS, KEYWORDS_SEED, NICHE_CATEGORIES, SCRAPER_DELAYS

logger = logging.getLogger(__name__)

AUTOCOMPLETE_URL = "https://suggestqueries.google.com/complete/search"


class GoogleAutocompleteScraper:
    """Fetches keyword suggestions from Google Autocomplete (no API key)."""

    def __init__(self):
        self._delays = SCRAPER_DELAYS["google_autocomplete"]
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    def _sleep(self):
        delay = random.uniform(self._delays["min"], self._delays["max"])
        time.sleep(delay)

    def get_autocomplete_suggestions(self, keyword: str) -> List[str]:
        """
        Return Google autocomplete suggestions for a given keyword.

        Args:
            keyword: The search query to expand.

        Returns:
            List of suggestion strings.
        """
        params = {
            "client": "firefox",
            "q": keyword,
            "hl": "en",
        }
        try:
            self._sleep()
            response = self._session.get(AUTOCOMPLETE_URL, params=params, timeout=10)
            response.raise_for_status()
            data = json.loads(response.text)
            # Response format: [query, [suggestion1, suggestion2, ...]]
            if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], list):
                return [str(s) for s in data[1]]
            return []
        except requests.exceptions.RequestException as exc:
            logger.error("Autocomplete request error for '%s': %s", keyword, exc)
            return []
        except (json.JSONDecodeError, IndexError, TypeError) as exc:
            logger.error("Autocomplete parse error for '%s': %s", keyword, exc)
            return []

    def get_alphabet_suggestions(self, base_keyword: str) -> Dict[str, List[str]]:
        """
        Append each letter a-z (and digits 0-9) after base_keyword to discover
        the full landscape of related queries.

        Args:
            base_keyword: e.g. "botanical pattern"

        Returns:
            {"a": ["botanical pattern aesthetic", ...], "b": [...], ...}
        """
        results: Dict[str, List[str]] = {}
        characters = string.ascii_lowercase + string.digits
        for char in characters:
            query = f"{base_keyword} {char}"
            suggestions = self.get_autocomplete_suggestions(query)
            if suggestions:
                results[char] = suggestions
        return results

    def analyze_pattern_niches(
        self,
        seed_keywords: List[str] = None,
        niche_categories: Dict[str, List[str]] = None,
    ) -> Dict[str, List[str]]:
        """
        Walk through seed keywords and niche category terms, collecting all
        autocomplete suggestions.

        Args:
            seed_keywords:    Override for KEYWORDS_SEED.
            niche_categories: Override for NICHE_CATEGORIES.

        Returns:
            {keyword: [suggestions], ...}
        """
        if seed_keywords is None:
            seed_keywords = KEYWORDS_SEED
        if niche_categories is None:
            niche_categories = NICHE_CATEGORIES

        all_results: Dict[str, List[str]] = {}

        # Collect from seed keywords
        for kw in seed_keywords:
            suggestions = self.get_autocomplete_suggestions(kw)
            if suggestions:
                all_results[kw] = suggestions

        # Collect from niche category terms
        for category, terms in niche_categories.items():
            for term in terms:
                combined = f"{term} pattern"
                suggestions = self.get_autocomplete_suggestions(combined)
                if suggestions:
                    all_results[combined] = suggestions

        return all_results

    def get_trending_pod_keywords(self) -> Dict[str, List[str]]:
        """
        Focused scan: combine popular POD descriptors with autocomplete to
        surface emerging niches.

        Returns:
            {query: [suggestions], ...}
        """
        pod_queries = [
            "seamless pattern ideas",
            "fabric print design",
            "surface pattern design",
            "print on demand niche",
            "trending fabric designs",
            "spoonflower trending",
            "redbubble trending",
            "best selling fabric pattern",
        ]
        results: Dict[str, List[str]] = {}
        for query in pod_queries:
            suggestions = self.get_autocomplete_suggestions(query)
            if suggestions:
                results[query] = suggestions
        return results
