"""
Cahiers des charges complets pour la production de motifs Spoonflower.

Ce module combine :
  - Les tendances Gemini (direction visuelle, palettes hex, références de style)
  - Les images de référence Wikimedia Commons (domaine public)
  - Les prompts IA Runware (positif + négatif, paramètres)

Résultat : des documents Markdown prêts à lire pour décider quels motifs générer.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class ReferenceImage:
    """Image de référence Wikimedia Commons (domaine public)."""
    title: str
    url: str
    width: int = 0
    height: int = 0


@dataclass
class SubNicheBrief:
    """Sous-niche avec angle unique et mots-clés de prompt."""
    name: str
    trending_score: int = 0
    unique_angle: str = ""
    prompt_keywords: List[str] = field(default_factory=list)


@dataclass
class ProductionBrief:
    """
    Cahier des charges complet pour un motif Spoonflower.

    Agrège toutes les informations nécessaires pour produire un motif
    seamless de qualité professionnelle : direction visuelle, palette,
    références, prompts IA, et spécifications Spoonflower.
    """

    # ── Identification ───────────────────────────────────────────────────────
    name: str
    trending_score: int
    market_opportunity: str
    why_trending: str
    target_audience: str
    sub_niches: List[SubNicheBrief]

    # ── Direction visuelle ───────────────────────────────────────────────────
    mood: str = ""
    composition: str = ""
    line_style: str = ""
    color_primary: List[str] = field(default_factory=list)
    color_accent: List[str] = field(default_factory=list)
    color_background: str = ""
    style_references: List[str] = field(default_factory=list)
    texture: str = ""

    # ── Spoonflower ──────────────────────────────────────────────────────────
    repeat_type: str = "basic"
    pattern_scale: str = "medium"
    top_products: List[str] = field(default_factory=list)
    competition_level: str = "medium"

    # ── Génération IA ────────────────────────────────────────────────────────
    positive_prompt: str = ""
    negative_prompt: str = ""
    key_elements: List[str] = field(default_factory=list)
    avoid_elements: List[str] = field(default_factory=list)
    cfg_scale: float = 7.5
    style_weight: float = 0.85

    # ── Références ───────────────────────────────────────────────────────────
    reference_images: List[ReferenceImage] = field(default_factory=list)
    generated_at: str = ""

    # ── Explicabilité (briques OpportunityValidator) ──────────────────────────
    opportunity_score: float = 0.0
    confidence: float = 0.0
    score_breakdown: dict = field(default_factory=dict)
    signals: dict = field(default_factory=dict)
    saturation: dict = field(default_factory=dict)
    reusability_detail: str = ""
    demand_evidence: str = ""

    # ── SEO (pour futur listing) ───────────────────────────────────────────────
    seo_keywords: List[str] = field(default_factory=list)
    title_seeds: List[str] = field(default_factory=list)

    # ── Type de niche ─────────────────────────────────────────────────────────
    crossover_gap: bool = False     # True = micro-niche crossover (communauté passionnée × gap marché)
    demand_gap_evidence: str = ""   # Preuve concrète de demande inassouvie (Reddit/Etsy/Pinterest)

    # ── Helpers ──────────────────────────────────────────────────────────────

    def opportunity_emoji(self) -> str:
        """Emoji couleur selon le niveau d'opportunité marché."""
        return {
            "very_high": "🟢",
            "high": "🟡",
            "medium": "🟠",
            "low": "🔴",
        }.get(self.market_opportunity, "⚪")

    def competition_emoji(self) -> str:
        """Emoji couleur selon le niveau de compétition."""
        return {
            "low": "🟢",
            "medium": "🟡",
            "high": "🟠",
            "very_high": "🔴",
        }.get(self.competition_level, "⚪")

    def to_markdown(self) -> str:
        """
        Génère un beau document Markdown complet.

        Contient : en-tête, analyse marché, palette couleurs, références de style,
        images Wikimedia, tableau des sous-niches, prompts IA en blocs de code,
        paramètres Runware, specs Spoonflower, checklist des éléments clés.
        """
        ts = self.generated_at or datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        lines: List[str] = []

        # ── En-tête ──────────────────────────────────────────────────────────
        crossover_badge = " &nbsp;🔀 **CROSSOVER GAP**" if self.crossover_gap else ""
        lines += [
            f"# {self.opportunity_emoji()} {self.name}{crossover_badge}",
            f"",
            f"> **Score tendance :** {self.trending_score}/100 &nbsp;|&nbsp; "
            f"**Opportunité marché :** {self.market_opportunity.replace('_', ' ').upper()} {self.opportunity_emoji()} &nbsp;|&nbsp; "
            f"**Généré le :** {ts}",
            f"",
            "---",
            "",
        ]

        # ── Preuve de demande inassouvie (crossover uniquement) ───────────────
        if self.crossover_gap and self.demand_gap_evidence:
            lines += [
                "> 🔀 **Preuve de demande inassouvie :** " + self.demand_gap_evidence,
                "",
            ]

        # ── Score & Fiabilité (briques d'explicabilité) ────────────────────────
        if self.opportunity_score or self.score_breakdown:
            prov_label = (self.signals or {}).get("provenance_label", "")
            lines += [
                "## Score & Fiabilité",
                "",
                f"- **Score d'opportunité :** {self.opportunity_score}/100",
                f"- **Fiabilité (confidence) :** {self.confidence}% "
                "_(part du score basée sur de vraies mesures)_",
            ]
            if prov_label:
                lines.append(f"- **Provenance :** {prov_label}")
            lines.append("")

            # ── Décomposition du score ─────────────────────────────────────────
            if self.score_breakdown:
                lines += [
                    "### Décomposition du Score",
                    "",
                    "| Composante | Valeur | Type | Source |",
                    "|------------|--------|------|--------|",
                ]
                for comp, m in self.score_breakdown.items():
                    if not isinstance(m, dict):
                        continue
                    lines.append(
                        f"| {comp.replace('_', ' ')} "
                        f"| {m.get('value', 0)}/100 "
                        f"| {str(m.get('kind', '')).upper()} "
                        f"| {m.get('source', '') or '—'} |"
                    )
                lines.append("")

            if self.demand_evidence:
                lines.append(f"**Demande mesurée :** {self.demand_evidence}")
                lines.append("")
            if isinstance(self.saturation, dict) and self.saturation:
                lines.append(
                    f"**Saturation :** {self.saturation.get('level', '?')} — "
                    f"{self.saturation.get('rationale', '')}"
                )
                lines.append("")
            if self.reusability_detail:
                lines.append(f"**Réutilisabilité :** {self.reusability_detail}")
                lines.append("")
            if isinstance(self.signals, dict) and self.signals:
                sources = ", ".join(self.signals.get("sources", []) or []) or "aucune source mesurée"
                triggers = ", ".join(self.signals.get("trigger_keywords", [])[:10] or [])
                lines.append(f"**Signaux utilisés :** sources = {sources}" + (f" · mots-clés = {triggers}" if triggers else ""))
                lines.append("")
            lines += ["---", ""]

        # ── Analyse marché ────────────────────────────────────────────────────
        lines += [
            "## Analyse Marché",
            "",
            f"**Pourquoi ça monte :** {self.why_trending}",
            "",
            f"**Audience cible :** {self.target_audience}",
            "",
        ]

        # ── Direction visuelle ────────────────────────────────────────────────
        lines += [
            "## Direction Visuelle",
            "",
        ]

        if self.mood:
            lines.append(f"- **Ambiance / Mood :** {self.mood}")
        if self.composition:
            lines.append(f"- **Composition :** {self.composition}")
        if self.line_style:
            lines.append(f"- **Style de trait :** {self.line_style}")
        if self.texture:
            lines.append(f"- **Texture :** {self.texture}")
        lines.append("")

        # ── Palette de couleurs ───────────────────────────────────────────────
        lines += [
            "## Palette de Couleurs",
            "",
        ]

        if self.color_primary:
            lines.append("**Couleurs primaires :**")
            for c in self.color_primary:
                # Try to extract hex code for display
                if "#" in c:
                    parts = c.split("#")
                    hex_part = parts[1][:6] if len(parts) > 1 else ""
                    name_part = parts[0].strip()
                    lines.append(f"  - `#{hex_part}` — {name_part}")
                else:
                    lines.append(f"  - {c}")
            lines.append("")

        if self.color_accent:
            lines.append("**Couleurs d'accentuation :**")
            for c in self.color_accent:
                if "#" in c:
                    parts = c.split("#")
                    hex_part = parts[1][:6] if len(parts) > 1 else ""
                    name_part = parts[0].strip()
                    lines.append(f"  - `#{hex_part}` — {name_part}")
                else:
                    lines.append(f"  - {c}")
            lines.append("")

        if self.color_background:
            if "#" in self.color_background:
                parts = self.color_background.split("#")
                hex_part = parts[1][:6] if len(parts) > 1 else ""
                name_part = parts[0].strip()
                lines.append(f"**Fond :** `#{hex_part}` — {name_part}")
            else:
                lines.append(f"**Fond :** {self.color_background}")
            lines.append("")

        # ── Références de style ───────────────────────────────────────────────
        if self.style_references:
            lines += [
                "## Références de Style",
                "",
            ]
            for ref in self.style_references:
                lines.append(f"- {ref}")
            lines.append("")

        # ── Images de référence Wikimedia ─────────────────────────────────────
        if self.reference_images:
            lines += [
                "## Images de Référence (Wikimedia Commons — Domaine Public)",
                "",
                "Ces images sont libres de droits et servent de références visuelles :",
                "",
            ]
            for img in self.reference_images:
                dims = f" ({img.width}×{img.height}px)" if img.width and img.height else ""
                lines.append(f"- [{img.title}{dims}]({img.url})")
            lines.append("")
        else:
            lines += [
                "## Images de Référence",
                "",
                "_Aucune image de référence trouvée sur Wikimedia Commons pour cette requête._",
                "",
            ]

        # ── Sous-niches ───────────────────────────────────────────────────────
        if self.sub_niches:
            lines += [
                "## Sous-Niches à Explorer",
                "",
                "| # | Nom | Score | Angle Unique |",
                "|---|-----|-------|--------------|",
            ]
            for i, sub in enumerate(self.sub_niches, 1):
                angle = sub.unique_angle[:60] + "…" if len(sub.unique_angle) > 60 else sub.unique_angle
                lines.append(
                    f"| {i} | **{sub.name}** | {sub.trending_score}/100 | {angle} |"
                )
            lines.append("")

            # Mots-clés par sous-niche
            lines.append("**Mots-clés par sous-niche :**")
            lines.append("")
            for sub in self.sub_niches:
                if sub.prompt_keywords:
                    kws = ", ".join(f"`{k}`" for k in sub.prompt_keywords)
                    lines.append(f"- **{sub.name}** : {kws}")
            lines.append("")

        # ── Prompts IA ────────────────────────────────────────────────────────
        lines += [
            "## Prompts IA — Prêts à l'Emploi",
            "",
            "### Prompt Positif",
            "",
            "```",
            self.positive_prompt or "(prompt non généré)",
            "```",
            "",
            "### Prompt Négatif",
            "",
            "```",
            self.negative_prompt or "(prompt négatif non généré)",
            "```",
            "",
        ]

        # ── Checklist des éléments clés ───────────────────────────────────────
        if self.key_elements or self.avoid_elements:
            lines += [
                "## Checklist des Éléments",
                "",
            ]
            if self.key_elements:
                lines.append("**Doit OBLIGATOIREMENT apparaître :**")
                lines.append("")
                for el in self.key_elements:
                    lines.append(f"- [ ] {el}")
                lines.append("")
            if self.avoid_elements:
                lines.append("**À ÉVITER absolument :**")
                lines.append("")
                for el in self.avoid_elements:
                    lines.append(f"- {el}")
                lines.append("")

        # ── Paramètres Runware ────────────────────────────────────────────────
        lines += [
            "## Paramètres de Génération Runware",
            "",
            "| Paramètre | Valeur |",
            "|-----------|--------|",
            "| Modèle recommandé | `runware:101@1` (FLUX.1 Dev) |",
            "| Modèle alternatif | `runware:100@1` (SDXL) |",
            f"| CFG Scale | `{self.cfg_scale}` |",
            f"| Style Weight | `{self.style_weight}` |",
            "| Steps | `30` |",
            "| Taille | `1024×1024` px |",
            "| Upscale | `4×` → 4096×4096 px |",
            "| DPI Spoonflower | `300 DPI` minimum |",
            "",
        ]

        # ── Specs Spoonflower ─────────────────────────────────────────────────
        lines += [
            "## Spécifications Spoonflower",
            "",
            f"- **Type de repeat :** {self.repeat_type}",
            f"- **Échelle du motif :** {self.pattern_scale}",
            f"- **Compétition :** {self.competition_level.replace('_', ' ')} {self.competition_emoji()}",
            "",
        ]

        if self.top_products:
            lines.append("**Produits recommandés :**")
            for prod in self.top_products:
                lines.append(f"- [ ] {prod.replace('_', ' ').title()}")
            lines.append("")

        lines += [
            "**Checklist export Spoonflower :**",
            "",
            "- [ ] Format PNG, fond transparent ou uni",
            "- [ ] 300 DPI minimum",
            "- [ ] 4500×4500 px minimum (= 15\" × 15\" à 300 DPI)",
            "- [ ] Tuile parfaite vérifiée (no visible seam)",
            "- [ ] Profil couleur sRGB",
            "",
        ]

        # ── SEO (pour futur listing) ───────────────────────────────────────────
        if self.seo_keywords or self.title_seeds:
            lines += [
                "## SEO (pour futur listing)",
                "",
            ]
            if self.seo_keywords:
                kws = ", ".join(f"`{k}`" for k in self.seo_keywords[:25])
                lines.append(f"**Mots-clés SEO :** {kws}")
                lines.append("")
            if self.title_seeds:
                lines.append("**Titres candidats :**")
                for t in self.title_seeds:
                    lines.append(f"- {t}")
                lines.append("")

        lines += ["---", ""]

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Sérialise le brief en dict pour export JSON."""
        return {
            "name": self.name,
            "trending_score": self.trending_score,
            "market_opportunity": self.market_opportunity,
            "why_trending": self.why_trending,
            "target_audience": self.target_audience,
            "sub_niches": [
                {
                    "name": s.name,
                    "trending_score": s.trending_score,
                    "unique_angle": s.unique_angle,
                    "prompt_keywords": s.prompt_keywords,
                }
                for s in self.sub_niches
            ],
            "visual_direction": {
                "mood": self.mood,
                "composition": self.composition,
                "line_style": self.line_style,
                "color_primary": self.color_primary,
                "color_accent": self.color_accent,
                "color_background": self.color_background,
                "style_references": self.style_references,
                "texture": self.texture,
            },
            "spoonflower": {
                "repeat_type": self.repeat_type,
                "pattern_scale": self.pattern_scale,
                "top_products": self.top_products,
                "competition_level": self.competition_level,
            },
            "ai_generation": {
                "positive_prompt": self.positive_prompt,
                "negative_prompt": self.negative_prompt,
                "key_elements": self.key_elements,
                "avoid_elements": self.avoid_elements,
                "cfg_scale": self.cfg_scale,
                "style_weight": self.style_weight,
            },
            "reference_images": [
                {
                    "title": img.title,
                    "url": img.url,
                    "width": img.width,
                    "height": img.height,
                }
                for img in self.reference_images
            ],
            "generated_at": self.generated_at,
            # ── Explicabilité ──────────────────────────────────────────────────
            "opportunity_score": self.opportunity_score,
            "confidence": self.confidence,
            "score_breakdown": self.score_breakdown,
            "signals": self.signals,
            "saturation": self.saturation,
            "reusability_detail": self.reusability_detail,
            "demand_evidence": self.demand_evidence,
            # ── SEO ────────────────────────────────────────────────────────────
            "seo_keywords": self.seo_keywords,
            "title_seeds": self.title_seeds,
        }


# ── Factory : conversion dict Gemini → ProductionBrief ────────────────────────

def _brief_from_trend(trend: Dict) -> ProductionBrief:
    """Convertit un dict de tendance Gemini en ProductionBrief."""
    vd = trend.get("visual_direction", {})
    cp = vd.get("color_palette", {})
    sf = trend.get("spoonflower_fit", {})
    ag = trend.get("ai_generation", {})

    # Sub-niches
    sub_niches = []
    for s in trend.get("sub_niches", []):
        if isinstance(s, dict):
            sub_niches.append(SubNicheBrief(
                name=s.get("name", ""),
                trending_score=int(s.get("trending_score", 0)),
                unique_angle=s.get("unique_angle", ""),
                prompt_keywords=s.get("prompt_keywords", []),
            ))
        elif isinstance(s, str):
            sub_niches.append(SubNicheBrief(name=s))

    # Reference images
    ref_images = []
    for img in trend.get("reference_images", []):
        ref_images.append(ReferenceImage(
            title=img.get("title", ""),
            url=img.get("url", ""),
            width=img.get("width", 0),
            height=img.get("height", 0),
        ))

    # ── Briques d'explicabilité (attachées par OpportunityValidator) ──────────
    opportunity_score = float(trend.get("opportunity_score", 0.0) or 0.0)
    confidence = float(trend.get("confidence", 0.0) or 0.0)
    score_breakdown = trend.get("score_breakdown", {}) or {}
    signals = dict(trend.get("signals", {}) or {})
    saturation = trend.get("saturation", {}) or {}
    reusability_detail = trend.get("reusability_detail", "") or ""
    demand_evidence = trend.get("demand_evidence", "") or ""

    # Reporter le label de provenance dans signals pour l'affichage markdown
    prov = trend.get("provenance", {}) or {}
    if prov.get("label") and "provenance_label" not in signals:
        signals["provenance_label"] = prov.get("label")

    # Score affiché : opportunity_score validé si présent, sinon score Gemini brut
    if opportunity_score > 0:
        displayed_score = int(round(opportunity_score))
    else:
        displayed_score = int(trend.get("trending_score", 50))

    # ── SEO : mots-clés tendance + tous les prompt_keywords des sous-niches ────
    seo_set = []
    for kw in ag.get("key_elements", []) or []:
        if kw:
            seo_set.append(str(kw).strip().lower())
    for s in trend.get("sub_niches", []):
        if isinstance(s, dict):
            for kw in s.get("prompt_keywords", []) or []:
                if kw:
                    seo_set.append(str(kw).strip().lower())
    seo_keywords = list(dict.fromkeys(k for k in seo_set if k))

    # Titres candidats (max ~6)
    title_seeds: List[str] = []
    name_val = trend.get("name", "")
    if name_val:
        title_seeds.append(f"{name_val} seamless pattern")
    for s in trend.get("sub_niches", []):
        if isinstance(s, dict) and s.get("name"):
            title_seeds.append(f"{s['name']} repeat pattern")
        if len(title_seeds) >= 6:
            break

    return ProductionBrief(
        name=trend.get("name", ""),
        trending_score=displayed_score,
        market_opportunity=trend.get("market_opportunity", "medium"),
        why_trending=trend.get("why_trending", ""),
        target_audience=trend.get("target_audience", ""),
        sub_niches=sub_niches,
        # Visual direction
        mood=vd.get("mood", ""),
        composition=vd.get("composition", ""),
        line_style=vd.get("line_style", ""),
        color_primary=cp.get("primary", []),
        color_accent=cp.get("accent", []),
        color_background=cp.get("background", ""),
        style_references=vd.get("style_references", []),
        texture=vd.get("texture", ""),
        # Spoonflower
        repeat_type=sf.get("repeat_type", "basic"),
        pattern_scale=sf.get("scale", "medium"),
        top_products=sf.get("top_products", ["fabric"]),
        competition_level=sf.get("competition_level", "medium"),
        # AI generation
        positive_prompt=ag.get("positive_prompt", ""),
        negative_prompt=ag.get("negative_prompt", ""),
        key_elements=ag.get("key_elements", []),
        avoid_elements=ag.get("avoid_elements", []),
        cfg_scale=float(ag.get("cfg_scale", 7.5)),
        style_weight=float(ag.get("style_weight", 0.85)),
        # References
        reference_images=ref_images,
        generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        # Explicabilité
        opportunity_score=round(opportunity_score, 1),
        confidence=round(confidence, 1),
        score_breakdown=score_breakdown,
        signals=signals,
        saturation=saturation,
        reusability_detail=reusability_detail,
        demand_evidence=demand_evidence,
        # SEO
        seo_keywords=seo_keywords,
        title_seeds=title_seeds,
        # Type de niche
        crossover_gap=bool(trend.get("crossover_gap", False)),
        demand_gap_evidence=str(trend.get("demand_gap_evidence", "")),
    )


# ── BriefGenerator ────────────────────────────────────────────────────────────

class BriefGenerator:
    """
    Génère des cahiers des charges complets combinant Gemini + Wikimedia.

    Workflow :
    1. Interroge Gemini (avec Google Search grounding) pour les 12 tendances
    2. Pour chaque tendance, cherche 2 images de référence sur Wikimedia Commons
    3. Convertit les données en objets ProductionBrief riches
    4. Peut exporter en Markdown + JSON
    """

    def __init__(self, profile=None):
        from trend_discovery.providers.gemini_provider import GeminiProvider
        from trend_discovery.markets.market_profile import get_profile
        self._profile = (
            get_profile(profile) if isinstance(profile, str) or profile is None
            else profile
        )
        self._gemini = GeminiProvider()

    def generate_all(self, extra_constraints: str = "") -> List[ProductionBrief]:
        """
        Pipeline optimal : Gemini → critique → images Wikimedia → validation.

        Étapes (si Gemini disponible) :
            1. fetch_global_pod_trends(profile) → auto-critique (critique_and_refine)
            2. enrichissement des images de référence Wikimedia (sans 2e appel Gemini
               de découverte : on réutilise les tendances déjà récupérées)
            3. OpportunityValidator().validate → score transparent + briques d'explicabilité
            4. conversion en ProductionBrief, tri par opportunity_score décroissant

        Si Gemini est indisponible / vide, bascule sur l'arbre de niches (lui aussi
        passé par l'OpportunityValidator pour des scores honnêtes/mesurés).

        Args:
            extra_constraints: contraintes opérateur injectées dans le prompt Gemini.

        Returns:
            Liste de ProductionBrief triée par opportunity_score décroissant.
        """
        from trend_discovery.research.opportunity_validator import OpportunityValidator

        trends: List[Dict] = []
        if self._gemini.is_available():
            trends = self._gemini.fetch_global_pod_trends(self._profile, extra_constraints)
            if trends:
                trends = self._gemini.critique_and_refine(trends, self._profile)
                # Enrichissement images : Wikimedia (domaine public) + Spoonflower bestsellers
                from trend_discovery.scrapers.spoonflower_scraper import SpoonflowerScraper
                _spf_scraper = SpoonflowerScraper()
                for trend in trends:
                    # Wikimedia Commons (style ref domaine public)
                    wiki_query = trend.get("wikimedia_query", trend.get("name", ""))
                    try:
                        trend["reference_images"] = self._gemini.find_wikimedia_images(wiki_query, limit=2)
                    except Exception as exc:
                        logger.warning(
                            "[BriefGenerator] images Wikimedia '%s' échouées: %s", wiki_query, exc
                        )
                        trend.setdefault("reference_images", [])

                    # Spoonflower bestsellers (images de ce qui vend réellement)
                    spf_query = trend.get("spoonflower_query", trend.get("name", ""))
                    try:
                        trend["spoonflower_references"] = _spf_scraper.search_bestsellers_with_images(
                            spf_query, limit=3
                        )
                        if trend["spoonflower_references"]:
                            logger.info(
                                "[BriefGenerator] Spoonflower refs '%s': %d image(s)",
                                spf_query, len(trend["spoonflower_references"]),
                            )
                    except Exception as exc:
                        logger.warning(
                            "[BriefGenerator] Spoonflower refs '%s' échouées: %s", spf_query, exc
                        )
                        trend.setdefault("spoonflower_references", [])

        if not trends:
            logger.warning(
                "[BriefGenerator] Gemini indisponible/vide — fallback arbre de niches "
                "(Wikipedia + Wikimedia + PromptBuilder, 0 clé / 0 coût)."
            )
            briefs = self.generate_from_niche_tree()
            self._record_history(briefs)
            return briefs

        # ── Signaux externes (2 appels Gemini batchés avec grounding) ─────────
        from trend_discovery.research.web_signal_fetcher import WebSignalFetcher
        niche_names = [t.get("name", "") for t in trends if t.get("name")]
        web_signals = {}
        try:
            fetcher = WebSignalFetcher(self._gemini)
            web_signals = fetcher.fetch_all(niche_names)
            n_measured = sum(1 for s in web_signals.values() if s.grounding_confirmed)
            logger.info(
                "[briefs] signaux externes: %d/%d niches avec grounding confirmé",
                n_measured, len(niche_names),
            )
        except Exception as exc:
            logger.warning("[briefs] WebSignalFetcher échoué, continuer sans: %s", exc)

        # ── Validation transparente (scores + briques d'explicabilité) ─────────
        try:
            trends = OpportunityValidator(web_signals=web_signals).validate(trends, self._profile)
        except Exception as exc:
            logger.warning("[BriefGenerator] validation des opportunités échouée: %s", exc)

        briefs = [_brief_from_trend(t) for t in trends]
        briefs.sort(key=lambda b: b.opportunity_score, reverse=True)

        logger.info("[BriefGenerator] %d cahiers des charges générés (Gemini + validation).", len(briefs))
        self._record_history(briefs)
        return briefs

    def _record_history(self, briefs: List[ProductionBrief]) -> None:
        """Enregistre les détections dans l'historique (best-effort, jamais bloquant)."""
        try:
            from trend_discovery.research.history_store import HistoryStore
            HistoryStore().record(briefs, self._profile)
        except Exception as exc:
            logger.warning("[BriefGenerator] historique non enregistré: %s", exc)

    def generate_from_niche_tree(self, max_briefs: int = 12) -> List[ProductionBrief]:
        """
        Construit des cahiers des charges SANS Gemini.

        Sources, toutes gratuites et sans clé :
          - Arbre de niches statique (noms + mots-clés, anglais)
          - Wikipedia Pageviews → demande réelle MESURÉE (ne bloque jamais les datacenters)
          - Wikimedia Commons → images de référence domaine public
          - PromptBuilder → prompts positif + négatif complets (modificateurs de style intégrés)

        Respecte la règle "zéro donnée inventée" : le score de tendance vient de
        Wikipedia quand disponible (MESURÉ), sinon il est clairement étiqueté HEURISTIQUE.

        Args:
            max_briefs: nombre maximum de cahiers des charges à produire.

        Returns:
            Liste de ProductionBrief triée par score décroissant.
        """
        from trend_discovery.normalizer.niche_tree_builder import NicheTree
        from trend_discovery.generators.prompt_builder import PromptBuilder
        from trend_discovery.providers.wikipedia_provider import WikipediaProvider

        tree = NicheTree()
        pb = PromptBuilder()
        wiki = WikipediaProvider()

        # ── Sélection diversifiée : feuilles réparties sur les catégories racines ─
        selected = []
        for root in tree.root_nodes():
            leaves = [n for n in tree.all_descendants(root.name) if not n.children]
            selected.extend(leaves[:2])  # 2 feuilles par catégorie racine
        # Compléter avec d'autres feuilles si besoin pour atteindre max_briefs
        if len(selected) < max_briefs:
            extra = [n for n in tree.all_leaves() if n not in selected]
            selected.extend(extra[: max_briefs - len(selected)])
        selected = selected[:max_briefs]

        # ── Construction de dicts "trend-like" (même schéma que Gemini) ────────
        # afin de les faire passer par l'OpportunityValidator : les scores du
        # fallback sont donc eux aussi mesurés/honnêtes (pas de 50 codé en dur).
        trends: List[Dict] = []
        for node in selected:
            # ── Sous-niches = enfants de la niche dans l'arbre ──────────────────
            sub_niches = [
                {
                    "name": child.name,
                    "trending_score": 0,
                    "unique_angle": "",
                    "prompt_keywords": child.keywords,
                }
                for child in tree.children_of(node.name)
            ]

            # ── Prompts complets (PromptBuilder, déterministe, 0 LLM) ────────────
            prompt = pb.build(node.name, niche_keywords=node.keywords)

            # ── Images de référence Wikimedia Commons (0 clé) ───────────────────
            query = node.keywords[0] if node.keywords else node.name
            try:
                raw_imgs = self._gemini.find_wikimedia_images(query, limit=2)
            except Exception as exc:
                logger.warning("[BriefGenerator] images Wikimedia '%s' échouées: %s", query, exc)
                raw_imgs = []

            # Demande (Wikipedia) pour renseigner why_trending honnêtement
            try:
                dmetric = wiki.demande_metric(node.name)
            except Exception:
                from trend_discovery.provenance import Metric
                dmetric = Metric.unavailable()
            if dmetric.is_real:
                why = f"Demande MESURÉE — {dmetric.detail}"
                trend_score = int(round(dmetric.value))
            else:
                why = "HEURISTIQUE — pas de données Wikipedia pour cette niche (à valider)"
                trend_score = 50

            trends.append({
                "name": node.name,
                "trending_score": trend_score,
                "market_opportunity": "medium",
                "why_trending": why,
                "target_audience": "",
                "sub_niches": sub_niches,
                "visual_direction": {},
                "spoonflower_fit": {"competition_level": "medium"},
                "ai_generation": {
                    "positive_prompt": prompt.positive,
                    "negative_prompt": prompt.negative,
                    "key_elements": node.keywords,
                },
                "wikimedia_query": query,
                "reference_images": raw_imgs,
            })

        # ── Validation transparente (scores honnêtes, briques d'explicabilité) ─
        try:
            from trend_discovery.research.opportunity_validator import OpportunityValidator
            trends = OpportunityValidator(wiki=wiki).validate(trends, self._profile)
        except Exception as exc:
            logger.warning("[BriefGenerator] validation fallback échouée: %s", exc)

        # ── Recalage de market_opportunity sur l'opportunity_score validé ──────
        for t in trends:
            sc = t.get("opportunity_score", t.get("trending_score", 50))
            t["market_opportunity"] = (
                "very_high" if sc >= 75
                else "high" if sc >= 60
                else "medium" if sc >= 40
                else "low"
            )

        briefs = [_brief_from_trend(t) for t in trends]
        briefs.sort(key=lambda b: b.opportunity_score, reverse=True)
        logger.info(
            "[BriefGenerator] %d cahiers des charges générés (arbre de niches + Wikipedia + validation).",
            len(briefs),
        )
        return briefs

    def save_report(
        self,
        briefs: List[ProductionBrief],
        output_dir: str = "./reports",
    ) -> str:
        """
        Sauvegarde un rapport Markdown complet + un fichier JSON.

        Le fichier Markdown est le document principal : beau, lisible, complet.
        Le JSON est pour l'intégration dans d'autres outils.

        Args:
            briefs: liste de ProductionBrief à inclure dans le rapport
            output_dir: dossier de sortie (créé si absent)

        Returns:
            Chemin absolu vers le fichier Markdown généré.
        """
        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.now(timezone.utc)
        timestamp = ts.strftime("%Y%m%d_%H%M")

        # ── Markdown ─────────────────────────────────────────────────────────
        md_path = os.path.join(output_dir, f"cahiers_des_charges_{timestamp}.md")

        header_lines = [
            f"# Cahiers des Charges — Motifs Spoonflower",
            f"",
            f"> Généré le **{ts.strftime('%d/%m/%Y à %H:%M UTC')}** — "
            f"{len(briefs)} tendances analysées",
            f"",
            "## Résumé des Opportunités",
            "",
            "| # | Tendance | Score | Opportunité | Compétition |",
            "|---|----------|-------|-------------|-------------|",
        ]

        for i, b in enumerate(briefs, 1):
            header_lines.append(
                f"| {i} | [{b.name}](#{_anchor(b.name)}) "
                f"| {b.trending_score}/100 "
                f"| {b.market_opportunity.replace('_', ' ')} {b.opportunity_emoji()} "
                f"| {b.competition_level} {b.competition_emoji()} |"
            )

        header_lines += ["", "---", ""]

        with open(md_path, "w", encoding="utf-8") as f:
            f.write("\n".join(header_lines))
            f.write("\n")
            for brief in briefs:
                f.write(brief.to_markdown())
                f.write("\n")

        logger.info("[BriefGenerator] Markdown sauvegardé : %s", md_path)

        # ── JSON ─────────────────────────────────────────────────────────────
        json_path = os.path.join(output_dir, f"cahiers_des_charges_{timestamp}.json")
        json_data = {
            "generated_at": ts.isoformat(),
            "total_briefs": len(briefs),
            "briefs": [b.to_dict() for b in briefs],
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        logger.info("[BriefGenerator] JSON sauvegardé : %s", json_path)

        return md_path


# ── Helpers ───────────────────────────────────────────────────────────────────

def _anchor(text: str) -> str:
    """Convertit un titre en ancre Markdown GitHub-compatible."""
    return (
        text.lower()
        .replace(" ", "-")
        .replace("'", "")
        .replace(",", "")
        .replace("(", "")
        .replace(")", "")
        .replace("&", "")
        .replace("/", "")
        .replace(".", "")
    )
