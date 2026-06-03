"""
Constructeur de prompts pour la génération d'images Spoonflower.

Convertit une niche/opportunité en prompts optimisés pour Stable Diffusion / Flux
via Runware, ciblant la production de motifs seamless pour tissu.

Spécifications Spoonflower :
- Motif seamless (tuile parfaite)
- 300 DPI minimum
- PNG, 4500×4500 px minimum (= 15" × 15" à 300 DPI)
- Gamme de couleurs cohérente
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GenerationPrompt:
    """Prompts complets pour une génération Runware."""
    positive: str
    negative: str
    niche: str
    style_hint: str = ""


class PromptBuilder:
    """
    Construit des prompts SD/Flux optimisés pour les motifs seamless Spoonflower.

    Hiérarchie de qualité :
    1. Métadonnées Gemini (style_keywords + color_keywords) — le plus précis
    2. Mots-clés du niche tree (keywords du nœud)
    3. Prompt générique basé sur le nom de niche
    """

    # Suffixe qualité universel pour Spoonflower
    _QUALITY_SUFFIX = (
        "seamless repeat pattern, tileable surface design, fabric pattern design, "
        "professional textile design, flat design, clean edges, high detail, "
        "300 DPI quality, vector-like precision, commercial quality"
    )

    # Prompt négatif universel
    _NEGATIVE_BASE = (
        "text, watermark, signature, logo, label, price tag, "
        "blurry, low quality, jpeg artifacts, noise, grain, "
        "photography, photorealistic, portrait, face, human, person, body, "
        "3D render, CGI, glossy, reflective, shadow, cast shadow, "
        "border, frame, vignette, edge cutoff, clipped, "
        "ugly, deformed, distorted, bad anatomy, "
        "asymmetric, misaligned, inconsistent style"
    )

    # Styles visuels par catégorie pour enrichir le prompt
    _STYLE_MODIFIERS: Dict[str, str] = {
        "botanical": "detailed botanical illustration style, naturalistic, scientific accuracy",
        "floral": "delicate floral watercolor style, painterly, soft edges",
        "mushroom": "whimsical illustration, earthy tones, hand-drawn feel",
        "forest": "woodland illustration, layered depth, organic shapes",
        "celestial": "celestial art nouveau style, gold accents, deep indigo",
        "geometric": "clean vector geometric, bold contrast, precise lines",
        "watercolor": "loose watercolor wash, wet on wet technique, organic bleeding",
        "art nouveau": "art nouveau decorative style, flowing lines, ornamental",
        "cottagecore": "soft cottagecore aesthetic, muted pastels, vintage charm",
        "halloween": "spooky halloween illustration, orange and black palette",
        "christmas": "festive holiday pattern, traditional red and green palette",
        "japanese": "japanese woodblock print style, ukiyo-e inspired",
        "gothic": "victorian gothic illustration, dark romantic aesthetic",
        "abstract": "abstract expressionist, bold color fields, gestural marks",
        "folk": "folk art style, naive illustration, flat colors, decorative",
    }

    def build(
        self,
        niche_name: str,
        niche_keywords: Optional[List[str]] = None,
        gemini_metadata: Optional[Dict] = None,
    ) -> GenerationPrompt:
        """
        Construit le prompt complet pour une niche.

        Args:
            niche_name: nom de la niche (ex: "Victorian Botanical")
            niche_keywords: mots-clés du niche tree
            gemini_metadata: dict complet de GeminiProvider (avec style_keywords, color_keywords)

        Returns:
            GenerationPrompt prêt à passer à RunwareGenerator.
        """
        parts: List[str] = []
        style_hint = ""

        # 1) Métadonnées Gemini (priorité maximale)
        if gemini_metadata:
            style_kws = gemini_metadata.get("style_keywords", [])
            color_kws = gemini_metadata.get("color_keywords", [])
            if style_kws:
                parts.append(", ".join(style_kws[:5]))
                style_hint = style_kws[0] if style_kws else ""
            if color_kws:
                parts.append(f"color palette: {', '.join(color_kws[:4])}")

        # 2) Mots-clés du niche tree
        if niche_keywords:
            parts.extend(niche_keywords[:4])

        # 3) Modificateur de style par catégorie
        niche_lower = niche_name.lower()
        for cat, modifier in self._STYLE_MODIFIERS.items():
            if cat in niche_lower:
                parts.append(modifier)
                if not style_hint:
                    style_hint = cat
                break

        # 4) Nom de la niche lui-même
        parts.insert(0, niche_name)

        # 5) Suffixe qualité Spoonflower
        parts.append(self._QUALITY_SUFFIX)

        positive = ", ".join(p for p in parts if p)

        # Négatif : base + ajustements selon le style
        negative = self._NEGATIVE_BASE
        if "photorealistic" in niche_lower or "realistic" in niche_lower:
            # Pour les styles réalistes, on autorise plus de détails
            negative = negative.replace("photorealistic, ", "")

        return GenerationPrompt(
            positive=positive,
            negative=negative,
            niche=niche_name,
            style_hint=style_hint,
        )

    def build_batch(
        self,
        niches: List[str],
        keywords_map: Optional[Dict[str, List[str]]] = None,
        gemini_map: Optional[Dict[str, Dict]] = None,
    ) -> List[GenerationPrompt]:
        """Construit les prompts pour une liste de niches."""
        prompts = []
        for niche in niches:
            kws = (keywords_map or {}).get(niche)
            meta = (gemini_map or {}).get(niche) or (gemini_map or {}).get(niche.lower())
            prompts.append(self.build(niche, kws, meta))
        return prompts
