"""
Provider YouTube — Data API v3 officielle (gratuite, quota 10 000 u/jour).

La demande de tutoriels/contenus sur une niche est un signal réel d'intérêt :
si beaucoup de gens cherchent "how to draw cottagecore patterns" avec
beaucoup de vues, l'esthétique est demandée.

Authentification : clé API Google (gratuite).
    YOUTUBE_API_KEY

Obtenir : https://console.cloud.google.com → activer "YouTube Data API v3"
"""
from __future__ import annotations

import logging
import math
import os
from typing import Dict, List, Optional

import requests

from trend_discovery.providers.base_provider import DataProvider
from trend_discovery.provenance import Metric

logger = logging.getLogger(__name__)

YT_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeProvider(DataProvider):
    key = "youtube"
    name = "YouTube Data API v3"
    required_env = ["YOUTUBE_API_KEY"]
    produces_measured_data = True

    def __init__(self):
        super().__init__()
        self._api_key = os.getenv("YOUTUBE_API_KEY", "")
        self._session = requests.Session()

    def _check_credentials(self) -> bool:
        return bool(self._api_key)

    def get_search_stats(self, query: str, max_results: int = 25) -> Optional[Dict]:
        """
        Recherche des vidéos et agrège les vraies statistiques de vues.

        Returns: {"video_count": int, "total_views": int, "avg_views": float} ou None.
        """
        if not self.is_available():
            return None
        try:
            # 1. Recherche → IDs vidéos
            sresp = self._session.get(
                f"{YT_BASE}/search",
                params={
                    "part": "id", "q": query, "type": "video",
                    "maxResults": max_results, "key": self._api_key,
                },
                timeout=20,
            )
            sresp.raise_for_status()
            ids = [it["id"]["videoId"] for it in sresp.json().get("items", []) if it.get("id", {}).get("videoId")]
            total_results = sresp.json().get("pageInfo", {}).get("totalResults", 0)
            if not ids:
                return {"video_count": total_results, "total_views": 0, "avg_views": 0.0}

            # 2. Statistiques des vidéos
            vresp = self._session.get(
                f"{YT_BASE}/videos",
                params={"part": "statistics", "id": ",".join(ids), "key": self._api_key},
                timeout=20,
            )
            vresp.raise_for_status()
            views = [int(v.get("statistics", {}).get("viewCount", 0)) for v in vresp.json().get("items", [])]
            total_views = sum(views)
            return {
                "video_count": total_results,
                "total_views": total_views,
                "avg_views": total_views / len(views) if views else 0.0,
            }
        except Exception as exc:
            logger.error("[youtube] erreur stats pour '%s': %s", query, exc)
            return None

    def demand_metric(self, niche: str) -> Metric:
        """
        Demande réelle (0-100) basée sur les vues moyennes des tutoriels.
        Échelle log sur la moyenne de vues.
        """
        stats = self.get_search_stats(f"{niche} pattern tutorial")
        if stats is None:
            return Metric.unavailable(detail=f"YouTube indisponible pour '{niche}'")
        avg = stats.get("avg_views", 0)
        if avg <= 0:
            return Metric.measured(0.0, source="youtube", confidence=70.0,
                                   detail="aucune vue (réel)")
        score = min(100.0, (math.log10(avg + 1) / 6.5) * 100)
        return Metric.measured(
            round(score, 1), source="youtube", confidence=78.0,
            detail=f"{int(avg):,} vues moy./tuto (réel)".replace(",", " "),
        )
