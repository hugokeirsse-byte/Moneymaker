"""
VariantEngine — génère des variantes de prompt à partir d'un CdC brut.

Au lieu de N copies du même prompt, produit N variantes distinctes :
  • Base       — le prompt original du CdC (1 image)
  • Sub-niche  — 1 image par sous-niche (même palette/style, motifs spécifiques)
  • Style      — déclinaisons visuelles : Dark Moody, Minimal Line Art
  • Fusion     — croisement avec un autre CdC du même run

Objectif : 5-10 images par CdC, toutes différentes et commercialement exploitables.
Aucun appel API — construction pure à partir des données du rapport JSON.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


_SPOONFLOWER_SUFFIX = (
    "seamless tileable repeat pattern, perfectly seamless on all four sides, "
    "flat 2D illustration, solid color fills, no gradients, no shading, no shadows, "
    "graphic flat design, even spacing between motifs, "
    "professional textile surface design for fabric and wallpaper, "
    "flat lay, even studio lighting, 300 DPI, clean solid background, "
    "no visible seam lines at tile edges"
)

_BASE_NEGATIVE = (
    "blurry, low quality, watermark, text, jpeg artifacts, pixelated, "
    "seam lines, visible tile edges, asymmetric repeat, "
    "3D render, fake 3D, bevel, emboss, drop shadow, cast shadow, "
    "ambient occlusion, specular highlight, glossy, shiny, metallic sheen, "
    "fake depth, perspective distortion, volumetric lighting, bump map, "
    "realistic photo, photorealistic, watercolor bleed, ink bleed, "
    "heavy gradients, soft blurry edges, busy cluttered layout, "
    "isolated object on white, single centered motif, white grid lines"
)


@dataclass
class PromptVariant:
    """Une variante de prompt à générer en une seule image."""
    label: str              # ex: "Base", "Sub: Pull-Along Ducks", "Style: Dark Moody"
    positive_prompt: str
    negative_prompt: str
    variant_type: str       # "base" | "sub_niche" | "style" | "fusion"
    metadata: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[{self.variant_type.upper()}] {self.label}"


def _format_palette(vd: dict) -> str:
    parts = []
    primaries = vd.get("color_primary", [])
    accents = vd.get("color_accent", [])
    if primaries:
        parts.append("Color palette: " + ", ".join(primaries))
    if accents:
        parts.append("accents: " + ", ".join(accents))
    return (". ".join(parts) + ". ") if parts else ""


def _first_sentence(text: str) -> str:
    """Extrait la première phrase (ou les 220 premiers chars)."""
    if not text:
        return ""
    for sep in (".", "!", "?"):
        idx = text.find(sep)
        if 40 < idx < 260:
            return text[: idx + 1]
    return text[:220].rstrip() + "."


class VariantEngine:
    """
    Génère des variantes de prompt à partir d'un CdC brut (dict issu du rapport JSON).

    Usage :
        engine = VariantEngine()
        variants = engine.generate_variants(best_brief, all_briefs=other_briefs, n_fusions=2)
        # → List[PromptVariant] prêts à passer à GenerationPipeline.run_variants()
    """

    # Chaque style : (nom, instruction visuelle, négatif additionnel)
    STYLE_VARIANTS: List[tuple] = [
        (
            "Dark Moody",
            (
                "Reworked in a dramatic dark colorway: deep navy, forest green, "
                "burgundy and aged ivory on a near-black background. "
                "Same motifs and composition, atmospheric low-key lighting, "
                "rich saturation, subtle candlelight highlights. "
                "Gothic sophisticated, editorial textile mood."
            ),
            "bright colors, pastel, white background, cheerful, neon, washed-out",
        ),
        (
            "Minimal Line Art",
            (
                "Reworked as elegant minimal line art: clean precise single-color "
                "ink lines on a pure white background, no color fills, "
                "monochromatic, fine pen weight, architectural precision. "
                "Same motifs and spacing, stripped to pure contour."
            ),
            "color fills, gradients, watercolor washes, dark backgrounds, heavy textures",
        ),
    ]

    def generate_variants(
        self,
        brief: dict,
        all_briefs: Optional[List[dict]] = None,
        n_fusions: int = 2,
    ) -> List[PromptVariant]:
        """
        Retourne la liste complète de variantes pour un CdC.

        Ordre : base → sous-niches (max 4) → styles (2) → fusions (n_fusions).
        Total typique : 1 + 4 + 2 + 2 = 9 variantes.
        """
        variants: List[PromptVariant] = []

        variants.append(self._base_variant(brief))

        for sub in brief.get("sub_niches", [])[:4]:
            variants.append(self._sub_niche_variant(brief, sub))

        for style_name, style_instr, style_neg in self.STYLE_VARIANTS:
            variants.append(self._style_variant(brief, style_name, style_instr, style_neg))

        if all_briefs and n_fusions > 0:
            others = [b for b in all_briefs if b.get("name") != brief.get("name")]
            for other in others[:n_fusions]:
                variants.append(self._fusion_variant(brief, other))

        return variants

    # ── constructeurs de variantes ────────────────────────────────────────────

    def _base_variant(self, brief: dict) -> PromptVariant:
        ai = brief.get("ai_generation", {})
        return PromptVariant(
            label="Base",
            positive_prompt=ai.get("positive_prompt", ""),
            negative_prompt=ai.get("negative_prompt", _BASE_NEGATIVE),
            variant_type="base",
        )

    def _sub_niche_variant(self, brief: dict, sub: dict) -> PromptVariant:
        vd = brief.get("visual_direction", {})
        mood = vd.get("mood", "")
        line_style = vd.get("line_style", "")
        texture = vd.get("texture", "")
        palette = _format_palette(vd)
        bg = vd.get("color_background", "white")
        comp = vd.get("composition", "tossed repeat, medium scale")
        style_refs = vd.get("style_references", [])

        sub_name = sub.get("name", "")
        unique_angle = sub.get("unique_angle", "")
        keywords_str = ", ".join(sub.get("prompt_keywords", []))

        prompt_parts = [
            f"A seamless repeat pattern focusing on {sub_name}.",
            unique_angle,
            f"Keywords: {keywords_str}.",
            f"Composition: {comp}.",
            f"Mood: {mood}.",
            f"Art style: {line_style}.",
        ]
        if texture:
            prompt_parts.append(f"Texture: {texture}.")
        if style_refs:
            prompt_parts.append("Style references: " + ", ".join(style_refs) + ".")
        if palette:
            prompt_parts.append(palette.strip())
        prompt_parts.append(f"Background: {bg}.")
        prompt_parts.append(_SPOONFLOWER_SUFFIX)

        base_neg = brief.get("ai_generation", {}).get("negative_prompt", _BASE_NEGATIVE)
        return PromptVariant(
            label=f"Sub: {sub_name}",
            positive_prompt=" ".join(p for p in prompt_parts if p),
            negative_prompt=base_neg,
            variant_type="sub_niche",
            metadata={"sub_niche": sub_name},
        )

    def _style_variant(
        self, brief: dict, style_name: str, style_instr: str, style_neg: str
    ) -> PromptVariant:
        vd = brief.get("visual_direction", {})
        comp = vd.get("composition", "tossed repeat, medium scale")
        base_prompt = brief.get("ai_generation", {}).get("positive_prompt", "")
        motif_desc = _first_sentence(base_prompt) or f"A {brief.get('name', 'pattern')} pattern."

        prompt = (
            f"{motif_desc} "
            f"Composition: {comp}. "
            f"{style_instr} "
            f"{_SPOONFLOWER_SUFFIX}"
        )
        combined_neg = f"{style_neg}, {_BASE_NEGATIVE}"
        return PromptVariant(
            label=f"Style: {style_name}",
            positive_prompt=prompt,
            negative_prompt=combined_neg,
            variant_type="style",
            metadata={"style": style_name},
        )

    def _fusion_variant(self, brief_a: dict, brief_b: dict) -> PromptVariant:
        name_a = brief_a.get("name", "")
        name_b = brief_b.get("name", "")

        base_prompt_a = brief_a.get("ai_generation", {}).get("positive_prompt", "")
        motif_a = _first_sentence(base_prompt_a) or f"A {name_a} pattern."

        vd_b = brief_b.get("visual_direction", {})
        palette_b = _format_palette(vd_b)
        bg_b = vd_b.get("color_background", "white")
        mood_b = vd_b.get("mood", "")
        style_b = vd_b.get("line_style", "")

        prompt = (
            f"A seamless repeat pattern fusing {name_a} with the aesthetic of {name_b}. "
            f"{motif_a} "
            f"Reimagined with the visual language of {name_b}: "
            f"mood {mood_b}, {style_b}. "
            + (palette_b if palette_b else "")
            + f"Background: {bg_b}. "
            + _SPOONFLOWER_SUFFIX
        )
        neg_a = brief_a.get("ai_generation", {}).get("negative_prompt", _BASE_NEGATIVE)
        return PromptVariant(
            label=f"Fusion: × {name_b}",
            positive_prompt=prompt,
            negative_prompt=neg_a,
            variant_type="fusion",
            metadata={"fused_with": name_b},
        )
