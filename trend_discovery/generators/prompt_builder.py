"""
Constructeur de prompts pour la génération d'images Spoonflower.

Convertit une niche/opportunité en prompts optimisés pour Stable Diffusion / Flux
via Runware, ciblant la production de motifs seamless pour tissu.

Deux syntaxes supportées :
  - FLUX (runware:101@1) : langage naturel descriptif, 80-120 mots
  - SDXL (runware:100@1) : termes pondérés avec (term:weight)

Exploite toutes les métadonnées Gemini disponibles :
  mood, composition, line_style, texture, style_references, color_palette

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
    model_hint: str = "runware:101@1"  # FLUX.1 Dev par défaut


class PromptBuilder:
    """
    Construit des prompts optimisés pour les motifs seamless Spoonflower.

    Hiérarchie de qualité :
    1. Métadonnées Gemini complètes (visual_direction) — le plus précis
    2. Mots-clés du niche tree (keywords du nœud)
    3. Modificateur de style par catégorie (fallback)
    4. Nom de la niche seul (dernier recours)

    Produit des prompts en 5 parties structurées (80-120 mots) :
    1. Sujet / descripteur de niche
    2. Style / technique de rendu
    3. Description des couleurs
    4. Composition / mise en page
    5. Suffixe qualité / format
    """

    # ── Suffixe qualité universel (obligatoire pour Spoonflower) ──────────────
    _QUALITY_SUFFIX = (
        "seamless repeat pattern, tileable, surface design, fabric pattern, "
        "professional textile design, flat lay, clean background"
    )

    # ── Prompt négatif universel — spécifique et complet ─────────────────────
    _NEGATIVE_BASE = (
        "text, watermark, signature, logo, copyright, blurry, low quality, "
        "noise, grain, jpeg artifacts, photography, photograph, photorealistic, "
        "3D render, CGI, glossy, reflective, shadow, cast shadow, "
        "border, frame, vignette, white border, edge cutoff, "
        "asymmetric pattern, misaligned repeat, inconsistent style, "
        "human, face, person, body parts, cartoon character, anime, manga"
    )

    # ── Modificateurs de style par catégorie (fallback si pas de métadonnées) ─
    _STYLE_MODIFIERS: Dict[str, Dict] = {
        "botanical": {
            "style": "detailed botanical illustration, naturalistic scientific accuracy, herbarium style",
            "technique": "fine pen line engraving with watercolor wash",
            "composition": "half-drop repeat, balanced arrangement of stems leaves and flowers",
        },
        "floral": {
            "style": "delicate floral illustration, painterly soft edges, garden watercolor",
            "technique": "loose watercolor technique, wet on wet blooms",
            "composition": "tossed repeat, abundant flowers with leaves and buds",
        },
        "mushroom": {
            "style": "whimsical forest illustration, earthy organic feel, hand-drawn",
            "technique": "ink outline with flat color fill, folk art influence",
            "composition": "scattered repeat, various mushroom species at different scales",
        },
        "forest": {
            "style": "woodland illustration, layered forest depth, nature print",
            "technique": "detailed ink illustration with muted palette",
            "composition": "vertical stripes of trees with forest floor elements",
        },
        "celestial": {
            "style": "celestial art nouveau, mystical cosmic art, gold accent design",
            "technique": "gold foil effect on deep indigo, art nouveau linework",
            "composition": "medallion repeat, moons stars planets in ornate frames",
        },
        "geometric": {
            "style": "clean vector geometric, bold modernist design, Bauhaus influence",
            "technique": "flat vector shapes, precise lines, bold contrast",
            "composition": "regular grid repeat, interlocking geometric shapes",
        },
        "watercolor": {
            "style": "loose expressive watercolor, wet bleeding edges, painterly",
            "technique": "wet on wet watercolor, granulation and blooms",
            "composition": "tossed scattered elements, organic placement",
        },
        "art nouveau": {
            "style": "art nouveau decorative, flowing organic lines, ornamental beauty",
            "technique": "sinuous black ink lines, flat fill colors, Mucha influence",
            "composition": "symmetrical half-drop, floral frames and borders integrated",
        },
        "cottagecore": {
            "style": "soft cottagecore aesthetic, vintage countryside charm, cozy",
            "technique": "soft pencil sketch with gentle watercolor, muted palette",
            "composition": "tossed repeat of small cottage motifs, flowers, herbs",
        },
        "halloween": {
            "style": "spooky halloween illustration, festive dark whimsy",
            "technique": "graphic ink illustration, flat colors, editorial style",
            "composition": "packed repeat, bats spiders pumpkins cauldrons",
        },
        "christmas": {
            "style": "festive holiday pattern, traditional Christmas warmth",
            "technique": "digital illustration, crisp lines, saturated colors",
            "composition": "regular repeat, holly berries stars snowflakes gifts",
        },
        "japanese": {
            "style": "Japanese woodblock print style, ukiyo-e inspired elegance",
            "technique": "flat areas of color with bold outlines, woodcut texture",
            "composition": "balanced asymmetric repeat, koi waves cherry blossoms",
        },
        "gothic": {
            "style": "Victorian gothic illustration, dark romantic drama",
            "technique": "fine detailed engraving, deep rich colors, ornate linework",
            "composition": "symmetrical baroque repeat, roses skulls and damask motifs",
        },
        "victorian": {
            "style": "Victorian era illustration, detailed scientific beauty",
            "technique": "fine pen engraving with watercolor, aged paper aesthetic",
            "composition": "half-drop repeat, classical arrangement with decorative borders",
        },
        "abstract": {
            "style": "bold abstract expressionist, dynamic color field design",
            "technique": "gestural brushwork, impasto texture, expressive marks",
            "composition": "allover repeat, fluid organic shapes and bold marks",
        },
        "folk": {
            "style": "folk art style, naive illustration, traditional craft aesthetic",
            "technique": "flat colors, bold outlines, hand-printed feel",
            "composition": "symmetrical medallion repeat, folk motifs birds flowers",
        },
    }

    def build(
        self,
        niche_name: str,
        niche_keywords: Optional[List[str]] = None,
        gemini_metadata: Optional[Dict] = None,
        model: str = "flux",
    ) -> GenerationPrompt:
        """
        Construit le prompt complet pour une niche.

        Utilise toutes les métadonnées Gemini disponibles pour produire
        un prompt riche en 5 parties structurées (80-120 mots).

        Args:
            niche_name: nom de la niche (ex: "Victorian Botanical")
            niche_keywords: mots-clés du niche tree
            gemini_metadata: dict complet de GeminiProvider (avec visual_direction,
                             ai_generation, color_palette, style_references, etc.)
            model: "flux" (runware:101@1) ou "sdxl" (runware:100@1)

        Returns:
            GenerationPrompt prêt à passer à RunwareGenerator.
        """
        style_hint = ""
        model_id = "runware:101@1" if model == "flux" else "runware:100@1"

        # ── Cas 1 : prompt Gemini complet disponible ─────────────────────────
        if gemini_metadata:
            ag = gemini_metadata.get("ai_generation", {})
            if ag.get("positive_prompt"):
                # Gemini a déjà produit un prompt complet — l'utiliser directement
                positive = ag["positive_prompt"]
                # S'assurer qu'il se termine par le suffixe qualité
                if self._QUALITY_SUFFIX not in positive:
                    positive = positive.rstrip("., ") + ", " + self._QUALITY_SUFFIX

                negative = ag.get("negative_prompt", "")
                if not negative:
                    negative = self._NEGATIVE_BASE
                else:
                    # Fusionner avec la base universelle pour les éléments manquants
                    negative = self._merge_negatives(negative)

                if model == "sdxl":
                    positive = self._flux_to_sdxl(positive)

                vd = gemini_metadata.get("visual_direction", {})
                style_hint = vd.get("line_style", "") or vd.get("mood", "") or niche_name

                return GenerationPrompt(
                    positive=positive,
                    negative=negative,
                    niche=niche_name,
                    style_hint=style_hint,
                    model_hint=model_id,
                )

            # Cas 1b : métadonnées partielles — construire le prompt depuis les composants
            positive = self._build_from_metadata(niche_name, gemini_metadata, model)
            negative = ag.get("negative_prompt", "") or self._NEGATIVE_BASE
            negative = self._merge_negatives(negative)

            vd = gemini_metadata.get("visual_direction", {})
            style_hint = vd.get("line_style", "") or vd.get("mood", "") or niche_name

            return GenerationPrompt(
                positive=positive,
                negative=negative,
                niche=niche_name,
                style_hint=style_hint,
                model_hint=model_id,
            )

        # ── Cas 2 : fallback — prompt depuis niche_keywords + modificateurs ──
        positive = self._build_fallback(niche_name, niche_keywords, model)
        style_hint = self._detect_style_hint(niche_name)

        return GenerationPrompt(
            positive=positive,
            negative=self._NEGATIVE_BASE,
            niche=niche_name,
            style_hint=style_hint,
            model_hint=model_id,
        )

    def _build_from_metadata(
        self,
        niche_name: str,
        metadata: Dict,
        model: str = "flux",
    ) -> str:
        """
        Construit un prompt depuis les métadonnées Gemini partielles.

        Structure en 5 parties :
        1. Sujet (niche_name + style_keywords)
        2. Technique de rendu (line_style + texture)
        3. Couleurs (color_palette)
        4. Composition (mood + composition)
        5. Suffixe qualité
        """
        vd = metadata.get("visual_direction", {})
        cp = vd.get("color_palette", {})

        parts: List[str] = []

        # Partie 1 : Sujet
        subject_parts = [niche_name]
        style_refs = vd.get("style_references", [])
        if style_refs:
            subject_parts.append(f"{style_refs[0]} style")
        mood = vd.get("mood", "")
        if mood:
            subject_parts.append(mood)
        parts.append(", ".join(subject_parts))

        # Partie 2 : Technique
        line_style = vd.get("line_style", "")
        texture = vd.get("texture", "")
        technique_parts = []
        if line_style:
            technique_parts.append(line_style)
        if texture:
            technique_parts.append(texture)
        if technique_parts:
            parts.append(", ".join(technique_parts))

        # Partie 3 : Couleurs
        color_parts = []
        primary = cp.get("primary", [])
        accent = cp.get("accent", [])
        bg = cp.get("background", "")

        # Extraire les noms de couleur sans les codes hex
        def color_name(c: str) -> str:
            return c.split("#")[0].strip().lower() if "#" in c else c.lower()

        if primary:
            color_parts.extend(color_name(c) for c in primary[:3])
        if accent:
            color_parts.extend(color_name(c) for c in accent[:2])
        if bg:
            color_parts.append(f"{color_name(bg)} background")
        if color_parts:
            if model == "sdxl":
                parts.append(", ".join(f"({c}:1.1)" for c in color_parts[:4]))
            else:
                parts.append(", ".join(color_parts[:5]))

        # Partie 4 : Composition
        composition = vd.get("composition", "")
        if composition:
            parts.append(composition)

        # Partie 5 : Suffixe qualité
        parts.append(self._QUALITY_SUFFIX)

        return ", ".join(p for p in parts if p)

    def _build_fallback(
        self,
        niche_name: str,
        niche_keywords: Optional[List[str]],
        model: str = "flux",
    ) -> str:
        """Prompt de fallback quand aucune métadonnée Gemini n'est disponible."""
        parts: List[str] = [niche_name]

        # Modificateur de style par catégorie
        niche_lower = niche_name.lower()
        style_mod = None
        for cat, mod in self._STYLE_MODIFIERS.items():
            if cat in niche_lower:
                style_mod = mod
                break

        if style_mod:
            if model == "sdxl":
                parts.append(f"({style_mod['style']}:1.3)")
            else:
                parts.append(style_mod["style"])
            parts.append(style_mod.get("technique", ""))
            parts.append(style_mod.get("composition", ""))

        # Mots-clés du niche tree
        if niche_keywords:
            if model == "sdxl":
                parts.extend(f"({kw}:1.2)" for kw in niche_keywords[:3])
            else:
                parts.extend(niche_keywords[:4])

        parts.append(self._QUALITY_SUFFIX)
        return ", ".join(p for p in parts if p)

    def _flux_to_sdxl(self, flux_prompt: str) -> str:
        """
        Convertit un prompt FLUX (langage naturel) en prompt SDXL (termes pondérés).

        Stratégie : extraire les noms/adjectifs clés et les encadrer de poids.
        Approximation heuristique — fonctionne bien pour les prompts de motifs.
        """
        # Liste de modificateurs courants à pondérer
        high_weight = [
            "seamless", "tileable", "repeat pattern", "botanical", "floral",
            "watercolor", "engraving", "illustration",
        ]
        result = flux_prompt
        for term in high_weight:
            if term in result and f"({term}" not in result:
                result = result.replace(term, f"({term}:1.2)")
        return result

    def _merge_negatives(self, specific_negative: str) -> str:
        """
        Fusionne un prompt négatif spécifique avec la base universelle.
        Évite les doublons.
        """
        base_terms = set(t.strip() for t in self._NEGATIVE_BASE.split(","))
        specific_terms = [t.strip() for t in specific_negative.split(",") if t.strip()]
        # Ajouter les termes spécifiques absents de la base
        extras = [t for t in specific_terms if t not in base_terms]
        if extras:
            return self._NEGATIVE_BASE + ", " + ", ".join(extras)
        return self._NEGATIVE_BASE

    def _detect_style_hint(self, niche_name: str) -> str:
        """Détecte la catégorie de style depuis le nom de niche."""
        niche_lower = niche_name.lower()
        for cat in self._STYLE_MODIFIERS:
            if cat in niche_lower:
                return cat
        return niche_name.split()[0].lower() if niche_name else ""

    def build_batch(
        self,
        niches: List[str],
        keywords_map: Optional[Dict[str, List[str]]] = None,
        gemini_map: Optional[Dict[str, Dict]] = None,
        model: str = "flux",
    ) -> List[GenerationPrompt]:
        """Construit les prompts pour une liste de niches."""
        prompts = []
        for niche in niches:
            kws = (keywords_map or {}).get(niche)
            meta = (gemini_map or {}).get(niche) or (gemini_map or {}).get(niche.lower())
            prompts.append(self.build(niche, kws, meta, model))
        return prompts
