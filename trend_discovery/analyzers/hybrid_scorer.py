"""
Hybrid scorer — evaluates and ranks combinations of two niches for POD.
High hybrid score = trending + low competition + natural synergy.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from trend_discovery.analyzers.trend_scorer import TrendScore

logger = logging.getLogger(__name__)

# Pre-defined synergy matrix: pairs that work naturally together in POD.
# Score 0-100: how well two styles/niches combine visually and commercially.
SYNERGY_MATRIX: Dict[Tuple[str, str], float] = {
    ("botanical", "watercolor"): 90,
    ("botanical", "cottagecore"): 88,
    ("botanical", "art nouveau"): 85,
    ("floral", "watercolor"): 88,
    ("floral", "vintage"): 82,
    ("floral", "cottagecore"): 85,
    ("mushrooms", "cottagecore"): 92,
    ("mushrooms", "goblincore"): 90,
    ("mushrooms", "forest"): 88,
    ("celestial", "watercolor"): 85,
    ("celestial", "witchy"): 90,
    ("celestial", "dark academia"): 80,
    ("space", "geometric"): 82,
    ("space", "abstract"): 78,
    ("cats", "watercolor"): 85,
    ("cats", "abstract"): 72,
    ("foxes", "forest"): 88,
    ("foxes", "cottagecore"): 85,
    ("deer", "forest"): 86,
    ("deer", "cottagecore"): 82,
    ("geometric", "minimalist"): 88,
    ("geometric", "abstract"): 80,
    ("japanese", "botanical"): 88,
    ("japanese", "geometric"): 85,
    ("scandinavian", "geometric"): 82,
    ("scandinavian", "minimalist"): 90,
    ("moroccan", "geometric"): 88,
    ("art nouveau", "floral"): 90,
    ("retro", "geometric"): 80,
    ("retro", "abstract"): 75,
    ("ocean", "watercolor"): 85,
    ("ocean", "tropical"): 88,
    ("tropical", "watercolor"): 82,
    ("crystals", "celestial"): 90,
    ("crystals", "witchy"): 88,
    ("tarot", "celestial"): 88,
    ("tarot", "witchy"): 90,
    ("astrology", "celestial"): 92,
    ("bees", "botanical"): 88,
    ("bees", "cottagecore"): 85,
    ("butterflies", "botanical"): 90,
    ("butterflies", "watercolor"): 88,
    ("birds", "botanical"): 85,
    ("birds", "watercolor"): 82,
    ("halloween", "witchy"): 92,
    ("halloween", "gothic"): 88,
    ("christmas", "scandinavian"): 88,
    ("christmas", "retro"): 80,
    ("boho", "floral"): 85,
    ("boho", "geometric"): 80,
    ("solarpunk", "botanical"): 88,
    ("solarpunk", "geometric"): 80,
    ("cyberpunk", "geometric"): 82,
    ("cyberpunk", "space"): 80,
    ("fairycore", "botanical"): 90,
    ("fairycore", "mushrooms"): 88,
    ("dark academia", "botanical"): 82,
    ("dark academia", "vintage"): 85,
    ("japandi", "minimalist"): 90,
    ("japandi", "botanical"): 88,
}


@dataclass
class HybridNiche:
    niche1: str
    niche2: str
    combined_keyword: str
    hybrid_score: float = 0.0       # 0-100 overall
    trend_score: float = 0.0        # average trend of both niches
    uniqueness_score: float = 0.0   # inverse of competition
    synergy_score: float = 0.0      # from synergy matrix
    example_products: List[str] = field(default_factory=list)


class HybridScorer:
    """Generates and scores hybrid niche combinations for POD."""

    def _get_synergy(self, niche1: str, niche2: str) -> float:
        """Look up synergy score; symmetric lookup with fallback."""
        n1, n2 = niche1.lower(), niche2.lower()
        score = SYNERGY_MATRIX.get((n1, n2)) or SYNERGY_MATRIX.get((n2, n1))
        if score is not None:
            return float(score)
        # Partial match fallback
        for (a, b), v in SYNERGY_MATRIX.items():
            if (n1 in a or a in n1) and (n2 in b or b in n2):
                return float(v)
            if (n2 in a or a in n2) and (n1 in b or b in n1):
                return float(v)
        # Default: moderate synergy for unknown pairs
        return 50.0

    def _example_products(self, niche1: str, niche2: str) -> List[str]:
        templates = [
            f"{niche1.title()} {niche2.title()} Seamless Pattern",
            f"{niche2.title()} {niche1.title()} Fabric Design",
            f"Repeat {niche1.title()} {niche2.title()} Pattern",
            f"{niche1.title()} {niche2.title()} Surface Design",
        ]
        return templates

    def calculate_hybrid_score(
        self,
        niche1: str,
        niche2: str,
        trend_scores: Optional[Dict[str, TrendScore]] = None,
        competition_data: Optional[Dict[str, Dict]] = None,
    ) -> HybridNiche:
        """
        Compute a HybridNiche score for a pair of niches.

        Args:
            niche1, niche2:   The two niches to combine.
            trend_scores:     {keyword: TrendScore} mapping.
            competition_data: {keyword: competition_dict} from RedbubbleScraper.
        """
        combined = f"{niche1} {niche2}"

        # Trend: average of both
        trend1 = trend_scores.get(niche1).overall_trend_score if (trend_scores and niche1 in trend_scores) else 40.0
        trend2 = trend_scores.get(niche2).overall_trend_score if (trend_scores and niche2 in trend_scores) else 40.0
        avg_trend = (trend1 + trend2) / 2

        # Uniqueness: from competition data on the combined keyword
        if competition_data and combined in competition_data:
            uniqueness = competition_data[combined].get("opportunity_score", 60.0)
        elif competition_data and niche1 in competition_data and niche2 in competition_data:
            opp1 = competition_data[niche1].get("opportunity_score", 60.0)
            opp2 = competition_data[niche2].get("opportunity_score", 60.0)
            # Combined niche is typically less contested than either solo
            uniqueness = min(100.0, (opp1 + opp2) / 2 + 10)
        else:
            uniqueness = 65.0  # default optimistic for unknown pairs

        synergy = self._get_synergy(niche1, niche2)

        # Overall: weighted composite
        hybrid_score = round(avg_trend * 0.40 + uniqueness * 0.35 + synergy * 0.25, 2)

        return HybridNiche(
            niche1=niche1,
            niche2=niche2,
            combined_keyword=combined,
            hybrid_score=hybrid_score,
            trend_score=round(avg_trend, 2),
            uniqueness_score=round(uniqueness, 2),
            synergy_score=round(synergy, 2),
            example_products=self._example_products(niche1, niche2),
        )

    def generate_hybrid_niches(
        self,
        scored_niches: List[TrendScore],
        competition_data: Optional[Dict[str, Dict]] = None,
        top_n_source: int = 15,
        max_hybrids: int = 30,
    ) -> List[HybridNiche]:
        """
        From the top N trend-scored niches, generate all pairwise hybrids,
        score them, and return the top max_hybrids sorted by hybrid_score.

        Args:
            scored_niches:    Output of TrendScorer.score_keywords().
            competition_data: Optional competition dict per keyword.
            top_n_source:     How many top niches to consider for pairing.
            max_hybrids:      How many hybrid results to return.
        """
        trend_map: Dict[str, TrendScore] = {s.keyword: s for s in scored_niches}
        pool = [s.keyword for s in scored_niches[:top_n_source]]

        hybrids: List[HybridNiche] = []
        seen = set()
        for i, n1 in enumerate(pool):
            for n2 in pool[i + 1:]:
                pair = tuple(sorted([n1, n2]))
                if pair in seen:
                    continue
                seen.add(pair)
                h = self.calculate_hybrid_score(n1, n2, trend_map, competition_data)
                hybrids.append(h)

        # Also add curated synergy pairs from the matrix that might not be in pool
        for (a, b) in list(SYNERGY_MATRIX.keys())[:20]:
            pair = tuple(sorted([a, b]))
            if pair not in seen:
                seen.add(pair)
                h = self.calculate_hybrid_score(a, b, trend_map, competition_data)
                if h.hybrid_score > 60:
                    hybrids.append(h)

        hybrids.sort(key=lambda h: h.hybrid_score, reverse=True)
        return hybrids[:max_hybrids]
