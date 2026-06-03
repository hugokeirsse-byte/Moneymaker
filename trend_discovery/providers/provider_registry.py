"""
Registre central des providers de données réelles.

Le pipeline interroge ce registre pour savoir quelles vraies sources sont
disponibles (clés configurées) et collecter les vraies données.

Ajouter un nouveau provider = ajouter une ligne dans _build().
"""
from __future__ import annotations

import logging
from typing import Dict, List

from trend_discovery.providers.base_provider import DataProvider

logger = logging.getLogger(__name__)


def _build() -> List[DataProvider]:
    providers: List[DataProvider] = []
    # ── Sources GRATUITES sans clé (toujours disponibles) ────────────────────
    try:
        from trend_discovery.providers.wikipedia_provider import WikipediaProvider
        providers.append(WikipediaProvider())
    except Exception as exc:
        logger.debug("Wikipedia non chargé: %s", exc)
    try:
        from trend_discovery.providers.duckduckgo_provider import DuckDuckGoProvider
        providers.append(DuckDuckGoProvider())
    except Exception as exc:
        logger.debug("DuckDuckGo non chargé: %s", exc)
    # ── Source payante optionnelle (vrais volumes Google) ────────────────────
    try:
        from trend_discovery.providers.dataforseo_provider import DataForSEOProvider
        providers.append(DataForSEOProvider())
    except Exception as exc:
        logger.debug("DataForSEO non chargé: %s", exc)
    try:
        from trend_discovery.providers.etsy_provider import EtsyProvider
        providers.append(EtsyProvider())
    except Exception as exc:
        logger.debug("Etsy non chargé: %s", exc)
    try:
        from trend_discovery.providers.reddit_provider import RedditProvider
        providers.append(RedditProvider())
    except Exception as exc:
        logger.debug("Reddit non chargé: %s", exc)
    try:
        from trend_discovery.providers.youtube_provider import YouTubeProvider
        providers.append(YouTubeProvider())
    except Exception as exc:
        logger.debug("YouTube non chargé: %s", exc)
    return providers


class ProviderRegistry:
    """Gère l'ensemble des providers et leur disponibilité."""

    def __init__(self):
        self._providers: Dict[str, DataProvider] = {p.key: p for p in _build()}

    def get(self, key: str) -> DataProvider:
        return self._providers.get(key)

    def available(self) -> List[DataProvider]:
        """Providers dont les clés sont configurées (donc utilisables)."""
        return [p for p in self._providers.values() if p.is_available()]

    def all(self) -> List[DataProvider]:
        return list(self._providers.values())

    def status_report(self) -> Dict:
        """État détaillé pour les rapports : qui est dispo, qui manque."""
        avail = self.available()
        return {
            "total": len(self._providers),
            "available_count": len(avail),
            "available": [p.key for p in avail],
            "missing": [
                {"key": p.key, "name": p.name, "required_env": p.required_env}
                for p in self._providers.values() if not p.is_available()
            ],
            "details": [p.status() for p in self._providers.values()],
        }

    def has_any_real_source(self) -> bool:
        """True si au moins une vraie source de données est disponible."""
        return len(self.available()) > 0
