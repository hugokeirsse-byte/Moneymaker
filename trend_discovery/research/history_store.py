"""
HistoryStore — Brique #4 : historique des détections.

Enregistre chaque détection (une niche scorée) en JSON Lines pour suivre
l'évolution des opportunités dans le temps (un score qui monte run après run
est un signal fort). Best-effort : ne plante JAMAIS le pipeline.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List

logger = logging.getLogger(__name__)


class HistoryStore:
    """Journal append-only des détections (un objet JSON par ligne)."""

    def __init__(self, path: str = "data/detection_history.jsonl"):
        self._path = path

    # ── Écriture ────────────────────────────────────────────────────────────────
    def record(self, briefs, profile) -> None:
        """
        Ajoute une ligne JSON par brief détecté.

        Champs enregistrés : timestamp UTC, marché, niche, opportunity_score,
        confidence, niveau de compétition / saturation, sous-niches.

        Best-effort : toute erreur est journalisée mais jamais propagée.
        """
        try:
            directory = os.path.dirname(self._path)
            if directory:
                os.makedirs(directory, exist_ok=True)

            market_key = getattr(profile, "key", "") if profile else ""
            ts = datetime.now(timezone.utc).isoformat()

            with open(self._path, "a", encoding="utf-8") as f:
                for b in briefs or []:
                    saturation = getattr(b, "saturation", {}) or {}
                    sub_names = [getattr(s, "name", "") for s in getattr(b, "sub_niches", []) or []]
                    record = {
                        "timestamp": ts,
                        "market": market_key,
                        "niche": getattr(b, "name", ""),
                        "opportunity_score": getattr(b, "opportunity_score", 0.0),
                        "confidence": getattr(b, "confidence", 0.0),
                        "competition_level": getattr(b, "competition_level", ""),
                        "saturation_level": saturation.get("level", ""),
                        "sub_niches": [s for s in sub_names if s],
                    }
                    f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as exc:
            logger.warning("[history] enregistrement échoué: %s", exc)

    # ── Lecture ─────────────────────────────────────────────────────────────────
    def _read_all(self) -> List[Dict]:
        records: List[Dict] = []
        try:
            if not os.path.exists(self._path):
                return records
            with open(self._path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except Exception as exc:
            logger.warning("[history] lecture échouée: %s", exc)
        return records

    def history_for(self, niche_name: str) -> List[Dict]:
        """Retourne tous les enregistrements passés d'une niche (suivi d'évolution)."""
        target = (niche_name or "").strip().lower()
        return [r for r in self._read_all() if (r.get("niche", "") or "").strip().lower() == target]

    def summary(self) -> Dict:
        """Résumé global de l'historique."""
        records = self._read_all()
        timestamps = sorted({r.get("timestamp", "") for r in records if r.get("timestamp")})
        niches = {(r.get("niche", "") or "").strip().lower() for r in records if r.get("niche")}
        return {
            "total_runs": len(timestamps),
            "total_detections": len(records),
            "distinct_niches": len(niches),
            "last_run": timestamps[-1] if timestamps else None,
        }
