"""
Trend scorer — combines Google Trends, Reddit buzz, and autocomplete signals
into a single normalised 0-100 trend score per keyword.
"""
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from trend_discovery.config import SCORING_WEIGHTS

logger = logging.getLogger(__name__)


@dataclass
class TrendScore:
    keyword: str
    google_trend_score: float = 0.0       # 0-100
    trend_direction: str = "stable"       # "rising" | "stable" | "declining"
    trend_velocity: float = 0.0           # rate of change (-100 to +100)
    seasonality_score: float = 0.0        # 0-100 (100 = highly seasonal)
    reddit_buzz_score: float = 0.0        # 0-100
    search_volume_proxy: float = 0.0      # 0-100 (from autocomplete density)
    overall_trend_score: float = 0.0      # 0-100 (weighted composite)
    sources: List[str] = field(default_factory=list)


class TrendScorer:
    """Aggregates multi-source data into a structured TrendScore."""

    # Weights within the trend score itself (separate from SCORING_WEIGHTS)
    _INTERNAL_WEIGHTS = {
        "google": 0.50,
        "reddit": 0.30,
        "autocomplete": 0.20,
    }

    def calculate_momentum(self, values: List[float]) -> float:
        """
        Compute trend momentum as the slope of a simple linear regression
        over the time series, normalised to [-100, +100].
        """
        n = len(values)
        if n < 2:
            return 0.0
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n
        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))
        if denominator == 0:
            return 0.0
        slope = numerator / denominator
        # Normalise: max possible slope is ~100/n (full 0→100 ramp)
        max_slope = 100.0 / max(n, 1)
        normalised = (slope / max_slope) * 100
        return max(-100.0, min(100.0, normalised))

    def detect_seasonality(self, values: List[float]) -> float:
        """
        Rough seasonality index: coefficient of variation of the time series.
        High CoV → high seasonality.
        Returns 0-100.
        """
        if not values or len(values) < 4:
            return 0.0
        mean = sum(values) / len(values)
        if mean == 0:
            return 0.0
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance)
        cov = (std / mean) * 100
        return min(100.0, cov)

    def _google_score(self, google_data: Optional[Dict], keyword: str) -> float:
        if not google_data or keyword not in google_data:
            return 0.0
        info = google_data[keyword]
        return float(info.get("mean_score", 0.0))

    def _autocomplete_score(self, autocomplete_data: Optional[Dict], keyword: str) -> float:
        """Score based on how many autocomplete suggestions exist for this keyword."""
        if not autocomplete_data:
            return 0.0
        # Count how many suggestion lists contain the keyword
        hits = sum(
            1 for q, suggestions in autocomplete_data.items()
            if keyword.lower() in q.lower()
            or any(keyword.lower() in s.lower() for s in suggestions)
        )
        total = max(len(autocomplete_data), 1)
        return min(100.0, (hits / total) * 100 * 3)  # *3 to boost sensitivity

    def calculate_trend_score(
        self,
        keyword: str,
        google_data: Optional[Dict] = None,
        reddit_data: Optional[Dict] = None,
        autocomplete_data: Optional[Dict] = None,
    ) -> TrendScore:
        """
        Build a full TrendScore for a keyword by combining all available data.

        Args:
            keyword:          The niche keyword.
            google_data:      Output of GoogleTrendsScraper.get_interest_over_time().
            reddit_data:      Output of RedditScraper.get_trending_keywords_from_reddit().
            autocomplete_data: Output of GoogleAutocompleteScraper.analyze_pattern_niches().
        """
        score = TrendScore(keyword=keyword)
        sources = []

        # --- Google Trends ---
        if google_data and keyword in google_data:
            info = google_data[keyword]
            values = info.get("values", [])
            score.google_trend_score = float(info.get("mean_score", 0.0))
            score.trend_velocity = self.calculate_momentum(values)
            score.seasonality_score = self.detect_seasonality(values)
            if score.trend_velocity > 5:
                score.trend_direction = "rising"
            elif score.trend_velocity < -5:
                score.trend_direction = "declining"
            else:
                score.trend_direction = "stable"
            sources.append("google_trends")
        elif google_data is not None:
            sources.append("google_trends(no_data)")

        # --- Reddit ---
        if reddit_data and isinstance(reddit_data, dict):
            kw_lower = keyword.lower()
            # Direct match or partial match
            buzz = reddit_data.get(keyword, reddit_data.get(kw_lower, None))
            if buzz is None:
                # Look for partial keyword overlap
                for k, v in reddit_data.items():
                    if kw_lower in k.lower() or k.lower() in kw_lower:
                        buzz = v
                        break
            score.reddit_buzz_score = float(buzz) if buzz is not None else 0.0
            sources.append("reddit")

        # --- Autocomplete ---
        if autocomplete_data:
            score.search_volume_proxy = self._autocomplete_score(autocomplete_data, keyword)
            sources.append("google_autocomplete")

        # --- Composite ---
        w = self._INTERNAL_WEIGHTS
        score.overall_trend_score = round(
            score.google_trend_score * w["google"]
            + score.reddit_buzz_score * w["reddit"]
            + score.search_volume_proxy * w["autocomplete"],
            2,
        )
        score.sources = sources
        return score

    def score_keywords(
        self,
        keywords: List[str],
        google_data: Optional[Dict] = None,
        reddit_data: Optional[Dict] = None,
        autocomplete_data: Optional[Dict] = None,
    ) -> List[TrendScore]:
        """Score a list of keywords and return sorted by overall_trend_score desc."""
        scores = [
            self.calculate_trend_score(kw, google_data, reddit_data, autocomplete_data)
            for kw in keywords
        ]
        scores.sort(key=lambda s: s.overall_trend_score, reverse=True)
        return scores
