"""
Pipeline de Génération d'Images — Module 03.

Orchestre la chaîne complète :
  Top niches (M01) → Prompts → Runware (génération) → Runware (upscale)
  → SpoonflowerPackager → fichiers PNG 300 DPI prêts à uploader

Usage :
    pipeline = GenerationPipeline()
    files = pipeline.run(opportunity_scores, max_images=5)
    # → ["./output/spoonflower/botanical_cottagecore_20250603.png", ...]
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class GenerationResult:
    """Résultat de génération pour une niche."""
    niche: str
    filepath: Optional[str]          # Chemin du fichier produit (None si échec)
    upscaled_url: Optional[str]       # URL Runware avant téléchargement
    success: bool
    error: str = ""

    def __str__(self):
        if self.success:
            return f"✅ {self.niche} → {os.path.basename(self.filepath or '')}"
        return f"❌ {self.niche}: {self.error}"


class GenerationPipeline:
    """
    Pipeline de génération d'images Spoonflower.

    Requiert RUNWARE_API_KEY dans l'environnement.
    Si absent : les méthodes retournent des GenerationResult vides sans crasher.
    """

    def __init__(
        self,
        output_dir: str = "./output/spoonflower",
        upscale_factor: int = 4,
    ):
        from trend_discovery.generators.prompt_builder import PromptBuilder
        from trend_discovery.generators.runware_generator import RunwareGenerator
        from trend_discovery.generators.spoonflower_packager import SpoonflowerPackager

        self._builder = PromptBuilder()
        self._runware = RunwareGenerator()
        self._packager = SpoonflowerPackager(output_dir=output_dir)
        self._upscale_factor = upscale_factor
        self._output_dir = output_dir

    def _get_niche_keywords(self, opp) -> List[str]:
        """Extrait les mots-clés d'un OpportunityScore pour le prompt."""
        keywords = []
        path = getattr(opp, "path", "") or ""
        if path:
            keywords.extend(p.strip() for p in path.replace(">", " ").split() if p.strip())
        canonical = getattr(opp, "canonical_name", "") or ""
        if canonical:
            keywords.append(canonical)
        return keywords[:6]

    def generate_one(
        self,
        niche_name: str,
        niche_keywords: Optional[List[str]] = None,
        gemini_metadata: Optional[Dict] = None,
    ) -> GenerationResult:
        """
        Génère une image Spoonflower-ready pour une niche.

        Returns:
            GenerationResult avec filepath si succès, error sinon.
        """
        if not self._runware.is_available():
            return GenerationResult(
                niche=niche_name,
                filepath=None,
                upscaled_url=None,
                success=False,
                error="RUNWARE_API_KEY non configurée",
            )

        # Construction du prompt
        gen_prompt = self._builder.build(niche_name, niche_keywords, gemini_metadata)
        logger.info(
            "[gen_pipeline] niche='%s' | prompt=%s...",
            niche_name, gen_prompt.positive[:80],
        )

        # Génération + upscale via Runware
        image_bytes, upscaled_url = self._runware.generate_and_upscale(
            positive_prompt=gen_prompt.positive,
            negative_prompt=gen_prompt.negative,
            upscale_factor=self._upscale_factor,
        )

        if not image_bytes:
            return GenerationResult(
                niche=niche_name,
                filepath=None,
                upscaled_url=upscaled_url,
                success=False,
                error="Runware n'a pas retourné d'image",
            )

        # Packaging Spoonflower
        filepath = self._packager.package(image_bytes, niche_name)
        if not filepath:
            return GenerationResult(
                niche=niche_name,
                filepath=None,
                upscaled_url=upscaled_url,
                success=False,
                error="Erreur packaging Spoonflower",
            )

        return GenerationResult(
            niche=niche_name,
            filepath=filepath,
            upscaled_url=upscaled_url,
            success=True,
        )

    def run(
        self,
        opportunity_scores: List,
        max_images: int = 5,
        gemini_cache: Optional[Dict] = None,
    ) -> List[GenerationResult]:
        """
        Génère des images pour les top N opportunités.

        Args:
            opportunity_scores: liste d'OpportunityScore triée par score desc
            max_images: nombre d'images à générer (défaut 5 pour Spoonflower)
            gemini_cache: dict {niche: metadata} depuis GeminiProvider

        Returns:
            Liste de GenerationResult (succès et échecs).
        """
        if not self._runware.is_available():
            logger.warning(
                "[gen_pipeline] RUNWARE_API_KEY absente — génération désactivée. "
                "Ajoute la clé dans .env ou GitHub Secrets."
            )
            return []

        results: List[GenerationResult] = []
        targets = opportunity_scores[:max_images]

        logger.info(
            "[gen_pipeline] Génération de %d image(s) Spoonflower…",
            len(targets),
        )

        for i, opp in enumerate(targets, 1):
            niche = getattr(opp, "niche", "") or f"niche_{i}"
            logger.info("[gen_pipeline] %d/%d — %s", i, len(targets), niche)

            keywords = self._get_niche_keywords(opp)
            metadata = None
            if gemini_cache:
                metadata = (
                    gemini_cache.get(niche)
                    or gemini_cache.get(niche.lower())
                )

            result = self.generate_one(niche, keywords, metadata)
            results.append(result)
            logger.info("[gen_pipeline] %s", result)

        # Bilan
        successes = [r for r in results if r.success]
        logger.info(
            "[gen_pipeline] ✅ %d/%d images générées → %s",
            len(successes), len(results), self._output_dir,
        )
        for r in successes:
            # Vérification de conformité Spoonflower
            ok, msg = self._packager.verify(r.filepath)
            logger.info("[gen_pipeline] vérif %s: %s", os.path.basename(r.filepath), msg)

        return results
