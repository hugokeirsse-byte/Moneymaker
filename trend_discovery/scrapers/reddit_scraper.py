"""
Reddit scraper using the public JSON API (no authentication required).
Falls back to PRAW if credentials are available in the environment.
"""
import logging
import random
import re
import time
from collections import Counter
from typing import Dict, List, Optional

import requests

from trend_discovery.config import (
    DEFAULT_HEADERS,
    REDDIT_CLIENT_ID,
    REDDIT_CLIENT_SECRET,
    REDDIT_SUBREDDITS,
    REDDIT_USER_AGENT,
    SCRAPER_DELAYS,
)

logger = logging.getLogger(__name__)

REDDIT_BASE = "https://www.reddit.com"
# Common English stop-words to exclude from keyword extraction
_STOP_WORDS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "this", "that", "was", "are",
    "be", "as", "i", "you", "he", "she", "we", "they", "my", "your",
    "how", "what", "when", "where", "who", "why", "do", "did", "does",
    "not", "no", "so", "if", "up", "out", "about", "just", "more",
    "can", "will", "would", "could", "should", "has", "have", "had",
    "get", "got", "any", "all", "one", "two", "three", "its", "their",
    "our", "than", "then", "there", "here", "also", "been", "into",
    "me", "him", "her", "us", "them", "which", "his",
}


class RedditScraper:
    """
    Collects trend signals from POD-related subreddits.
    Works in anonymous mode (public JSON API) or with PRAW when credentials
    are provided.
    """

    def __init__(
        self,
        subreddits: Optional[List[str]] = None,
        use_praw: bool = False,
    ):
        self._subreddits = subreddits or REDDIT_SUBREDDITS
        self._delays = SCRAPER_DELAYS["reddit"]
        self._session = requests.Session()
        self._session.headers.update({**DEFAULT_HEADERS, "User-Agent": REDDIT_USER_AGENT})
        self._praw_reddit = None
        if use_praw and REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET:
            self._init_praw()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sleep(self):
        time.sleep(random.uniform(self._delays["min"], self._delays["max"]))

    def _init_praw(self):
        try:
            import praw  # noqa: F401 – optional dependency
            self._praw_reddit = praw.Reddit(
                client_id=REDDIT_CLIENT_ID,
                client_secret=REDDIT_CLIENT_SECRET,
                user_agent=REDDIT_USER_AGENT,
                read_only=True,
            )
            logger.info("PRAW initialized successfully.")
        except Exception as exc:
            logger.warning("PRAW initialization failed: %s", exc)

    def _score_post(self, post_data: Dict) -> float:
        """
        Compute a normalized buzz score (0-100) for a single post using
        upvotes and comments.
        """
        ups = max(0, post_data.get("ups", 0))
        comments = max(0, post_data.get("num_comments", 0))
        raw = ups + comments * 2
        # Cap at 10 000 for normalization purposes
        return min(100.0, raw / 100.0)

    def _extract_words(self, text: str) -> List[str]:
        """Tokenize text into lowercase words, removing stop words."""
        words = re.findall(r"[a-z]{3,}", text.lower())
        return [w for w in words if w not in _STOP_WORDS]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_hot_posts(self, subreddit: str, limit: int = 100) -> List[Dict]:
        """
        Retrieve hot posts from a subreddit using the public JSON endpoint.

        Args:
            subreddit: Name of the subreddit (without r/).
            limit:     Number of posts to retrieve (max 100).

        Returns:
            List of dicts with keys: title, score, num_comments, url, created_utc, buzz_score.
        """
        url = f"{REDDIT_BASE}/r/{subreddit}/hot.json"
        params = {"limit": min(limit, 100)}
        posts = []
        try:
            self._sleep()
            response = self._session.get(url, params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            children = data.get("data", {}).get("children", [])
            for item in children:
                post = item.get("data", {})
                posts.append(
                    {
                        "title": post.get("title", ""),
                        "score": post.get("score", 0),
                        "ups": post.get("ups", 0),
                        "num_comments": post.get("num_comments", 0),
                        "url": post.get("url", ""),
                        "permalink": REDDIT_BASE + post.get("permalink", ""),
                        "created_utc": post.get("created_utc", 0),
                        "subreddit": subreddit,
                        "buzz_score": self._score_post(post),
                    }
                )
        except requests.exceptions.RequestException as exc:
            logger.error("Reddit request error for r/%s: %s", subreddit, exc)
        except Exception as exc:
            logger.error("Reddit parse error for r/%s: %s", subreddit, exc)
        return posts

    def get_trending_keywords_from_reddit(
        self, subreddits: Optional[List[str]] = None, top_n: int = 50
    ) -> Dict[str, float]:
        """
        Aggregate posts from all subreddits and extract the most-mentioned
        keywords, weighted by post buzz score.

        Args:
            subreddits: Override default subreddit list.
            top_n:      Return the top N keywords.

        Returns:
            {keyword: weighted_score, ...} sorted by score descending.
        """
        target_subs = subreddits or self._subreddits
        word_scores: Dict[str, float] = {}

        for sub in target_subs:
            posts = self.get_hot_posts(sub)
            for post in posts:
                words = self._extract_words(post["title"])
                weight = post["buzz_score"]
                for word in words:
                    word_scores[word] = word_scores.get(word, 0.0) + weight

        # Normalize to 0-100
        if word_scores:
            max_score = max(word_scores.values())
            if max_score > 0:
                word_scores = {k: (v / max_score) * 100 for k, v in word_scores.items()}

        # Sort and truncate
        sorted_kws = sorted(word_scores.items(), key=lambda x: x[1], reverse=True)
        return dict(sorted_kws[:top_n])

    def get_post_titles_by_keyword(
        self, keyword: str, subreddits: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Search posts whose title contains *keyword* across subreddits.

        Args:
            keyword:    Keyword to search for.
            subreddits: Override default subreddit list.

        Returns:
            List of post dicts (same format as get_hot_posts).
        """
        target_subs = subreddits or self._subreddits
        matching_posts = []
        kw_lower = keyword.lower()

        for sub in target_subs:
            posts = self.get_hot_posts(sub)
            for post in posts:
                if kw_lower in post["title"].lower():
                    matching_posts.append(post)

        # Sort by buzz_score descending
        matching_posts.sort(key=lambda p: p["buzz_score"], reverse=True)
        return matching_posts

    def get_keyword_buzz_score(self, keyword: str) -> float:
        """
        Return a 0-100 buzz score for a specific keyword based on Reddit
        presence and engagement.
        """
        posts = self.get_post_titles_by_keyword(keyword)
        if not posts:
            return 0.0
        total = sum(p["buzz_score"] for p in posts)
        # Diminishing returns: cap at 100
        return min(100.0, total)

    def get_all_subreddit_data(self) -> Dict[str, List[Dict]]:
        """
        Collect hot posts from all configured subreddits.

        Returns:
            {subreddit_name: [post_dict, ...], ...}
        """
        result = {}
        for sub in self._subreddits:
            result[sub] = self.get_hot_posts(sub)
        return result
