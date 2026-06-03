"""
TikTok trend scraper — hashtag trends and trending sounds/themes.

TikTok drives a significant portion of aesthetic trends that land on POD.
Uses the Creative Center public API (no auth required) and
TikTok autocomplete/search suggestions.
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

TIKTOK_CREATIVE_CENTER = "https://ads.tiktok.com/business/creativecenter"
TIKTOK_TRENDING_HASHTAGS = (
    "https://ads.tiktok.com/business/creativecenter/hashtag/home/pc/en"
)


class TikTokScraper:
    """
    Extracts trend signals from TikTok:
    - Trending hashtags (via TikTok Creative Center — public, no auth)
    - Trending searches (via search autocomplete)
    - Aesthetic/theme trends

    TikTok hashtag trends are highly predictive of near-future POD demand.
    """

    def __init__(self):
        self._delays = SCRAPER_DELAYS.get("tiktok", {"min": 2, "max": 5})
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    def _sleep(self):
        time.sleep(random.uniform(self._delays["min"], self._delays["max"]))

    def get_trending_hashtags(self, country: str = "US", period: str = "7") -> List[Dict]:
        """
        Fetch trending hashtags from TikTok Creative Center.
        Country: "US", "GB", "FR", etc.
        Period: "7" (7 days), "30" (30 days)
        """
        url = "https://ads.tiktok.com/business/creativecenter/api/v1/creativecenter/hashtag/list/v2"
        params = {
            "period": period,
            "country_code": country,
            "page": 1,
            "limit": 50,
        }
        try:
            self._sleep()
            resp = self._session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            hashtags = data.get("data", {}).get("list", [])
            return [
                {
                    "hashtag": h.get("hashtag_name", ""),
                    "post_count": h.get("publish_cnt", 0),
                    "view_count": h.get("video_views", 0),
                    "trend": h.get("trend", ""),
                }
                for h in hashtags
            ]
        except Exception as exc:
            logger.warning("TikTok Creative Center hashtag error: %s", exc)
            return []

    def get_aesthetic_hashtags(self) -> List[str]:
        """
        Filter trending hashtags for POD-relevant aesthetics.
        """
        all_hashtags = self.get_trending_hashtags()
        if not all_hashtags:
            # Fallback to known aesthetic hashtags if API fails
            return [
                "cottagecore", "darkacademia", "goblincore", "fairycore",
                "witchtok", "altaesthetic", "cottagewitchtok",
                "mushroomtok", "celestial", "botanical", "vintage",
                "solarpunk", "cozyaesthetic",
            ]
        pod_keywords = [
            "core", "aesthetic", "art", "pattern", "design", "vintage",
            "cottag", "goblin", "fairy", "witch", "botanical", "floral",
            "mushroom", "celestial", "dark", "gothic",
        ]
        relevant = []
        for h in all_hashtags:
            name = h["hashtag"].lower()
            if any(kw in name for kw in pod_keywords):
                relevant.append(name)
        return relevant[:30]

    def get_trending_sounds_topics(self) -> List[str]:
        """
        Trending sound topics often reflect aesthetic communities.
        Returns topic names that map to POD niches.
        """
        url = "https://ads.tiktok.com/business/creativecenter/api/v1/creativecenter/trend/music/list/v2"
        params = {"period": "7", "country_code": "US", "page": 1, "limit": 20}
        try:
            self._sleep()
            resp = self._session.get(url, params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            songs = data.get("data", {}).get("music_info", [])
            topics = []
            for song in songs:
                for tag in song.get("tags", []):
                    topics.append(tag.lower())
            return list(dict.fromkeys(topics))[:30]
        except Exception as exc:
            logger.warning("TikTok music trends error: %s", exc)
            return []

    def map_hashtags_to_niches(self, hashtags: List[str]) -> Dict[str, float]:
        """
        Map TikTok hashtags to POD niche scores.
        More mentions / higher views = higher demand signal.
        Returns {niche_keyword: normalized_score_0_100}.
        """
        # Manual mapping of TikTok aesthetics → POD niches
        HASHTAG_TO_NICHE = {
            "cottagecore": "cottagecore",
            "cottage": "cottagecore",
            "darkacademia": "dark academia",
            "goblincore": "goblincore",
            "fairycore": "fairycore",
            "witchtok": "witchy",
            "botanical": "botanique",
            "mushroomtok": "champignons",
            "mushroom": "champignons",
            "celestial": "céleste",
            "astrology": "astrologie",
            "tarot": "tarot",
            "crystals": "cristaux",
            "vintage": "vintage",
            "retro": "rétro",
            "aesthetic": None,  # too generic
            "artnouveau": "art nouveau",
            "gothicaesthetic": "gothique",
            "japandi": "japandi",
            "solarpunk": "solarpunk",
            "boho": "boho",
            "maximalist": "maximalist",
        }
        niche_scores: Dict[str, float] = {}
        for tag in hashtags:
            tag_clean = tag.replace("#", "").lower().replace(" ", "")
            for key, niche in HASHTAG_TO_NICHE.items():
                if niche and (key in tag_clean or tag_clean in key):
                    niche_scores[niche] = niche_scores.get(niche, 0) + 10
        # Normalize to 0-100
        if niche_scores:
            max_score = max(niche_scores.values())
            niche_scores = {k: min(100.0, v / max_score * 100) for k, v in niche_scores.items()}
        return niche_scores
