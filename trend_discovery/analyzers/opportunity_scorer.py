"""
Phase 5 — Scoring des Opportunités.

Formule :
    Score = (Demande + Croissance + Potentiel_Visuel
             + Potentiel_Commercial + Potentiel_Hybridation)
            - Concurrence

Chaque composante est normalisée 0-100.
La concurrence est soustraite avec un facteur d'atténuation pour éviter
les scores négatifs.

Score final : 0 - 100.
"""
import logging
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class OpportunityScore:
    # ── Identité ────────────────────────────────────────────────────────────
    niche: str
    canonical_name: Optional[str] = None  # normalized name if different from raw
    path: str = ""                          # tree path, e.g. "Nature > Herboristerie"

    # ── Composantes (0-100 chacune) ──────────────────────────────────────────
    demande: float = 0.0             # volume de recherche actuel
    croissance: float = 0.0          # vitesse de progression
    potentiel_visuel: float = 0.0    # facilité de génération d'images attractives
    potentiel_commercial: float = 0.0 # potentiel de revenu sur plateformes POD
    potentiel_hybridation: float = 0.0 # capacité à générer des sous-niches
    concurrence: float = 0.0         # niveau de saturation (+ = pire)

    # ── Score final ──────────────────────────────────────────────────────────
    score_final: float = 0.0         # 0-100, le critère de classement

    # ── Contexte ─────────────────────────────────────────────────────────────
    seasonality_flag: bool = False
    seasonality_note: str = ""
    sources: List[str] = field(default_factory=list)
    confidence: float = 0.0          # 0-100, confiance selon nb de sources

    # ── Traçabilité des données (provenance) ─────────────────────────────────
    reliability: float = 0.0         # 0-100 : part du score basée sur du réel
    reliability_label: str = "🔴 NON FIABLE (aucune donnée réelle)"
    real_sources: List[str] = field(default_factory=list)  # sources MEASURED
    provenance: dict = field(default_factory=dict)         # détail par composante

    def score_breakdown(self) -> str:
        """Human-readable breakdown of the score components."""
        return (
            f"Score={self.score_final:.1f} | "
            f"Demande={self.demande:.0f} Croissance={self.croissance:.0f} "
            f"Visuel={self.potentiel_visuel:.0f} Commercial={self.potentiel_commercial:.0f} "
            f"Hybridation={self.potentiel_hybridation:.0f} "
            f"Concurrence={self.concurrence:.0f}"
        )


