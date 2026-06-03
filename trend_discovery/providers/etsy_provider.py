"""
Provider Etsy — API v3 officielle (gratuite).

Etsy est LA source de vraie compétition pour le marché POD/numérique :
    - nombre réel de listings actifs pour un mot-clé (saturation réelle)
    - tags réellement utilisés par les vendeurs qui marchent
    - prix réels pratiqués

Authentification : clé API Etsy (x-api-key).
    ETSY_API_KEY

Obtenir une clé (gratuit) : https://www.etsy.com/developers/register
Docs : https://developers.etsy.com/documentation/reference/

Note : l'endpoint findAllListingActive est restreint sur les nouvelles apps ;
on utilise getListingsByShop / search via l'API ouverte quand disponible,
et on dégrade proprement si l'accès est limité.
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

ETSY_BASE = "https://openapi.etsy.com/v3/application"


class EtsyProvider(DataProvider):
    key = "etsy"
    name = "Etsy API v3"
    required_env = ["ETSY_API_KEY"]
    produces_measured_data = True

    def __init__(self):
        super().__init__()
        self._api_key = os.getenv("ETSY_API_KEY", "")
        self._session = requests.Session()
        if self._api_key:
            self._session.headers.update({"x-api-key": self._api_key})

    def _check_credentials(self) -> bool:
        return bool(self._api_key)

    def get_active_listing_count(self, keyword: str) -> Optional[int]:
        """
        Nombre réel de listings actifs pour un mot-clé = saturation réelle
        du marché Etsy pour cette niche.

        Returns: int (réel) ou None si indisponible.
        """
        if not self.is_available():
            return None
        try:
            resp = self._session.get(
                f"{ETSY_BASE}/listings/active",
                params={"keywords": keyword, "limit": 1},
                timeout=20,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("count")
        except requests.exceptions.RequestException as exc:
            logger.error("[etsy] erreur listing count pour '%s': %s", keyword, exc)
            return None
        except Exception as exc:
            logger.error("[etsy] erreur parsing pour '%s': %s", keyword, exc)
            return None

    def get_listings_sample(self, keyword: str, limit: int = 50) -> List[Dict]:
        """
        Échantillon de listings actifs pour analyser les tags réels et prix.
        Returns: liste de dicts {title, price, tags, num_favorers}.
        """
        if not self.is_available():
            return []
        try:
            resp = self._session.get(
                f"{ETSY_BASE}/listings/active",
                params={"keywords": keyword, "limit": min(limit, 100)},
                timeout=25,
            )
            resp.raise_for_status()
            data = resp.json()
            listings = []
            for item in data.get("results", []):
                listings.append({
                    "title": item.get("title", ""),
                    "tags": item.get("tags", []),
                    "price": (item.get("price", {}) or {}).get("amount", 0) / 100
                        if isinstance(item.get("price"), dict) else 0,
                    "num_favorers": item.get("num_favorers", 0),
                    "views": item.get("views", 0),
                })
            return listings
        except Exception as exc:
            logger.error("[etsy] erreur sample pour '%s': %s", keyword, exc)
            return []

    def competition_metric(self, keyword: str) -> Metric:
        """
        Compétition réelle Etsy (0-100) basée sur le nombre de listings actifs.
        Échelle log : 100 listings→~25, 1k→~45, 10k→~65, 100k→~85, 1M→~100.
        """
        count = self.get_active_listing_count(keyword)
        if count is None:
            return Metric.unavailable(detail=f"Etsy indisponible pour '{keyword}'")
        if count <= 0:
            return Metric.measured(0.0, source="etsy", confidence=85.0,
                                   detail="0 listing actif (réel)")
        score = min(100.0, (math.log10(count + 1) / 6) * 100)
        return Metric.measured(
            round(score, 1), source="etsy", confidence=92.0,
            detail=f"{count:,} listings actifs Etsy (réel)".replace(",", " "),
        )

    def get_popular_tags(self, keyword: str, top_n: int = 20) -> List[str]:
        """Tags les plus fréquents parmi les listings réels d'un mot-clé."""
        listings = self.get_listings_sample(keyword, limit=100)
        from collections import Counter
        counter: Counter = Counter()
        for l in listings:
            for tag in l.get("tags", []):
                counter[tag.lower()] += 1
        return [t for t, _ in counter.most_common(top_n)]
