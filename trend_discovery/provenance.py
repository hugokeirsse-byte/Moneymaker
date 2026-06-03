"""
Traçabilité des données (data provenance).

RÈGLE FONDAMENTALE DU SYSTÈME :
    Le système ne doit JAMAIS déguiser une estimation en mesure réelle.

Chaque valeur numérique manipulée par le moteur est encapsulée dans un objet
`Metric` qui porte explicitement :
    - sa valeur
    - sa nature : MEASURED (vraie donnée d'une source réelle),
                  HEURISTIC (estimation/règle interne), ou UNAVAILABLE (manquant)
    - sa source (nom du provider qui l'a produite)
    - sa confiance (0-100)

Ainsi, n'importe quel score final peut être audité : on sait exactement
quelle part repose sur de vraies recherches et quelle part sur des heuristiques.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

logger = logging.getLogger(__name__)


class MetricKind(str, Enum):
    """Nature d'une valeur — détermine si elle est fiable ou estimée."""
    MEASURED = "measured"        # vraie donnée mesurée par une source réelle
    HEURISTIC = "heuristic"      # estimation basée sur une règle interne
    UNAVAILABLE = "unavailable"  # donnée non disponible (aucune source)


@dataclass
class Metric:
    """
    Une valeur tracée. Toujours utiliser ceci au lieu d'un float nu pour
    toute donnée qui alimente un score.
    """
    value: float
    kind: MetricKind = MetricKind.UNAVAILABLE
    source: str = ""
    confidence: float = 0.0  # 0-100
    detail: str = ""
    captured_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def is_real(self) -> bool:
        """True uniquement si la valeur provient d'une vraie source mesurée."""
        return self.kind == MetricKind.MEASURED

    @classmethod
    def measured(cls, value: float, source: str, confidence: float = 90.0, detail: str = "") -> "Metric":
        return cls(value=value, kind=MetricKind.MEASURED, source=source,
                   confidence=confidence, detail=detail)

    @classmethod
    def heuristic(cls, value: float, source: str = "internal_rules", confidence: float = 40.0, detail: str = "") -> "Metric":
        return cls(value=value, kind=MetricKind.HEURISTIC, source=source,
                   confidence=confidence, detail=detail)

    @classmethod
    def unavailable(cls, detail: str = "") -> "Metric":
        return cls(value=0.0, kind=MetricKind.UNAVAILABLE, source="", confidence=0.0, detail=detail)

    def to_dict(self) -> dict:
        return {
            "value": round(self.value, 2),
            "kind": self.kind.value,
            "source": self.source,
            "confidence": round(self.confidence, 1),
            "detail": self.detail,
        }


@dataclass
class ProvenanceLedger:
    """
    Agrège les métriques d'un calcul de score pour produire un rapport
    de fiabilité : quelle part du score repose sur du réel vs de l'heuristique.
    """
    metrics: List[Metric] = field(default_factory=list)

    def add(self, metric: Metric) -> Metric:
        self.metrics.append(metric)
        return metric

    @property
    def measured_count(self) -> int:
        return sum(1 for m in self.metrics if m.kind == MetricKind.MEASURED)

    @property
    def heuristic_count(self) -> int:
        return sum(1 for m in self.metrics if m.kind == MetricKind.HEURISTIC)

    @property
    def unavailable_count(self) -> int:
        return sum(1 for m in self.metrics if m.kind == MetricKind.UNAVAILABLE)

    @property
    def reliability(self) -> float:
        """
        Part du score basée sur de vraies mesures (0-100).
        100 = entièrement basé sur des données réelles.
        0 = entièrement heuristique/manquant.
        """
        total = len(self.metrics)
        if total == 0:
            return 0.0
        # measured = 1.0, heuristic = 0.3, unavailable = 0.0
        weighted = sum(
            1.0 if m.kind == MetricKind.MEASURED
            else 0.3 if m.kind == MetricKind.HEURISTIC
            else 0.0
            for m in self.metrics
        )
        return round((weighted / total) * 100, 1)

    @property
    def real_sources(self) -> List[str]:
        return sorted({m.source for m in self.metrics if m.kind == MetricKind.MEASURED and m.source})

    def reliability_label(self) -> str:
        r = self.reliability
        if r >= 75:
            return "🟢 FIABLE (données réelles)"
        elif r >= 45:
            return "🟡 MIXTE (réel + heuristique)"
        elif r >= 20:
            return "🟠 FAIBLE (majoritairement heuristique)"
        else:
            return "🔴 NON FIABLE (aucune donnée réelle)"

    def summary(self) -> dict:
        return {
            "reliability": self.reliability,
            "label": self.reliability_label(),
            "measured": self.measured_count,
            "heuristic": self.heuristic_count,
            "unavailable": self.unavailable_count,
            "real_sources": self.real_sources,
        }
