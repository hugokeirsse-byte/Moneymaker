"""
Phase 6 — Base de données des opportunités.

SQLite persistant. Stocke chaque niche avec tous ses scores.
Permet les classements, filtres et exports.
"""
import json
import logging
import os
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = "./data/opportunities.db"


@dataclass
class Opportunity:
    niche: str
    canonical_name: Optional[str]
    path: str
    score_final: float
    demande: float
    croissance: float
    potentiel_visuel: float
    potentiel_commercial: float
    potentiel_hybridation: float
    concurrence: float
    confidence: float
    seasonality_flag: bool
    seasonality_note: str
    sources: List[str]
    first_detected: str = ""
    last_updated: str = ""
    detection_count: int = 1          # how many times this niche was detected


class OpportunityStore:
    """
    Phase 6 — SQLite store for ranked opportunities.

    Tables:
        opportunities  — one row per canonical niche (upsert on each run)
        score_history  — append-only score snapshots (feeds Phase 7)
        hybrids        — top hybrid niche pairs
    """

    def __init__(self, db_path: str = DEFAULT_DB_PATH):
        self._db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
        logger.info("OpportunityStore initialized at %s", db_path)

    def _init_schema(self):
        cur = self._conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS opportunities (
                niche               TEXT PRIMARY KEY,
                canonical_name      TEXT,
                path                TEXT DEFAULT '',
                score_final         REAL DEFAULT 0,
                demande             REAL DEFAULT 0,
                croissance          REAL DEFAULT 0,
                potentiel_visuel    REAL DEFAULT 0,
                potentiel_commercial REAL DEFAULT 0,
                potentiel_hybridation REAL DEFAULT 0,
                concurrence         REAL DEFAULT 0,
                confidence          REAL DEFAULT 0,
                seasonality_flag    INTEGER DEFAULT 0,
                seasonality_note    TEXT DEFAULT '',
                sources             TEXT DEFAULT '[]',
                first_detected      TEXT,
                last_updated        TEXT,
                detection_count     INTEGER DEFAULT 1
            );

            CREATE INDEX IF NOT EXISTS idx_opp_score ON opportunities(score_final DESC);

            CREATE TABLE IF NOT EXISTS score_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                niche           TEXT NOT NULL,
                timestamp       TEXT NOT NULL,
                score_final     REAL,
                demande         REAL,
                croissance      REAL,
                potentiel_visuel REAL,
                potentiel_commercial REAL,
                potentiel_hybridation REAL,
                concurrence     REAL,
                sources         TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_hist_niche ON score_history(niche, timestamp);

            CREATE TABLE IF NOT EXISTS hybrids (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                niche1      TEXT NOT NULL,
                niche2      TEXT NOT NULL,
                combined    TEXT NOT NULL,
                score       REAL,
                trend_score REAL,
                uniqueness  REAL,
                synergy     REAL,
                detected_at TEXT,
                UNIQUE(niche1, niche2)
            );
        """)
        self._conn.commit()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ── Upsert ───────────────────────────────────────────────────────────────

    def upsert_opportunity(self, opp) -> None:
        """
        Insert or update an opportunity.
        On conflict (same niche): update scores, increment detection_count.
        `opp` can be OpportunityScore or Opportunity.
        """
        now = self._now()
        sources_json = json.dumps(list(opp.sources))

        cur = self._conn.cursor()
        cur.execute("""
            INSERT INTO opportunities (
                niche, canonical_name, path, score_final, demande, croissance,
                potentiel_visuel, potentiel_commercial, potentiel_hybridation,
                concurrence, confidence, seasonality_flag, seasonality_note,
                sources, first_detected, last_updated, detection_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            ON CONFLICT(niche) DO UPDATE SET
                canonical_name      = excluded.canonical_name,
                path                = excluded.path,
                score_final         = excluded.score_final,
                demande             = excluded.demande,
                croissance          = excluded.croissance,
                potentiel_visuel    = excluded.potentiel_visuel,
                potentiel_commercial = excluded.potentiel_commercial,
                potentiel_hybridation = excluded.potentiel_hybridation,
                concurrence         = excluded.concurrence,
                confidence          = excluded.confidence,
                seasonality_flag    = excluded.seasonality_flag,
                seasonality_note    = excluded.seasonality_note,
                sources             = excluded.sources,
                last_updated        = excluded.last_updated,
                detection_count     = detection_count + 1
        """, (
            opp.niche,
            getattr(opp, "canonical_name", None),
            getattr(opp, "path", ""),
            opp.score_final,
            opp.demande,
            opp.croissance,
            opp.potentiel_visuel,
            opp.potentiel_commercial,
            opp.potentiel_hybridation,
            opp.concurrence,
            getattr(opp, "confidence", 0.0),
            int(getattr(opp, "seasonality_flag", False)),
            getattr(opp, "seasonality_note", ""),
            sources_json,
            now,
            now,
        ))
        self._conn.commit()

    def upsert_many(self, opps: List) -> None:
        """Bulk upsert a list of OpportunityScore or Opportunity objects."""
        for opp in opps:
            self.upsert_opportunity(opp)
        logger.info("Upserted %d opportunities into database", len(opps))

    def upsert_hybrid(self, hybrid) -> None:
        """Insert or update a hybrid niche pair."""
        now = self._now()
        cur = self._conn.cursor()
        cur.execute("""
            INSERT INTO hybrids (niche1, niche2, combined, score, trend_score, uniqueness, synergy, detected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(niche1, niche2) DO UPDATE SET
                score = excluded.score,
                trend_score = excluded.trend_score,
                uniqueness = excluded.uniqueness,
                synergy = excluded.synergy,
                detected_at = excluded.detected_at
        """, (
            hybrid.niche1, hybrid.niche2,
            getattr(hybrid, "combined_keyword", f"{hybrid.niche1} {hybrid.niche2}"),
            hybrid.hybrid_score,
            getattr(hybrid, "trend_score", 0),
            getattr(hybrid, "uniqueness_score", 0),
            getattr(hybrid, "synergy_score", 0),
            now,
        ))
        self._conn.commit()

    # ── Queries ──────────────────────────────────────────────────────────────

    def get_top_opportunities(self, limit: int = 20, min_confidence: float = 0) -> List[Dict]:
        """Return top N opportunities sorted by score_final."""
        cur = self._conn.cursor()
        cur.execute("""
            SELECT * FROM opportunities
            WHERE confidence >= ?
            ORDER BY score_final DESC
            LIMIT ?
        """, (min_confidence, limit))
        rows = cur.fetchall()
        return [dict(r) for r in rows]

    def get_opportunity(self, niche: str) -> Optional[Dict]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM opportunities WHERE niche = ?", (niche,))
        row = cur.fetchone()
        return dict(row) if row else None

    def get_top_hybrids(self, limit: int = 20) -> List[Dict]:
        cur = self._conn.cursor()
        cur.execute("SELECT * FROM hybrids ORDER BY score DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]

    def count(self) -> int:
        cur = self._conn.cursor()
        cur.execute("SELECT COUNT(*) FROM opportunities")
        return cur.fetchone()[0]

    def get_rising_opportunities(self, limit: int = 10) -> List[Dict]:
        """Opportunities with high croissance score — the emerging niches."""
        cur = self._conn.cursor()
        cur.execute("""
            SELECT * FROM opportunities
            ORDER BY croissance DESC, score_final DESC
            LIMIT ?
        """, (limit,))
        return [dict(r) for r in cur.fetchall()]

    def get_low_competition(self, limit: int = 10, max_concurrence: float = 40) -> List[Dict]:
        """Opportunities with low competition — quick wins."""
        cur = self._conn.cursor()
        cur.execute("""
            SELECT * FROM opportunities
            WHERE concurrence <= ?
            ORDER BY score_final DESC
            LIMIT ?
        """, (max_concurrence, limit))
        return [dict(r) for r in cur.fetchall()]

    def export_json(self, path: str, limit: int = 100) -> str:
        """Export top opportunities to a JSON file."""
        opps = self.get_top_opportunities(limit=limit)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(opps, f, indent=2, ensure_ascii=False)
        return path

    def close(self):
        self._conn.close()
