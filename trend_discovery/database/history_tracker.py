"""
Phase 7 — Mémoire Historique.

Enregistre l'évolution des scores dans le temps.
Permet de mesurer quelles prédictions étaient bonnes/mauvaises.
Calcule la dérive de score, identifie les niches en accélération réelle.
"""
import json
import logging
import sqlite3
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class HistoryTracker:
    """
    Phase 7 — Tracks score evolution for every niche across runs.

    Uses the same SQLite database as OpportunityStore (shared connection).
    """

    def __init__(self, db_path: str = "./data/opportunities.db"):
        self._db_path = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row

    def record_snapshot(self, opp) -> None:
        """
        Append one score snapshot for an opportunity.
        Called after every pipeline run for each niche.
        """
        now = datetime.now(timezone.utc).isoformat()
        sources_json = json.dumps(list(getattr(opp, "sources", [])))
        cur = self._conn.cursor()
        cur.execute("""
            INSERT INTO score_history (
                niche, timestamp, score_final, demande, croissance,
                potentiel_visuel, potentiel_commercial, potentiel_hybridation,
                concurrence, sources
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            opp.niche,
            now,
            opp.score_final,
            opp.demande,
            opp.croissance,
            opp.potentiel_visuel,
            opp.potentiel_commercial,
            opp.potentiel_hybridation,
            opp.concurrence,
            sources_json,
        ))
        self._conn.commit()

    def record_batch(self, opps: List) -> None:
        """Record snapshots for a batch of opportunities."""
        for opp in opps:
            self.record_snapshot(opp)
        logger.info("Recorded %d history snapshots", len(opps))

    def get_history(self, niche: str, limit: int = 30) -> List[Dict]:
        """
        Return the most recent score history for a niche.

        Returns:
            List of dicts with timestamp and score components, newest first.
        """
        cur = self._conn.cursor()
        cur.execute("""
            SELECT * FROM score_history
            WHERE niche = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (niche, limit))
        return [dict(r) for r in cur.fetchall()]

    def get_score_evolution(self, niche: str) -> Dict:
        """
        Compute score evolution statistics for a niche.

        Returns:
            {
                "niche": str,
                "history_count": int,
                "first_score": float,
                "latest_score": float,
                "delta": float,           # latest - first
                "trend": str,             # "rising" | "stable" | "declining"
                "max_score": float,
                "min_score": float,
                "avg_score": float,
                "volatility": float,      # std deviation of scores
            }
        """
        history = self.get_history(niche, limit=100)
        if not history:
            return {"niche": niche, "history_count": 0}

        scores = [h["score_final"] for h in history]
        # history is newest-first, so reverse for chronological order
        scores_chron = list(reversed(scores))

        first = scores_chron[0]
        latest = scores_chron[-1]
        delta = latest - first
        avg = sum(scores) / len(scores)
        n = len(scores)
        variance = sum((s - avg) ** 2 for s in scores) / n
        import math
        volatility = math.sqrt(variance)

        if delta > 5:
            trend = "rising"
        elif delta < -5:
            trend = "declining"
        else:
            trend = "stable"

        return {
            "niche": niche,
            "history_count": n,
            "first_score": round(first, 2),
            "latest_score": round(latest, 2),
            "delta": round(delta, 2),
            "trend": trend,
            "max_score": round(max(scores), 2),
            "min_score": round(min(scores), 2),
            "avg_score": round(avg, 2),
            "volatility": round(volatility, 2),
        }

    def get_all_rising_niches(self, min_delta: float = 5.0, min_history: int = 2) -> List[Dict]:
        """
        Return niches whose score_final has increased by at least `min_delta`
        across their recorded history.
        """
        cur = self._conn.cursor()
        cur.execute("SELECT DISTINCT niche FROM score_history")
        niches = [r["niche"] for r in cur.fetchall()]

        rising = []
        for niche in niches:
            evo = self.get_score_evolution(niche)
            if (
                evo.get("history_count", 0) >= min_history
                and evo.get("delta", 0) >= min_delta
            ):
                rising.append(evo)

        rising.sort(key=lambda x: x["delta"], reverse=True)
        return rising

    def get_prediction_accuracy(self) -> Dict:
        """
        Meta-analysis: which past signals were actually predictive?

        Compares scores at detection vs 4 weeks later (if data exists).
        Returns accuracy metrics and a list of top predictive signals.
        """
        cur = self._conn.cursor()
        # Get niches with enough history
        cur.execute("""
            SELECT niche, COUNT(*) as cnt
            FROM score_history
            GROUP BY niche
            HAVING cnt >= 4
            ORDER BY cnt DESC
        """)
        niches_with_history = [r["niche"] for r in cur.fetchall()]

        correct_predictions = 0
        total_predictions = 0
        good_predictor_niches = []
        bad_predictor_niches = []

        for niche in niches_with_history:
            evo = self.get_score_evolution(niche)
            total_predictions += 1
            # "Good" prediction: score increased and we called it rising, or vice versa
            if evo["delta"] > 5 and evo["first_score"] > 50:
                correct_predictions += 1
                good_predictor_niches.append(niche)
            elif evo["delta"] < -5 and evo["first_score"] < 50:
                correct_predictions += 1
            else:
                bad_predictor_niches.append(niche)

        accuracy = (correct_predictions / total_predictions * 100) if total_predictions > 0 else 0

        return {
            "total_niches_tracked": total_predictions,
            "correct_predictions": correct_predictions,
            "accuracy_percent": round(accuracy, 1),
            "good_predictor_niches": good_predictor_niches[:10],
            "bad_predictor_niches": bad_predictor_niches[:10],
        }

    def get_historical_summary_table(self, top_n: int = 20) -> List[Dict]:
        """
        Return a summary table with score evolution for the top N niches.
        Used in report generation.
        """
        cur = self._conn.cursor()
        cur.execute("""
            SELECT niche FROM opportunities
            ORDER BY score_final DESC
            LIMIT ?
        """, (top_n,))
        niches = [r["niche"] for r in cur.fetchall()]
        return [self.get_score_evolution(n) for n in niches]

    def close(self):
        self._conn.close()
