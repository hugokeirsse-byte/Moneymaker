"""
OpportunityValidator — Pilier 3 : validation transparente des opportunités.

Pour CHAQUE tendance proposée (par Gemini ou par l'arbre de niches), ce module
calcule un score d'opportunité 0-100 décomposé en 6 composants, où CHAQUE
composant est une `Metric` tracée (MEASURED / HEURISTIC / UNAVAILABLE). On sait
donc exactement quelle part du score repose sur de vraies données mesurées.

RÈGLE NON NÉGOCIABLE : zéro donnée inventée. Une valeur n'est MEASURED que si
elle vient d'une source réelle (Wikipedia pageviews). Tout le reste est
explicitement HEURISTIC (opinion Gemini / règles internes) ou UNAVAILABLE.

────────────────────────────────────────────────────────────────────────────
FORMULE DE MÉLANGE (documentée et auditable)
────────────────────────────────────────────────────────────────────────────
    opportunity_score =
          0.30 × demand
        + 0.15 × growth
        + 0.25 × competition      (LOW competition = score ÉLEVÉ = bon)
        + 0.10 × visual_potential
        + 0.10 × reusability
        + 0.10 × platform_fit

Chaque composant est borné 0-100. Les poids somment à 1.0.

Briques d'explicabilité attachées à chaque tendance :
    #1 score_breakdown   : décomposition complète (les 6 Metrics)
    #2 confidence        : ledger.reliability (part MESURÉE — distincte du score)
    #3 signals           : sources, mots-clés déclencheurs, catégories, notes
    #6 saturation        : niveau d'exploitation du marché (inverse de competition)
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional

from trend_discovery.provenance import Metric, ProvenanceLedger

logger = logging.getLogger(__name__)


# ── Poids de la formule de mélange (somme = 1.0) ──────────────────────────────
WEIGHTS: Dict[str, float] = {
    "demand": 0.30,
    "growth": 0.15,
    "competition": 0.25,
    "visual_potential": 0.10,
    "reusability": 0.10,
    "platform_fit": 0.10,
}

# Mapping niveau de compétition → score (LOW competition = BON = score élevé)
_COMPETITION_SCORE = {
    "low": 90.0,
    "medium": 60.0,
    "high": 35.0,
    "very_high": 15.0,
}


class OpportunityValidator:
    """
    Calcule un score d'opportunité transparent et le rattache à chaque tendance.

    Ne plante JAMAIS sur une erreur réseau : tout appel provider est protégé et
    dégrade proprement vers HEURISTIC / UNAVAILABLE.
    """

    def __init__(self, wiki=None):
        """
        Args:
            wiki: WikipediaProvider (instancié si absent). Tolère un échec
                d'instanciation (réseau / import) → reste à None.
        """
        if wiki is not None:
            self._wiki = wiki
        else:
            try:
                from trend_discovery.providers.wikipedia_provider import WikipediaProvider
                self._wiki = WikipediaProvider()
            except Exception as exc:
                logger.warning("[validator] WikipediaProvider indisponible: %s", exc)
                self._wiki = None

    # ── API publique ──────────────────────────────────────────────────────────
    def validate(self, trends: List[Dict], profile) -> List[Dict]:
        """
        Score chaque tendance, attache les briques d'explicabilité, et retourne
        la liste re-triée par `opportunity_score` décroissant.

        Args:
            trends: liste de dicts de tendances (schéma Gemini).
            profile: MarketProfile ciblé (lu pour repeat_required notamment).

        Returns:
            La même liste, chaque dict enrichi, triée best-first.
        """
        for trend in trends:
            try:
                self._score_trend(trend, profile)
            except Exception as exc:  # filet de sécurité absolu
                logger.warning(
                    "[validator] échec scoring '%s': %s — score neutre",
                    trend.get("name", "?"), exc,
                )
                trend.setdefault("opportunity_score", 0.0)
                trend.setdefault("confidence", 0.0)
                trend.setdefault("score_breakdown", {})

        trends.sort(key=lambda t: t.get("opportunity_score", 0.0), reverse=True)
        return trends

    # ── Cœur du calcul ──────────────────────────────────────────────────────────
    def _score_trend(self, trend: Dict, profile) -> None:
        name = trend.get("name", "")

        demand = self._demand_metric(trend, name)
        growth = self._growth_metric(name)
        competition = self._competition_metric(trend)
        visual = self._visual_metric(trend)
        reusability = self._reusability_metric(trend)
        platform = self._platform_metric(trend, profile)

        components = {
            "demand": demand,
            "growth": growth,
            "competition": competition,
            "visual_potential": visual,
            "reusability": reusability,
            "platform_fit": platform,
        }

        # ── Mélange pondéré ──────────────────────────────────────────────────
        score = sum(WEIGHTS[k] * components[k].value for k in WEIGHTS)
        score = round(max(0.0, min(100.0, score)), 1)

        # ── Ledger de provenance (les 6 composants) ──────────────────────────
        ledger = ProvenanceLedger()
        for m in components.values():
            ledger.add(m)

        # ── Briques d'explicabilité ──────────────────────────────────────────
        comp_level = (trend.get("spoonflower_fit", {}) or {}).get("competition_level", "medium")
        trigger_keywords = self._collect_keywords(trend)

        trend["opportunity_score"] = score
        trend["score_breakdown"] = {k: m.to_dict() for k, m in components.items()}  # BRICK #1
        trend["confidence"] = ledger.reliability  # BRICK #2
        trend["provenance"] = ledger.summary()
        trend["demand_evidence"] = demand.detail or "UNAVAILABLE"

        notes = self._notes(components, comp_level)
        trend["signals"] = {  # BRICK #3
            "sources": ledger.real_sources,
            "trigger_keywords": trigger_keywords[:15],
            "categories": [
                trend.get("market_opportunity", ""),
                comp_level,
            ],
            "notes": notes,
        }

        # BRICK #6 — saturation = inverse de la compétition (haut = très exploité)
        trend["saturation"] = {
            "level": comp_level,
            "score": round(100.0 - competition.value, 1),
            "rationale": (
                f"compétition '{comp_level.replace('_', ' ')}' → "
                f"marché {'très exploité' if (100 - competition.value) >= 65 else 'modérément exploité' if (100 - competition.value) >= 40 else 'encore ouvert'}"
            ),
        }

        trend["reusability_detail"] = reusability.detail

    # ── Composant 1 : demande ─────────────────────────────────────────────────
    def _demand_metric(self, trend: Dict, name: str) -> Metric:
        """
        Demande réelle : meilleure valeur MESURÉE entre le nom et les mots-clés
        de prompt. Repli HEURISTIC sur le trending_score Gemini.
        """
        candidates: List[Metric] = []
        if self._wiki is not None:
            queries = [name] + self._collect_keywords(trend)[:4]
            for q in queries:
                if not q:
                    continue
                try:
                    m = self._wiki.demande_metric(q)
                    if m is not None and m.is_real:
                        candidates.append(m)
                except Exception as exc:
                    logger.debug("[validator] demande '%s' échouée: %s", q, exc)

        if candidates:
            return max(candidates, key=lambda m: m.value)

        # Repli : opinion Gemini → HEURISTIC explicite
        gem = float(trend.get("trending_score", 50) or 50)
        return Metric.heuristic(
            value=max(0.0, min(100.0, gem)),
            source="gemini",
            confidence=40.0,
            detail=f"score Gemini {gem:.0f} (heuristique, aucune mesure Wikipedia)",
        )

    # ── Composant 2 : croissance ──────────────────────────────────────────────
    def _growth_metric(self, name: str) -> Metric:
        if self._wiki is not None and name:
            try:
                m = self._wiki.croissance_metric(name)
                if m is not None and m.is_real:
                    return m
            except Exception as exc:
                logger.debug("[validator] croissance '%s' échouée: %s", name, exc)
        return Metric.heuristic(
            value=50.0, source="internal_rules", confidence=30.0,
            detail="croissance neutre (aucune mesure Wikipedia)",
        )

    # ── Composant 3 : compétition (LOW = bon) ─────────────────────────────────
    def _competition_metric(self, trend: Dict) -> Metric:
        level = (trend.get("spoonflower_fit", {}) or {}).get("competition_level", "medium")
        value = _COMPETITION_SCORE.get(str(level).lower(), 60.0)
        return Metric.heuristic(
            value=value, source="gemini", confidence=40.0,
            detail=f"compétition '{level}' → score {value:.0f} (LOW=bon, opinion Gemini)",
        )

    # ── Composant 4 : potentiel visuel ────────────────────────────────────────
    def _visual_metric(self, trend: Dict) -> Metric:
        vd = trend.get("visual_direction", {}) or {}
        cp = vd.get("color_palette", {}) or {}
        score = 0.0
        reasons: List[str] = []

        primary = cp.get("primary", []) or []
        if len(primary) >= 3:
            score += 25
            reasons.append("≥3 couleurs primaires")
        if cp.get("accent"):
            score += 15
            reasons.append("accents")
        if vd.get("style_references"):
            score += 20
            reasons.append("références de style")
        if vd.get("line_style") and vd.get("texture"):
            score += 20
            reasons.append("trait+texture")
        if vd.get("mood"):
            score += 20
            reasons.append("mood")

        score = max(0.0, min(100.0, score))
        return Metric.heuristic(
            value=score, source="internal_rules", confidence=35.0,
            detail=f"richesse visuelle: {', '.join(reasons) or 'pauvre'}",
        )

    # ── Composant 5 : réutilisabilité ─────────────────────────────────────────
    def _reusability_metric(self, trend: Dict) -> Metric:
        """
        Estime combien de collections/séries cette niche peut engendrer :
        nombre de sous-niches + variété des mots-clés + angles distincts.
        """
        subs = [s for s in trend.get("sub_niches", []) if isinstance(s, dict)]
        n_subs = len(subs)

        distinct_kw = set()
        for s in subs:
            for kw in s.get("prompt_keywords", []) or []:
                if kw:
                    distinct_kw.add(str(kw).strip().lower())
        n_kw = len(distinct_kw)

        distinct_angles = len({
            (s.get("unique_angle", "") or "").strip().lower()
            for s in subs if (s.get("unique_angle", "") or "").strip()
        })

        # 0-100 : sous-niches (max ~50), mots-clés (max ~35), angles (max ~15)
        score = min(50.0, n_subs * 12.5) + min(35.0, n_kw * 3.5) + min(15.0, distinct_angles * 5.0)
        score = round(max(0.0, min(100.0, score)), 1)

        detail = (
            f"{n_subs} sous-niches, {n_kw} mots-clés distincts → "
            f"{'fort' if score >= 65 else 'moyen' if score >= 35 else 'faible'} potentiel de collections"
        )
        return Metric.heuristic(
            value=score, source="internal_rules", confidence=35.0, detail=detail,
        )

    # ── Composant 6 : adéquation plateforme ───────────────────────────────────
    def _platform_metric(self, trend: Dict, profile) -> Metric:
        sf = trend.get("spoonflower_fit", {}) or {}
        score = 0.0
        if sf.get("repeat_type"):
            score += 30
        if sf.get("scale"):
            score += 25
        if sf.get("top_products"):
            score += 25

        repeat_required = bool(getattr(profile, "repeat_required", False)) if profile else False
        if repeat_required:
            pos = (trend.get("ai_generation", {}) or {}).get("positive_prompt", "") or ""
            pl = pos.lower()
            if "seamless" in pl or "tileable" in pl or "tile" in pl:
                score += 20
        else:
            score += 20  # pas de contrainte de repeat → bonus neutre

        score = round(max(0.0, min(100.0, score)), 1)
        return Metric.heuristic(
            value=score, source="internal_rules", confidence=35.0,
            detail=f"complétude spoonflower_fit + repeat → {score:.0f}",
        )

    # ── Helpers ────────────────────────────────────────────────────────────────
    @staticmethod
    def _collect_keywords(trend: Dict) -> List[str]:
        """Mots-clés déclencheurs : key_elements + tous prompt_keywords des sous-niches."""
        kws: List[str] = []
        for kw in (trend.get("ai_generation", {}) or {}).get("key_elements", []) or []:
            if kw:
                kws.append(str(kw).strip())
        for s in trend.get("sub_niches", []):
            if isinstance(s, dict):
                for kw in s.get("prompt_keywords", []) or []:
                    if kw:
                        kws.append(str(kw).strip())
        # Dédup en préservant l'ordre
        return list(dict.fromkeys(k for k in kws if k))

    @staticmethod
    def _notes(components: Dict[str, Metric], comp_level: str) -> str:
        demand = components["demand"]
        bits = []
        if demand.is_real:
            bits.append(f"demande MESURÉE ({demand.source})")
        else:
            bits.append("demande heuristique (Gemini)")
        bits.append(f"compétition {comp_level.replace('_', ' ')}")
        if components["growth"].is_real:
            bits.append("croissance mesurée")
        return " · ".join(bits)
