"""
YouTube Trends scraper — art/design tutorial views as demand signals.

If people are watching "how to draw cottagecore patterns" in large numbers,
it's a strong demand signal for that visual aesthetic in POD.
Uses YouTube Data API v3 (free: 10,000 units/day quota) if key available,
otherwise falls back to YouTube autocomplete (no key needed).
"""
import json
import logging
import os
import random
import time
from typing import Dict, List, Optional

import requests

from trend_discovery.config import DEFAULT_HEADERS, SCRAPER_DELAYS

logger = logging.getLogger(__name__)

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"
YOUTUBE_SUGGEST_URL = "https://suggestqueries.google.com/complete/search"


class YouTubeTrendsScraper:
    """
    Extracts design trend signals from YouTube.
    Works in two modes:
    - API mode: requires YOUTUBE_API_KEY env var (10k free units/day)
    - Autocomplete mode: no key needed, returns search suggestions
    """

    def __init__(self):
        self._delays = SCRAPER_DELAYS.get("youtube", {"min": 1, "max": 3})
        self._api_key = os.getenv("YOUTUBE_API_KEY", "")
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    def _sleep(self):
        time.sleep(random.uniform(self._delays["min"], self._delays["max"]))

    def get_autocomplete_suggestions(self, query: str) -> List[str]:
        """YouTube autocomplete (no API key, uses Google's suggest endpoint)."""
        params = {"client": "firefox", "ds": "yt", "q": query, "hl": "en"}
        try:
            self._sleep()
            resp = self._session.get(YOUTUBE_SUGGEST_URL, params=params, timeout=10)
            resp.raise_for_status()
            data = json.loads(resp.text)
            if isinstance(data, list) and len(data) >= 2:
                return [str(s) for s in data[1]]
            return []
        except Exception as exc:
            logger.warning("YouTube autocomplete error for '%s': %s", query, exc)
            return []

    def search_videos(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search YouTube videos via API.
        Returns basic stats (view count is a strong demand signal).
        Requires YOUTUBE_API_KEY.
        """
        if not self._api_key:
            logger.debug("No YOUTUBE_API_KEY set — skipping API search for '%s'", query)
            return []
        params = {
            "part": "snippet",
            "q": query,
            "maxResults": max_results,
            "type": "video",
            "relevanceLanguage": "en",
            "key": self._api_key,
        }
        try:
            self._sleep()
            resp = self._session.get(f"{YOUTUBE_API_BASE}/search", params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", [])
            videos = []
            for item in items:
                snippet = item.get("snippet", {})
                vid_id = item.get("id", {}).get("videoId", "")
                videos.append({
                    "title": snippet.get("title", ""),
                    "channel": snippet.get("channelTitle", ""),
                    "published": snippet.get("publishedAt", ""),
                    "video_id": vid_id,
                    "url": f"https://youtube.com/watch?v={vid_id}",
                })
            return videos
        except Exception as exc:
            logger.warning("YouTube API search error for '%s': %s", query, exc)
            return []

    def get_design_tutorial_demand(self, niches: Optional[List[str]] = None) -> Dict[str, List[str]]:
        """
        For each niche, get autocomplete suggestions for tutorial queries.
        High number of suggestions = high viewer interest.
        """
        if niches is None:
            niches = [
                "botanical pattern", "cottagecore art", "seamless pattern tutorial",
                "surface pattern design", "goblincore aesthetic", "mushroom pattern",
                "celestial pattern", "dark academia art",
            ]
        results: Dict[str, List[str]] = {}
        for niche in niches:
            queries = [f"{niche} tutorial", f"how to draw {niche}", f"{niche} timelapse"]
            for q in queries:
                suggestions = self.get_autocomplete_suggestions(q)
                if suggestions:
                    results.setdefault(niche, []).extend(suggestions)
        return results
