"""
Collecteur de données réelles.

Pont entre les providers (vraies APIs) et le moteur de scoring.
Pour chaque niche, interroge toutes les sources réelles disponibles et
produit des `Metric` tracés (MEASURED quand la donnée est réelle).

Si aucune source réelle n'est disponible, le collecteur retourne des
métriques UNAVAILABLE — le scoring saura alors que le résultat est
non fiable et le rapport l'indiquera clairement.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from trend_discovery.providers.provider_registry import ProviderRegistry
from trend_discovery.provenance import Metric, MetricKind

logger = logging.getLogger(__name__)


@dataclass
class NicheRealData:
    """Données réelles collectées pour une niche, chaque champ tracé."""
    niche: str
    demande: Metric
    croissance: Metric
    concurrence: Metric
    buzz: Metric
    # données brutes utiles pour le rapport
    raw: Dict = field(default_factory=dict)

    @property
    def has_real_demand(self) -> bool:
        return self.demande.is_real

    @property
    def real_source_count(self) -> int:
        return sum(1 for m in [self.demande, self.croissance, self.concurrence, self.buzz] if m.is_real)


class RealDataCollector:
    """
    Orchestre la collecte de vraies données via les providers disponibles.
    """

    def __init__(self, registry: Optional[ProviderRegistry] = None):
        self._registry = registry or ProviderRegistry()
        self._dataforseo = self._registry.get("dataforseo")
        self._etsy = self._registry.get("etsy")
        self._reddit = self._registry.get("reddit")
        self._youtube = self._registry.get("youtube")
        # Cache des volumes DataForSEO (batch)
        self._volume_cache: Dict[str, Dict] = {}

    def available_sources(self) -> List[str]:
        return [p.key for p in self._registry.available()]

    def prefetch_search_volumes(self, keywords: List[str]) -> None:
        """
        Pré-charge les volumes DataForSEO en un seul appel batch
        (économise les coûts : un seul appel pour tous les mots-clés).
        """
        if self._dataforseo and self._dataforseo.is_available():
            logger.info("[collector] pré-chargement DataForSEO pour %d mots-clés", len(keywords))
            self._volume_cache = self._dataforseo.get_search_volumes(keywords)

    def _croissance_from_trend(self, keyword: str) -> Metric:
        """Croissance réelle dérivée de la tendance mensuelle DataForSEO (12 mois)."""
        rec = self._volume_cache.get(keyword)
        if not rec or not rec.get("monthly_trend"):
            return Metric.unavailable(detail="pas de tendance mensuelle")
        trend = rec["monthly_trend"]
        if len(trend) < 4:
            return Metric.unavailable(detail="historique insuffisant")
        # Pente normalisée : compare la moyenne des 3 derniers mois aux 3 premiers
        recent = sum(trend[-3:]) / 3
        old = sum(trend[:3]) / 3
        if old <= 0:
            return Metric.measured(60.0, source="dataforseo", confidence=70.0,
                                   detail="nouvelle tendance (réel)")
        growth_pct = (recent - old) / old * 100
        # Remap : -50%→20, 0%→50, +100%→90
        score = max(0.0, min(100.0, 50 + growth_pct / 2))
        return Metric.measured(
            round(score, 1), source="dataforseo", confidence=85.0,
            detail=f"évolution {growth_pct:+.0f}% sur 12 mois (réel)",
        )

    def collect(self, niche: str) -> NicheRealData:
        """
        Collecte toutes les vraies données disponibles pour une niche.
        Les champs sans source réelle sont marqués UNAVAILABLE.
        """
        raw: Dict = {}

        # ── Demande : DataForSEO (priorité) sinon YouTube ────────────────────
        demande = Metric.unavailable(detail="aucune source de demande")
        if self._dataforseo and self._dataforseo.is_available():
            demande = self._dataforseo.demande_metric(niche, self._volume_cache)
            if niche in self._volume_cache:
                raw["search_volume"] = self._volume_cache[niche].get("search_volume")
                raw["cpc"] = self._volume_cache[niche].get("cpc")
        if not demande.is_real and self._youtube and self._youtube.is_available():
            demande = self._youtube.demand_metric(niche)

        # ── Croissance : tendance mensuelle DataForSEO ───────────────────────
        croissance = Metric.unavailable(detail="aucune source de croissance")
        if self._dataforseo and self._dataforseo.is_available():
            croissance = self._croissance_from_trend(niche)

        # ── Concurrence : Etsy (priorité) sinon DataForSEO ───────────────────
        concurrence = Metric.unavailable(detail="aucune source de concurrence")
        if self._etsy and self._etsy.is_available():
            concurrence = self._etsy.competition_metric(niche)
        if not concurrence.is_real and self._dataforseo and self._dataforseo.is_available():
            concurrence = self._dataforseo.competition_metric(niche, self._volume_cache)

        # ── Buzz : Reddit ────────────────────────────────────────────────────
        buzz = Metric.unavailable(detail="aucune source de buzz")
        if self._reddit and self._reddit.is_available():
            buzz = self._reddit.buzz_metric(niche)

        return NicheRealData(
            niche=niche,
            demande=demande,
            croissance=croissance,
            concurrence=concurrence,
            buzz=buzz,
            raw=raw,
        )

    def collect_batch(self, niches: List[str], prefetch: bool = True) -> Dict[str, NicheRealData]:
        """Collecte pour une liste de niches. Pré-charge les volumes d'abord."""
        if prefetch:
            self.prefetch_search_volumes(niches)
        return {n: self.collect(n) for n in niches}
