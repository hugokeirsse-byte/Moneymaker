"""
Module 02 — Estimation du Potentiel Économique.

⚠️ HONNÊTETÉ DES DONNÉES :
Les valeurs produites ici sont des ESTIMATIONS STRUCTURELLES dérivées de deux
sources :
  1. Les composantes RÉELLES de l'OpportunityScore (Module 01) : demande,
     croissance, concurrence — issues de scrapers/scorers.
  2. Les SCORES DE COMPATIBILITÉ STRUCTURELLE par plateforme (Module 02), basés
     sur les profils de plateformes.

Ce ne sont PAS des prévisions de chiffre d'affaires réelles. Le "tier de revenu
estimé" est une étiquette qualitative relative, pas un montant en euros.
Toutes les hypothèses de calcul sont documentées dans les méthodes.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict

logger = logging.getLogger(__name__)


@dataclass
class EconomicPotential:
    """
    Synthèse du potentiel économique structurel d'une opportunité.

    Tous les scores sont normalisés 0-100 (sauf exploitable_markets_count).
    """

    sales_potential: float = 0.0        # 0-100, dérivé de demande/croissance (données réelles M01)
    competition_pressure: float = 0.0   # 0-100, dérivé de la concurrence (données réelles M01)
    reusability_score: float = 0.0      # 0-100, basé sur le nb de plateformes compatibles (structurel)
    exploitable_markets_count: int = 0  # nb de plateformes avec compat >= 60
    estimated_revenue_tier: str = "faible"  # "faible"/"moyen"/"élevé"/"premium" (qualitatif)
    notes: str = ""

    def summary(self) -> str:
        """Résumé lisible du potentiel économique."""
        return (
            f"Tier={self.estimated_revenue_tier} | "
            f"Ventes={self.sales_potential:.0f} "
            f"Pression concurrentielle={self.competition_pressure:.0f} "
            f"Réutilisabilité={self.reusability_score:.0f} "
            f"Marchés exploitables={self.exploitable_markets_count}"
        )


class EconomicEstimator:
    """
    Estime le potentiel économique structurel d'une opportunité en combinant
    les données réelles du Module 01 et les scores de compatibilité du Module 02.
    """

    # Seuil de compatibilité au-delà duquel une plateforme est considérée
    # comme un "marché exploitable".
    _EXPLOITABLE_THRESHOLD = 60.0
    # Seuil de compatibilité "élevée" pour le calcul de réutilisabilité.
    _HIGH_COMPAT_THRESHOLD = 70.0

    def _compute_sales_potential(self, opportunity_score) -> float:
        """
        Potentiel de ventes dérivé des DONNÉES RÉELLES de demande et de
        croissance du Module 01.

        Hypothèse : la demande actuelle pèse davantage (60%) que la croissance
        future (40%), car elle reflète un marché déjà actif.
        """
        demande = getattr(opportunity_score, "demande", 0.0) or 0.0
        croissance = getattr(opportunity_score, "croissance", 0.0) or 0.0
        raw = demande * 0.60 + croissance * 0.40
        return min(100.0, max(0.0, raw))

    def _compute_competition_pressure(self, opportunity_score) -> float:
        """
        Pression concurrentielle = composante concurrence du Module 01
        (DONNÉE RÉELLE). Plus c'est haut, plus le marché est saturé.
        """
        concurrence = getattr(opportunity_score, "concurrence", 0.0) or 0.0
        return min(100.0, max(0.0, concurrence))

    def _compute_reusability(self, platform_scores: Dict[str, float]) -> float:
        """
        Score de réutilisabilité STRUCTUREL : un design exploitable sur de
        nombreuses plateformes vaut plus qu'un design mono-plateforme.

        Hypothèse : on compte les plateformes avec une compatibilité élevée
        (>= 70) et on rapporte ce nombre au total des plateformes, avec un
        plafond à 100. La diversité des débouchés réduit le risque.
        """
        if not platform_scores:
            return 0.0
        total = len(platform_scores)
        high = sum(1 for s in platform_scores.values() if s >= self._HIGH_COMPAT_THRESHOLD)
        # Ratio de plateformes fortement compatibles, amplifié pour valoriser
        # la polyvalence (un design utilisable partout est rare et précieux).
        ratio = high / total if total else 0.0
        return min(100.0, ratio * 130.0)

    def _count_exploitable_markets(self, platform_scores: Dict[str, float]) -> int:
        """Nombre de plateformes avec compatibilité >= 60 (marchés exploitables)."""
        return sum(1 for s in platform_scores.values() if s >= self._EXPLOITABLE_THRESHOLD)

    def _revenue_tier(
        self,
        sales_potential: float,
        competition_pressure: float,
        reusability_score: float,
        exploitable_markets: int,
    ) -> str:
        """
        Tier de revenu QUALITATIF (pas un montant). Combine potentiel de ventes,
        diversité des débouchés et réutilisabilité, atténué par la concurrence.

        Hypothèse de calcul (note structurelle indicative) :
            indice = ventes×0.40 + réutilisabilité×0.25 + (marchés×8 plafonné 100)×0.20
                     − pression_concurrentielle×0.15
        """
        markets_score = min(100.0, exploitable_markets * 8.0)
        index = (
            sales_potential * 0.40
            + reusability_score * 0.25
            + markets_score * 0.20
            - competition_pressure * 0.15
        )
        index = min(100.0, max(0.0, index))
        if index >= 70:
            return "premium"
        if index >= 50:
            return "élevé"
        if index >= 30:
            return "moyen"
        return "faible"

    def estimate(self, opportunity_score, platform_scores: Dict[str, float]) -> EconomicPotential:
        """
        Calcule le potentiel économique structurel complet.

        Args:
            opportunity_score: OpportunityScore du Module 01 (données réelles).
            platform_scores:   Dict {platform_key: score_compat} du Module 02.

        Returns:
            EconomicPotential (ne lève jamais d'exception).
        """
        try:
            platform_scores = platform_scores or {}

            sales = self._compute_sales_potential(opportunity_score)
            pressure = self._compute_competition_pressure(opportunity_score)
            reusability = self._compute_reusability(platform_scores)
            markets = self._count_exploitable_markets(platform_scores)
            tier = self._revenue_tier(sales, pressure, reusability, markets)

            notes = (
                f"Estimation structurelle : ventes dérivées de la demande "
                f"({getattr(opportunity_score, 'demande', 0):.0f}) et croissance "
                f"({getattr(opportunity_score, 'croissance', 0):.0f}) réelles (M01) ; "
                f"réutilisabilité et marchés exploitables dérivés des "
                f"compatibilités structurelles (M02). "
                f"Le tier '{tier}' est qualitatif, pas un montant en euros."
            )

            return EconomicPotential(
                sales_potential=round(sales, 1),
                competition_pressure=round(pressure, 1),
                reusability_score=round(reusability, 1),
                exploitable_markets_count=markets,
                estimated_revenue_tier=tier,
                notes=notes,
            )

        except Exception as exc:  # robustesse : jamais de crash
            logger.error("Erreur EconomicEstimator.estimate: %s", exc)
            return EconomicPotential(
                notes="Estimation indisponible suite à une erreur interne."
            )
