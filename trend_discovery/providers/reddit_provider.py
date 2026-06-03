"""
Provider Reddit — API OAuth officielle (gratuite) via PRAW.

Bien plus stable que le scraping JSON anonyme (qui est bloqué en 403 sur les
IP de datacenter). Donne le vrai buzz communautaire :
    - upvotes réels, commentaires réels
    - communautés actives autour d'une niche

Authentification (gratuite) :
    REDDIT_CLIENT_ID
    REDDIT_CLIENT_SECRET
    REDDIT_USER_AGENT

Obtenir : https://www.reddit.com/prefs/apps (créer une app type "script")
"""
from __future__ import annotations

import logging
import math
import os
import re
from collections import Counter
from typing import Dict, List, Optional

from trend_discovery.providers.base_provider import DataProvider
from trend_discovery.provenance import Metric

logger = logging.getLogger(__name__)

_STOP = {
    "the", "and", "for", "with", "this", "that", "you", "your", "are",
    "have", "from", "what", "how", "can", "any", "all", "out", "get",
}


class RedditProvider(DataProvider):
    key = "reddit"
    name = "Reddit API (OAuth)"
    required_env = ["REDDIT_CLIENT_ID", "REDDIT_CLIENT_SECRET"]
    produces_measured_data = True

    def __init__(self, subreddits: Optional[List[str]] = None):
        super().__init__()
        self._cid = os.getenv("REDDIT_CLIENT_ID", "")
        self._secret = os.getenv("REDDIT_CLIENT_SECRET", "")
        self._ua = os.getenv("REDDIT_USER_AGENT", "Moneymaker/1.0")
        self._reddit = None
        self._subreddits = subreddits or [
            "surfacedesign", "patterndesign", "Spoonflower", "redbubble",
            "printondemand", "Etsy", "EtsySellers", "somethingimade",
            "crafts", "interiordecorating",
        ]

    def _check_credentials(self) -> bool:
        if not (self._cid and self._secret):
            return False
        try:
            import praw
            self._reddit = praw.Reddit(
                client_id=self._cid,
                client_secret=self._secret,
                user_agent=self._ua,
                read_only=True,
            )
            # Test léger
            self._reddit.subreddit("test").id
            return True
        except Exception as exc:
            logger.warning("[reddit] init PRAW échouée: %s", exc)
            return False

    def get_keyword_buzz(self, keyword: str, limit: int = 50) -> Optional[Dict]:
        """
        Recherche un mot-clé dans les subreddits POD et agrège le vrai
        engagement (upvotes + commentaires).

        Returns: {"posts": int, "total_score": int, "total_comments": int} ou None.
        """
        if not self.is_available() or self._reddit is None:
            return None
        total_score = 0
        total_comments = 0
        posts = 0
        try:
            for sub in self._subreddits:
                for submission in self._reddit.subreddit(sub).search(keyword, limit=limit // len(self._subreddits) + 1):
                    posts += 1
                    total_score += submission.score
                    total_comments += submission.num_comments
            return {"posts": posts, "total_score": total_score, "total_comments": total_comments}
        except Exception as exc:
            logger.error("[reddit] erreur recherche '%s': %s", keyword, exc)
            return None

    def buzz_metric(self, keyword: str) -> Metric:
        """Buzz Reddit réel (0-100) pour un mot-clé."""
        buzz = self.get_keyword_buzz(keyword)
        if buzz is None:
            return Metric.unavailable(detail=f"Reddit indisponible pour '{keyword}'")
        raw = buzz["total_score"] + buzz["total_comments"] * 2
        if raw <= 0:
            return Metric.measured(0.0, source="reddit", confidence=75.0,
                                   detail="aucun engagement (réel)")
        score = min(100.0, (math.log10(raw + 1) / 5) * 100)
        return Metric.measured(
            round(score, 1), source="reddit", confidence=80.0,
            detail=f"{buzz['posts']} posts, {buzz['total_score']} upvotes (réel)",
        )

    def get_trending_keywords(self, top_n: int = 50) -> Dict[str, float]:
        """Mots-clés les plus discutés (pondérés par engagement) dans les subreddits POD."""
        if not self.is_available() or self._reddit is None:
            return {}
        word_scores: Dict[str, float] = {}
        try:
            for sub in self._subreddits:
                for submission in self._reddit.subreddit(sub).hot(limit=50):
                    weight = math.log10(submission.score + submission.num_comments * 2 + 1)
                    for w in re.findall(r"[a-z]{3,}", submission.title.lower()):
                        if w not in _STOP:
                            word_scores[w] = word_scores.get(w, 0.0) + weight
            if word_scores:
                mx = max(word_scores.values())
                word_scores = {k: v / mx * 100 for k, v in word_scores.items()}
            return dict(sorted(word_scores.items(), key=lambda x: x[1], reverse=True)[:top_n])
        except Exception as exc:
            logger.error("[reddit] erreur trending: %s", exc)
            return {}
