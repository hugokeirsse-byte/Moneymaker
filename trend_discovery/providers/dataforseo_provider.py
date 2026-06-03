"""
Provider DataForSEO — vrais volumes de recherche Google + compétition.

C'est la source PRINCIPALE de demande réelle du système.
DataForSEO expose les données du Google Keyword Planner :
    - volume de recherche mensuel moyen (chiffre réel)
    - niveau de compétition (0-1)
    - CPC moyen (signal de valeur commerciale)
    - tendance mensuelle sur 12 mois

Modèle : pay-as-you-go (pas d'abonnement). On met en cache agressivement
pour ne payer qu'une seule fois par mot-clé.

Authentification : login + mot de passe DataForSEO (Basic Auth).
    DATAFORSEO_LOGIN
    DATAFORSEO_PASSWORD

Coût indicatif : ~0,05 $ pour ~1000 mots-clés par requête "live".
Docs : https://docs.dataforseo.com/v3/keywords_data/google_ads/search_volume/live/
"""
from __future__ import annotations

import json
import logging
import os
from typing import Dict, List, Optional

import requests

from trend_discovery.providers.base_provider import DataProvider
from trend_discovery.provenance import Metric

logger = logging.getLogger(__name__)

DFS_BASE = "https://api.dataforseo.com/v3"


class DataForSEOProvider(DataProvider):
    key = "dataforseo"
    name = "DataForSEO (Google Keyword Planner)"
    required_env = ["DATAFORSEO_LOGIN", "DATAFORSEO_PASSWORD"]
    produces_measured_data = True

    def __init__(self, cache_path: str = "./data/cache_dataforseo.json"):
        super().__init__()
        self._login = os.getenv("DATAFORSEO_LOGIN", "")
        self._password = os.getenv("DATAFORSEO_PASSWORD", "")
        self._cache_path = cache_path
        self._cache: Dict[str, dict] = self._load_cache()

    def _check_credentials(self) -> bool:
        return bool(self._login and self._password)

    # ── Cache (pour ne payer qu'une fois par mot-clé) ────────────────────────
    def _load_cache(self) -> Dict[str, dict]:
        try:
            if os.path.exists(self._cache_path):
                with open(self._cache_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as exc:
            logger.warning("[dataforseo] cache load failed: %s", exc)
        return {}

    def _save_cache(self):
        try:
            os.makedirs(os.path.dirname(self._cache_path), exist_ok=True)
            with open(self._cache_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, ensure_ascii=False, indent=2)
        except Exception as exc:
            logger.warning("[dataforseo] cache save failed: %s", exc)

    # ── API ──────────────────────────────────────────────────────────────────
    def get_search_volumes(
        self,
        keywords: List[str],
        location_code: int = 2840,   # 2840 = United States
        language_code: str = "en",
        use_cache: bool = True,
    ) -> Dict[str, Dict]:
        """
        Retourne pour chaque mot-clé son volume de recherche mensuel réel,
        sa compétition et son CPC.

        Returns:
            {
              keyword: {
                "search_volume": int,        # recherches/mois (réel)
                "competition": float,        # 0-1 (réel)
                "competition_level": str,    # LOW/MEDIUM/HIGH
                "cpc": float,                # $ (réel)
                "monthly_trend": List[int],  # 12 derniers mois
              }
            }
        Mots-clés non disponibles → absents du dict.
        """
        if not self.is_available():
            return {}

        result: Dict[str, Dict] = {}
        to_fetch: List[str] = []

        # 1. Servir depuis le cache
        for kw in keywords:
            ck = kw.lower().strip()
            if use_cache and ck in self._cache:
                result[kw] = self._cache[ck]
            else:
                to_fetch.append(kw)

        if not to_fetch:
            logger.info("[dataforseo] %d mots-clés servis depuis le cache", len(result))
            return result

        # 2. Appel API pour le reste (par lots de 1000 max)
        chunks = [to_fetch[i:i + 700] for i in range(0, len(to_fetch), 700)]
        for chunk in chunks:
            payload = [{
                "keywords": chunk,
                "location_code": location_code,
                "language_code": language_code,
            }]
            try:
                resp = requests.post(
                    f"{DFS_BASE}/keywords_data/google_ads/search_volume/live",
                    auth=(self._login, self._password),
                    json=payload,
                    timeout=60,
                )
                resp.raise_for_status()
                data = resp.json()
                tasks = data.get("tasks", [])
                for task in tasks:
                    for item in (task.get("result") or []):
                        kw = item.get("keyword", "")
                        if not kw:
                            continue
                        record = {
                            "search_volume": item.get("search_volume") or 0,
                            "competition": item.get("competition_index", 0) / 100
                                if item.get("competition_index") is not None else 0.0,
                            "competition_level": item.get("competition", "UNKNOWN"),
                            "cpc": item.get("cpc") or 0.0,
                            "monthly_trend": [
                                m.get("search_volume", 0)
                                for m in (item.get("monthly_searches") or [])
                            ],
                        }
                        result[kw] = record
                        self._cache[kw.lower().strip()] = record
                logger.info("[dataforseo] %d mots-clés récupérés (API)", len(chunk))
            except requests.exceptions.RequestException as exc:
                logger.error("[dataforseo] erreur API: %s", exc)
            except Exception as exc:
                logger.error("[dataforseo] erreur parsing: %s", exc)

        self._save_cache()
        return result

    def demande_metric(self, keyword: str, volume_data: Dict) -> Metric:
        """
        Convertit un volume de recherche réel en Metric de demande (0-100),
        tracée comme MEASURED.

        Échelle logarithmique : 100 recherches→~30, 1k→~50, 10k→~70, 100k→~90.
        """
        rec = volume_data.get(keyword)
        if not rec:
            return Metric.unavailable(detail=f"Pas de volume DataForSEO pour '{keyword}'")
        vol = rec.get("search_volume", 0)
        if vol <= 0:
            return Metric.measured(0.0, source="dataforseo",
                                   confidence=80.0, detail="volume nul (réel)")
        import math
        score = min(100.0, max(0.0, (math.log10(vol + 1) / 6) * 100))
        return Metric.measured(
            round(score, 1), source="dataforseo", confidence=95.0,
            detail=f"{vol} recherches/mois (réel)",
        )

    def competition_metric(self, keyword: str, volume_data: Dict) -> Metric:
        """Compétition réelle Google Ads (0-100), tracée MEASURED."""
        rec = volume_data.get(keyword)
        if not rec:
            return Metric.unavailable(detail=f"Pas de compétition pour '{keyword}'")
        comp = rec.get("competition", 0.0) * 100
        return Metric.measured(
            round(comp, 1), source="dataforseo", confidence=90.0,
            detail=f"compétition Google Ads {comp:.0f}/100, CPC ${rec.get('cpc', 0):.2f}",
        )
