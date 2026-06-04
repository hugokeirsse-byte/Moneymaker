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
        lines += [
            f"# {self.opportunity_emoji()} {self.name}",
            f"",
            f"> **Score tendance :** {self.trending_score}/100 &nbsp;|&nbsp; "
            f"**Opportunité marché :** {self.market_opportunity.replace('_', ' ').upper()} {self.opportunity_emoji()} &nbsp;|&nbsp; "
            f"**Généré le :** {ts}",
            f"",
            "---",
            "",
        ]

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
            "---",
            "",
        ]

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

    return ProductionBrief(
        name=trend.get("name", ""),
        trending_score=int(trend.get("trending_score", 50)),
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

    def __init__(self):
        from trend_discovery.providers.gemini_provider import GeminiProvider
        self._gemini = GeminiProvider()

    def generate_all(self) -> List[ProductionBrief]:
        """
        Récupère les tendances Gemini + images Wikimedia → construit les briefs.

        Returns:
            Liste de ProductionBrief, triée par trending_score décroissant.
        """
        raw_trends = self._gemini.build_production_briefs()

        if not raw_trends:
            logger.warning("[BriefGenerator] Aucune tendance retournée par Gemini.")
            return []

        briefs = [_brief_from_trend(t) for t in raw_trends]
        # Trier par score décroissant
        briefs.sort(key=lambda b: b.trending_score, reverse=True)

        logger.info("[BriefGenerator] %d cahiers des charges générés.", len(briefs))
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
