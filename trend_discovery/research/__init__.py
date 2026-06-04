"""
Pilier de recherche d'opportunités — validation transparente et traçable.

Ce package contient les briques d'explicabilité du moteur :
    - OpportunityValidator : score multi-composants, chaque composant étant une
      Metric tracée (MEASURED / HEURISTIC / UNAVAILABLE).
    - HistoryStore : historique des détections pour suivre l'évolution des niches.
"""
from __future__ import annotations

from trend_discovery.research.opportunity_validator import OpportunityValidator
from trend_discovery.research.history_store import HistoryStore

__all__ = ["OpportunityValidator", "HistoryStore"]
