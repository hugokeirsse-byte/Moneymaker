"""
Provider DuckDuckGo Autocomplete — expansion de sous-niches, gratuit, sans clé.

DuckDuckGo expose un endpoint d'autocomplétion permissif (contrairement à
Google qui bloque les datacenters). Utile pour découvrir les variantes et
sous-niches réellement recherchées autour d'un terme.

Aucune authentification.
Endpoint : https://duckduckgo.com/ac/?q=<query>&type=list
"""
from __future__ import annotations

import logging
import string
from typing import Dict, List

import requests

from trend_discovery.providers.base_provider import DataProvider

logger = logging.getLogger(__name__)

DDG_AC = "https://duckduckgo.com/ac/"


class DuckDuckGoProvider(DataProvider):
    key = "duckduckgo"
    name = "DuckDuckGo Autocomplete (gratuit, sans clé)"
    required_env = []
    produces_measured_data = False  # suggestions = signal qualitatif, pas une mesure

    def __init__(self):
        super().__init__()
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": "Mozilla/5.0 (compatible; Moneymaker/1.0)"})

    def _check_credentials(self) -> bool:
        return True

    def suggestions(self, query: str) -> List[str]:
        """Retourne les suggestions d'autocomplétion pour une requête."""
        try:
            resp = self._session.get(DDG_AC, params={"q": query, "type": "list"}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            # Format : [query, [suggestions...]]
            if isinstance(data, list) and len(data) >= 2 and isinstance(data[1], list):
                return [str(s) for s in data[1]]
            # Format alternatif : [{"phrase": ...}, ...]
            if isinstance(data, list) and data and isinstance(data[0], dict):
                return [d.get("phrase", "") for d in data if d.get("phrase")]
            return []
        except Exception as exc:
            logger.warning("[duckduckgo] suggestions '%s' échoué: %s", query, exc)
            return []

    def expand_niche(self, niche: str) -> List[str]:
        """
        Découvre les sous-niches d'un terme en combinant plusieurs requêtes
        (terme seul, + 'pattern', + 'design', + alphabet).
        """
        found: List[str] = []
        seeds = [niche, f"{niche} pattern", f"{niche} design"]
        for seed in seeds:
            found.extend(self.suggestions(seed))
        # Expansion alphabétique légère (a-f) pour découvrir plus de variantes
        for ch in string.ascii_lowercase[:6]:
            found.extend(self.suggestions(f"{niche} {ch}"))
        # Déduplication en préservant l'ordre
        return list(dict.fromkeys(found))

    def get_pod_landscape(self, seeds: List[str] = None) -> Dict[str, List[str]]:
        """Cartographie de sous-niches POD à partir de termes de départ."""
        seeds = seeds or [
            "seamless pattern", "surface pattern design", "fabric print",
            "repeat pattern", "botanical pattern", "cottagecore pattern",
        ]
        return {s: self.suggestions(s) for s in seeds}