class OpportunityScorer:
    """
    Calcule le score d'opportunité final pour une niche selon la formule
    du Module 01.

    Les données d'entrée proviennent des scrapers et des scorers existants
    (TrendScorer, FeasibilityScorer, HybridScorer).
    """

    # Poids relatifs des composantes positives (somme = 1.0)
    _POSITIVE_WEIGHTS = {
        "demande": 0.25,
        "croissance": 0.20,
        "potentiel_visuel": 0.20,
        "potentiel_commercial": 0.20,
        "potentiel_hybridation": 0.15,
    }
    # Poids de la pénalité concurrence (réduit le score mais ne le met pas à 0)
    _COMPETITION_PENALTY_FACTOR = 0.35

    def _compute_demande(
        self,
        google_score: float,
        reddit_score: float,
        autocomplete_score: float,
    ) -> float:
        """
        Mesure la demande actuelle.
        Combine Google Trends, buzz Reddit, et volume autocomplete.
        """
        weighted = (
            google_score * 0.50
            + reddit_score * 0.30
            + autocomplete_score * 0.20
        )
        return min(100.0, max(0.0, weighted))

    def _compute_croissance(
        self,
        trend_velocity: float,
        related_rising_count: int = 0,
    ) -> float:
        """
        Mesure la vitesse de progression.
        trend_velocity : -100 → +100 (de TrendScorer.calculate_momentum)
        related_rising_count : nb de requêtes "rising" associées sur Google Trends
        """
        # Remap velocity -100..+100 → 0..100
        velocity_score = (trend_velocity + 100) / 2
        rising_bonus = min(20.0, related_rising_count * 4.0)
        raw = velocity_score * 0.80 + rising_bonus * 0.20
        return min(100.0, max(0.0, raw))

    def _compute_potentiel_visuel(self, feasibility_score) -> float:
        """
        Mesure la capacité à générer des visuels attractifs.
        Utilise directement FeasibilityScore.
        """
        if feasibility_score is None:
            return 60.0  # valeur par défaut conservative
        # Blend: prompt clarity + seamless compatibility + color flexibility
        score = (
            feasibility_score.prompt_clarity * 0.40
            + feasibility_score.seamless_compatibility * 0.35
            + feasibility_score.color_flexibility * 0.25
        )
        return min(100.0, max(0.0, score))

    def _compute_potentiel_commercial(
        self,
        feasibility_commercial: float,
        platform_presence: float = 50.0,
        b2b_potential: float = 40.0,
    ) -> float:
        """
        Mesure le potentiel de revenu commercial.
        - feasibility_commercial : score commercial de FeasibilityScorer
        - platform_presence : présence sur les plateformes cibles
        - b2b_potential : potentiel de vente B2B (licences, etc.)
        """
        raw = (
            feasibility_commercial * 0.50
            + platform_presence * 0.30
            + b2b_potential * 0.20
        )
        return min(100.0, max(0.0, raw))

    def _compute_potentiel_hybridation(
        self,
        niche: str,
        hybrid_count: int = 0,
        avg_hybrid_score: float = 0.0,
        synergy_matrix_entries: int = 0,
    ) -> float:
        """
        Mesure la capacité de la niche à générer des combinaisons rentables.
        - hybrid_count : nombre de bons hybrides identifiés
        - avg_hybrid_score : score moyen des hybrides
        - synergy_matrix_entries : nb d'entrées dans la matrice de synergie
        """
        count_score = min(100.0, hybrid_count * 10.0)  # 10 hybrids = 100
        quality_score = avg_hybrid_score
        matrix_score = min(100.0, synergy_matrix_entries * 8.0)
        raw = count_score * 0.40 + quality_score * 0.40 + matrix_score * 0.20
        return min(100.0, max(0.0, raw))

    def _compute_concurrence(
        self,
        redbubble_competition: float = 50.0,
        spoonflower_competition: float = 50.0,
    ) -> float:
        """
        Mesure la saturation du marché.
        Higher = more competition = worse for us.
        """
        raw = redbubble_competition * 0.60 + spoonflower_competition * 0.40
        return min(100.0, max(0.0, raw))

    def _apply_formula(
        self,
        demande: float,
        croissance: float,
        potentiel_visuel: float,
        potentiel_commercial: float,
        potentiel_hybridation: float,
        concurrence: float,
    ) -> float:
        """
        Score Final = (Demande + Croissance + Potentiel_Visuel
                       + Potentiel_Commercial + Potentiel_Hybridation) / 5
                      × (1 - Concurrence × PENALTY_FACTOR / 100)

        La concurrence réduit le score mais ne peut pas le mettre à zéro
        (même avec concurrence=100, le multiplicateur est 1 - 0.35 = 0.65).
        """
        positive = (
            demande * self._POSITIVE_WEIGHTS["demande"]
            + croissance * self._POSITIVE_WEIGHTS["croissance"]
            + potentiel_visuel * self._POSITIVE_WEIGHTS["potentiel_visuel"]
            + potentiel_commercial * self._POSITIVE_WEIGHTS["potentiel_commercial"]
            + potentiel_hybridation * self._POSITIVE_WEIGHTS["potentiel_hybridation"]
        )
        competition_multiplier = 1.0 - (concurrence / 100.0 * self._COMPETITION_PENALTY_FACTOR)
        raw = positive * competition_multiplier
        return round(min(100.0, max(0.0, raw)), 2)

    def _confidence(self, sources: List[str]) -> float:
        """
        Score de confiance basé sur le nombre de sources consultées.
        Plus de sources = plus fiable.
        """
        weights = {
            "google_trends": 25,
            "reddit": 15,
            "google_autocomplete": 10,
            "redbubble": 25,
            "spoonflower": 15,
            "etsy": 10,
        }
        total = sum(weights.get(s, 5) for s in sources)
        max_possible = sum(weights.values())
        return min(100.0, (total / max_possible) * 100)

    def score_opportunity(
        self,
        niche: str,
        trend_score=None,
        feasibility_score=None,
        hybrid_scores: Optional[List] = None,
        competition_data: Optional[Dict] = None,
        tree_path: str = "",
        canonical_name: Optional[str] = None,
    ) -> OpportunityScore:
        """
        Calcule le score d'opportunité complet pour une niche.

        Args:
            niche:            Nom de la niche.
            trend_score:      TrendScore de TrendScorer.
            feasibility_score: FeasibilityScore de FeasibilityScorer.
            hybrid_scores:    Liste de HybridNiche impliquant cette niche.
            competition_data: Dict {niche: competition_dict} de RedBubble/Spoonflower.
            tree_path:        Chemin dans l'arbre de niches.
            canonical_name:   Nom canonique si différent.
        """
        sources = []

        # ── Demande ──────────────────────────────────────────────────────────
        google_score = 0.0
        reddit_score = 0.0
        autocomplete_score = 0.0
        trend_velocity = 0.0
        related_rising = 0

        if trend_score:
            google_score = trend_score.google_trend_score
            reddit_score = trend_score.reddit_buzz_score
            autocomplete_score = trend_score.search_volume_proxy
            trend_velocity = trend_score.trend_velocity
            sources.extend(trend_score.sources)

        demande = self._compute_demande(google_score, reddit_score, autocomplete_score)

        # ── Croissance ───────────────────────────────────────────────────────
        croissance = self._compute_croissance(trend_velocity, related_rising)

        # ── Potentiel Visuel ─────────────────────────────────────────────────
        potentiel_visuel = self._compute_potentiel_visuel(feasibility_score)

        # ── Potentiel Commercial ─────────────────────────────────────────────
        feas_commercial = feasibility_score.commercial_viability if feasibility_score else 70.0
        comp = competition_data.get(niche, {}) if competition_data else {}
        # Platform presence: low competition = platform is accessible
        platform_presence = comp.get("opportunity_score", 50.0)
        potentiel_commercial = self._compute_potentiel_commercial(
            feas_commercial, platform_presence
        )

        # ── Potentiel d'Hybridation ──────────────────────────────────────────
        related_hybrids = []
        if hybrid_scores:
            related_hybrids = [
                h for h in hybrid_scores
                if h.niche1.lower() == niche.lower() or h.niche2.lower() == niche.lower()
            ]
        hybrid_count = len(related_hybrids)
        avg_hybrid = (
            sum(h.hybrid_score for h in related_hybrids) / hybrid_count
            if related_hybrids else 0.0
        )
        potentiel_hybridation = self._compute_potentiel_hybridation(
            niche, hybrid_count, avg_hybrid
        )

        # ── Concurrence ──────────────────────────────────────────────────────
        rb_comp = comp.get("competition_score", 50.0)
        sf_comp = 50.0  # default; can be updated when Spoonflower data is available
        concurrence = self._compute_concurrence(rb_comp, sf_comp)

        if "redbubble" in str(comp):
            sources.append("redbubble")

        # ── Saisonnalité ─────────────────────────────────────────────────────
        seasonal_flag = False
        seasonal_note = ""
        if trend_score and trend_score.seasonality_score > 60:
            seasonal_flag = True
            seasonal_note = f"Score saisonnalité élevé ({trend_score.seasonality_score:.0f}/100)"

        # ── Score Final ───────────────────────────────────────────────────────
        score_final = self._apply_formula(
            demande, croissance, potentiel_visuel,
            potentiel_commercial, potentiel_hybridation, concurrence,
        )

        confidence = self._confidence(list(set(sources)))

        return OpportunityScore(
            niche=niche,
            canonical_name=canonical_name,
            path=tree_path,
            demande=round(demande, 1),
            croissance=round(croissance, 1),
            potentiel_visuel=round(potentiel_visuel, 1),
            potentiel_commercial=round(potentiel_commercial, 1),
            potentiel_hybridation=round(potentiel_hybridation, 1),
            concurrence=round(concurrence, 1),
            score_final=score_final,
            seasonality_flag=seasonal_flag,
            seasonality_note=seasonal_note,
            sources=list(set(sources)),
            confidence=round(confidence, 1),
        )

    def enrich_with_real_data(self, opp: "OpportunityScore", real_data) -> "OpportunityScore":
        """
        Remplace les composantes heuristiques par les VRAIES métriques mesurées
        quand elles sont disponibles, et calcule la fiabilité (provenance).

        `real_data` est un NicheRealData (providers.real_data_collector).
        Les composantes sans source réelle restent heuristiques et sont
        marquées comme telles dans le ledger.
        """
        from trend_discovery.provenance import Metric, MetricKind, ProvenanceLedger
        ledger = ProvenanceLedger()

        # ── Demande ──────────────────────────────────────────────────────────
        if real_data and real_data.demande.is_real:
            opp.demande = round(real_data.demande.value, 1)
            ledger.add(real_data.demande)
        else:
            ledger.add(Metric.heuristic(opp.demande, source="trend_scorer",
                                        detail="demande estimée (pas de source réelle)"))

        # ── Croissance ───────────────────────────────────────────────────────
        if real_data and real_data.croissance.is_real:
            opp.croissance = round(real_data.croissance.value, 1)
            ledger.add(real_data.croissance)
        else:
            ledger.add(Metric.heuristic(opp.croissance, source="trend_scorer",
                                        detail="croissance estimée"))

        # ── Concurrence ──────────────────────────────────────────────────────
        if real_data and real_data.concurrence.is_real:
            opp.concurrence = round(real_data.concurrence.value, 1)
            ledger.add(real_data.concurrence)
        else:
            ledger.add(Metric.heuristic(opp.concurrence, source="internal_rules",
                                        detail="concurrence estimée"))

        # ── Buzz → renforce la demande si mesuré ─────────────────────────────
        if real_data and real_data.buzz.is_real:
            ledger.add(real_data.buzz)
            # Le buzz réel tire légèrement la demande vers le haut
            opp.demande = round(min(100.0, opp.demande * 0.8 + real_data.buzz.value * 0.2), 1)

        # ── Potentiel visuel / hybridation : toujours heuristiques (légitimes) ─
        ledger.add(Metric.heuristic(opp.potentiel_visuel, source="feasibility_scorer",
                                    detail="potentiel visuel (règles de faisabilité)"))
        ledger.add(Metric.heuristic(opp.potentiel_hybridation, source="hybrid_scorer",
                                    detail="potentiel d'hybridation (matrice de synergie)"))

        # ── Recalcul du score final avec les vraies valeurs ──────────────────
        opp.score_final = self._apply_formula(
            opp.demande, opp.croissance, opp.potentiel_visuel,
            opp.potentiel_commercial, opp.potentiel_hybridation, opp.concurrence,
        )

        # ── Provenance ────────────────────────────────────────────────────────
        summary = ledger.summary()
        opp.reliability = summary["reliability"]
        opp.reliability_label = summary["label"]
        opp.real_sources = summary["real_sources"]
        opp.provenance = {
            "demande": real_data.demande.to_dict() if real_data else {},
            "croissance": real_data.croissance.to_dict() if real_data else {},
            "concurrence": real_data.concurrence.to_dict() if real_data else {},
            "buzz": real_data.buzz.to_dict() if real_data else {},
            "summary": summary,
        }
        # La confiance globale tient compte de la fiabilité réelle
        opp.confidence = round((opp.confidence + opp.reliability) / 2, 1)
        return opp

    def score_all(
        self,
        niches: List[str],
        trend_scores_map: Optional[Dict] = None,
        feasibility_scores_map: Optional[Dict] = None,
        hybrid_scores: Optional[List] = None,
        competition_data: Optional[Dict] = None,
        tree_paths: Optional[Dict] = None,
        canonical_names: Optional[Dict] = None,
        real_data_map: Optional[Dict] = None,
    ) -> List[OpportunityScore]:
        """
        Score a list of niches and return sorted by score_final descending.

        Si `real_data_map` ({niche: NicheRealData}) est fourni, les vraies
        données mesurées remplacent les heuristiques et la fiabilité est calculée.
        """
        results = []
        for niche in niches:
            ts = trend_scores_map.get(niche) if trend_scores_map else None
            fs = feasibility_scores_map.get(niche) if feasibility_scores_map else None
            path = tree_paths.get(niche, "") if tree_paths else ""
            canon = canonical_names.get(niche) if canonical_names else None
            opp = self.score_opportunity(
                niche=niche,
                trend_score=ts,
                feasibility_score=fs,
                hybrid_scores=hybrid_scores,
                competition_data=competition_data,
                tree_path=path,
                canonical_name=canon,
            )
            if real_data_map and niche in real_data_map:
                opp = self.enrich_with_real_data(opp, real_data_map[niche])
            results.append(opp)

        # Tri : fiabilité d'abord (le réel prime), puis score, puis confiance
        results.sort(key=lambda x: (x.reliability, x.score_final, x.confidence), reverse=True)
        return results
