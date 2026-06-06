"""
Pipeline de Génération d'Images — Module 03.

Orchestre la chaîne complète :
  Top niches (M01) → Prompts → Runware (génération) → Runware (upscale)
  → SpoonflowerPackager → fichiers PNG 300 DPI prêts à uploader

Usage :
    pipeline = GenerationPipeline()
    files = pipeline.run(opportunity_scores, max_images=5)
    # → ["./output/spoonflower/botanical_cottagecore_20250603.png", ...]

    # Depuis un ProductionBrief approuvé (flux principal) :
    results = pipeline.run_brief(brief, n_images=5)
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Dict, List, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from trend_discovery.generators.production_brief import ProductionBrief
    from trend_discovery.generators.quality_auditor import QualityAuditor

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
        tiling: bool = True,
    ):
        from trend_discovery.generators.prompt_builder import PromptBuilder
        from trend_discovery.generators.runware_generator import RunwareGenerator
        from trend_discovery.generators.spoonflower_packager import SpoonflowerPackager

        self._builder = PromptBuilder()
        self._runware = RunwareGenerator()
        self._packager = SpoonflowerPackager(output_dir=output_dir)
        self._upscale_factor = upscale_factor
        self._output_dir = output_dir
        self._tiling = tiling

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
            tiling=self._tiling,
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

    def run_brief(
        self,
        brief: "ProductionBrief",
        n_images: int = 5,
        auditor: Optional["QualityAuditor"] = None,
    ) -> List[GenerationResult]:
        """
        Génère N images à partir d'un ProductionBrief approuvé.

        Utilise directement le positive_prompt et negative_prompt du CdC
        (construits par Gemini, 120-180 mots, structure 7 parties).
        Chaque image passe par l'audit qualité avant packaging ; si elle échoue,
        on retente (max 2 reprises) avant de la rejeter.

        Args:
            brief: ProductionBrief avec positive_prompt rempli.
            n_images: nombre d'images à produire.
            auditor: QualityAuditor optionnel. Si absent, aucun audit n'est fait.

        Returns:
            Liste de GenerationResult (succès + échecs).
        """
        if not self._runware.is_available():
            return [GenerationResult(
                niche=brief.name,
                filepath=None,
                upscaled_url=None,
                success=False,
                error="RUNWARE_API_KEY non configurée",
            )]

        if not brief.positive_prompt:
            logger.error("[gen_pipeline] '%s' — positive_prompt vide", brief.name)
            return [GenerationResult(
                niche=brief.name, filepath=None, upscaled_url=None,
                success=False, error="positive_prompt manquant dans le CdC",
            )]

        results: List[GenerationResult] = []
        logger.info(
            "[gen_pipeline] '%s' — génération de %d image(s) | prompt: %s…",
            brief.name, n_images, brief.positive_prompt[:80],
        )

        cfg_scale = float(getattr(brief, "cfg_scale", 4.0) or 4.0)
        for i in range(n_images):
            result = self._generate_with_audit(
                niche_name=brief.name,
                positive_prompt=brief.positive_prompt,
                negative_prompt=brief.negative_prompt or "",
                auditor=auditor,
                attempt_label=f"{i+1}/{n_images}",
                cfg_scale=cfg_scale,
            )
            results.append(result)
            logger.info("[gen_pipeline] %s [%d/%d]: %s", brief.name, i + 1, n_images, result)

        successes = sum(1 for r in results if r.success)
        logger.info(
            "[gen_pipeline] '%s' → %d/%d images acceptées",
            brief.name, successes, n_images,
        )
        return results

    def run_variants(
        self,
        brief_data: dict,
        variants: List,
        auditor: Optional["QualityAuditor"] = None,
    ) -> List[GenerationResult]:
        """
        Génère 1 image par variante de prompt (base, sous-niche, style, fusion).

        Args:
            brief_data : dict brut du CdC (issu du rapport JSON).
            variants   : List[PromptVariant] produits par VariantEngine.
            auditor    : QualityAuditor optionnel.

        Returns:
            List[GenerationResult] — un résultat par variante.
        """
        if not self._runware.is_available():
            return [GenerationResult(
                niche=f"{brief_data.get('name', '')} — {v.label}",
                filepath=None, upscaled_url=None, success=False,
                error="RUNWARE_API_KEY non configurée",
            ) for v in variants]

        results: List[GenerationResult] = []
        brief_name = brief_data.get("name", "niche")

        logger.info(
            "[gen_pipeline] '%s' — %d variante(s) à générer",
            brief_name, len(variants),
        )

        ai_gen = brief_data.get("ai_generation", {})
        spf_refs = brief_data.get("spoonflower_references", [])
        # ai_generation.seed_image_url takes priority over spoonflower_references
        seed_image_url: Optional[str] = (
            ai_gen.get("seed_image_url")
            or (spf_refs[0].get("image_url") if spf_refs else None)
        )
        if seed_image_url:
            logger.info("[gen_pipeline] seedImage: %s…", seed_image_url[:80])

        # CFG du CdC (FLUX.1 Dev : 4.0 par défaut). Honoré pour toutes les variantes.
        cfg_scale = float(ai_gen.get("cfg_scale", 4.0))
        # strength for img2img (default 0.6 when reference image provided, ignored otherwise)
        strength = float(ai_gen.get("strength", 0.6))
        # tiling=False for non-seamless images (naturalist plates, Redbubble prints)
        tiling = bool(ai_gen.get("tiling", True))

        for i, variant in enumerate(variants, 1):
            niche_label = f"{brief_name} — {variant.label}"
            logger.info(
                "[gen_pipeline] %d/%d — %s | CFG %.1f | tiling=%s | prompt: %s…",
                i, len(variants), variant.label, cfg_scale, tiling, variant.positive_prompt[:80],
            )
            result = self._generate_with_audit(
                niche_name=niche_label,
                positive_prompt=variant.positive_prompt,
                negative_prompt=variant.negative_prompt or "",
                auditor=auditor,
                attempt_label=f"{i}/{len(variants)}",
                seed_image_url=seed_image_url,
                cfg_scale=cfg_scale,
                strength=strength,
                tiling=tiling,
            )
            results.append(result)
            logger.info("[gen_pipeline] %s", result)

        ok = sum(1 for r in results if r.success)
        logger.info(
            "[gen_pipeline] '%s' → %d/%d variantes générées → %s",
            brief_name, ok, len(variants), self._output_dir,
        )
        return results

    def _generate_with_audit(
        self,
        niche_name: str,
        positive_prompt: str,
        negative_prompt: str,
        auditor: Optional["QualityAuditor"],
        attempt_label: str = "",
        max_retries: int = 1,  # 2 tentatives max (1 initiale + 1 retry)
        seed_image_url: Optional[str] = None,
        cfg_scale: float = 4.0,
        strength: float = 0.6,
        tiling: bool = True,
    ) -> GenerationResult:
        """
        Génère une image, l'audite, retente une seule fois si nécessaire.
        Si les 2 tentatives échouent l'audit → image rejetée, pas sauvegardée.
        """
        for attempt in range(max_retries + 1):
            image_bytes, upscaled_url = self._runware.generate_and_upscale(
                positive_prompt=positive_prompt,
                negative_prompt=negative_prompt,
                upscale_factor=self._upscale_factor,
                cfg_scale=cfg_scale,
                retries=0,  # on gère nous-mêmes les retries ici
                seed_image_url=seed_image_url,
                strength=strength,
                tiling=tiling,
            )

            if not image_bytes:
                if attempt < max_retries:
                    logger.warning("[gen_pipeline] '%s' tentative %d échouée, retry", niche_name, attempt + 1)
                    continue
                return GenerationResult(
                    niche=niche_name, filepath=None,
                    upscaled_url=upscaled_url, success=False,
                    error="Runware n'a retourné aucune image",
                )

            # Audit qualité
            if auditor is not None:
                audit = auditor.audit(image_bytes)
                if not audit.passed:
                    logger.warning(
                        "[gen_pipeline] '%s' audit échoué [tentative %d/%d]: %s",
                        niche_name, attempt + 1, max_retries + 1,
                        "; ".join(audit.issues),
                    )
                    if attempt < max_retries:
                        continue
                    # Toutes les tentatives épuisées — image rejetée, pas sauvegardée
                    logger.error(
                        "[gen_pipeline] ❌ '%s' — image non viable après %d tentatives, rejetée. %s",
                        niche_name, max_retries + 1, audit.details,
                    )
                    return GenerationResult(
                        niche=niche_name, filepath=None,
                        upscaled_url=upscaled_url, success=False,
                        error=f"image non viable (audit): {'; '.join(audit.issues)}",
                    )
                else:
                    logger.info("[gen_pipeline] '%s' audit OK: %s", niche_name, audit.details)

            # Packaging Spoonflower
            filepath = self._packager.package(image_bytes, niche_name)
            if not filepath:
                return GenerationResult(
                    niche=niche_name, filepath=None,
                    upscaled_url=upscaled_url, success=False,
                    error="Erreur packaging Spoonflower",
                )

            return GenerationResult(
                niche=niche_name, filepath=filepath,
                upscaled_url=upscaled_url, success=True,
            )

        return GenerationResult(
            niche=niche_name, filepath=None, upscaled_url=None,
            success=False, error=f"Échec après {max_retries + 1} tentatives",
        )
