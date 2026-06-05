"""
ElementGenerator — génère 10 éléments isolés pour un CdC.

Chaque élément est un objet unique centré sur fond blanc (ou fond cible),
généré séparément par Runware. L'assemblage en repeat pattern se fait ensuite
gratuitement via PatternAssembler (Pillow).
"""
from __future__ import annotations

import logging
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class ElementGenerator:
    """
    Génère des éléments visuels isolés (icônes/objets individuels) via Runware.

    Au lieu de générer un pattern complet en un seul appel (ce qui produit
    des rendus 3D non désirés avec Flux), on génère chaque élément séparément
    sur fond blanc, puis PatternAssembler les assemble en seamless repeat.

    Max 10 appels Runware par CdC.
    """

    ELEMENT_NEGATIVE = (
        "multiple objects, other objects, pattern, repeat, background scene, "
        "environment, context, table surface, hands, perspective, drop shadow, "
        "cast shadow, ambient occlusion, reflection, gradient fill, 3D render, "
        "glossy surface, metallic sheen, volumetric lighting, depth of field, "
        "bokeh, watermark, text, frame, border, group of items"
    )

    def __init__(self):
        from trend_discovery.generators.runware_generator import RunwareGenerator
        self._runware = RunwareGenerator()

    def is_available(self) -> bool:
        """Délègue à RunwareGenerator.is_available()."""
        return self._runware.is_available()

    def generate_element(
        self,
        element: dict,
        bg_color: str = "#FFFFFF",
    ) -> Optional[bytes]:
        """
        Génère un élément isolé unique via Runware.

        Args:
            element: dict avec au moins les clés "name" et "prompt"
            bg_color: couleur de fond (non utilisée directement dans la génération —
                      l'élément est toujours généré sur fond blanc puis le fond est
                      supprimé par PatternAssembler)

        Returns:
            bytes PNG de l'élément, ou None en cas d'échec.
        """
        base_prompt = element.get("prompt", "")
        if not base_prompt:
            logger.warning(
                "[element_gen] élément '%s' sans prompt — ignoré",
                element.get("name", "?"),
            )
            return None

        full_prompt = (
            f"{base_prompt}, centered on pure white background, isolated object, no other objects"
        )

        image_bytes, _url = self._runware.generate_and_upscale(
            positive_prompt=full_prompt,
            negative_prompt=self.ELEMENT_NEGATIVE,
            retries=0,
        )
        return image_bytes

    def generate_all(self, brief: dict) -> List[Tuple[dict, bytes]]:
        """
        Génère tous les éléments d'un CdC (max 10).

        Args:
            brief: dict CdC contenant au moins la clé "elements" (liste de dicts)
                   et optionnellement "assembly_guide" (pour le bg_color)

        Returns:
            Liste de tuples (element_dict, image_bytes) pour les éléments générés avec succès.
        """
        elements = brief.get("elements", [])[:10]
        bg_color = brief.get("assembly_guide", {}).get("background_color", "#FFFFFF")

        logger.info(
            "[element_gen] '%s' — %d éléments à générer",
            brief.get("name", "?"),
            len(elements),
        )

        results: List[Tuple[dict, bytes]] = []
        for element in elements:
            name = element.get("name", "?")
            logger.info("[element_gen] génération élément : %s", name)
            image_bytes = self.generate_element(element, bg_color=bg_color)
            if image_bytes is None:
                logger.warning("[element_gen] élément '%s' échoué — ignoré", name)
                continue
            results.append((element, image_bytes))
            logger.info("[element_gen] élément '%s' OK (%d bytes)", name, len(image_bytes))

        logger.info(
            "[element_gen] %d/%d éléments générés avec succès",
            len(results),
            len(elements),
        )
        return results
