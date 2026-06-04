"""
Profils de marché (MarketProfile) — cœur de la scalabilité du moteur.

Un MarketProfile décrit TOUT ce qui rend un marché POD spécifique
(Spoonflower, Redbubble, Society6, etc.) : ses produits, ses acheteurs,
ses signaux de recherche propres, ses contraintes d'export.

Le reste du moteur (prompt Gemini, validation, briefs) est alimenté PAR
ce profil — ce qui rend le système agnostique au marché : ajouter une
nouvelle plateforme = ajouter un MarketProfile, sans toucher au moteur.
"""
from trend_discovery.markets.market_profile import (
    MarketProfile,
    SPOONFLOWER,
    PROFILES,
    get_profile,
)

__all__ = ["MarketProfile", "SPOONFLOWER", "PROFILES", "get_profile"]
