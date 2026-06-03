"""
Module 02 — Moteur d'Allocation d'Opportunités Multi-Plateformes.

À partir d'une opportunité détectée (OpportunityScore du Module 01), ce package
produit une recommandation stratégique complète :
    "Quelle niche, sur quelle plateforme, pour quel produit, avec quelle priorité ?"

⚠️ HONNÊTETÉ DES DONNÉES :
Les scores de compatibilité par plateforme sont des SCORES STRUCTURELS basés sur
les profils de plateformes (connaissance structurelle légitime), à pondérer par
les vraies données de demande/concurrence du Module 01. Ce ne sont pas des
mesures de marché en temps réel.
"""
from trend_discovery.platform_router.allocator import (
    OpportunityAllocator,
    StrategicRecommendation,
)
from trend_discovery.platform_router.compatibility_matrix import CompatibilityMatrix
from trend_discovery.platform_router.economic_estimator import (
    EconomicEstimator,
    EconomicPotential,
)
from trend_discovery.platform_router.platform_profiles import (
    PLATFORM_PROFILES,
    PlatformProfile,
    all_platform_keys,
    get_profile,
)
from trend_discovery.platform_router.product_recommender import ProductRecommender
from trend_discovery.platform_router.strategy_reporter import StrategyReporter

__all__ = [
    "OpportunityAllocator",
    "StrategicRecommendation",
    "CompatibilityMatrix",
    "EconomicEstimator",
    "EconomicPotential",
    "ProductRecommender",
    "StrategyReporter",
    "PlatformProfile",
    "PLATFORM_PROFILES",
    "get_profile",
    "all_platform_keys",
]
