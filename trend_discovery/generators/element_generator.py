"""
ElementGenerator — génère 10 éléments isolés pour un CdC.

Chaque élément est un objet unique centré sur fond blanc, généré séparément
par Runware, puis sauvegardé en PNG fond transparent dans output/elements/.

Ces fichiers PNG transparents sont l'actif principal : ils peuvent être
réassemblés à l'infini (différentes combinaisons, fonds, layouts) sans
re-générer via Runware.
"""
from __future__ import annotations

import io
import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _safe_name(text: str, max_len: int = 40) -> str:
    return (
        "".join(c if c.isalnum() or c in (" ", "-") else "_" for c in text)
        .strip().replace(" ", "_").lower()[:max_len]
    )


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

    def save_elements(
        self,
        results: List[Tuple[dict, bytes]],
        brief: dict,
        output_dir: str = "./output/elements",
    ) -> str:
        """
        Sauvegarde chaque élément en PNG fond transparent + un manifest JSON.

        Structure :
          output/elements/{cdc_name}/
            manifest.json          ← métadonnées + assembly_guide
            01_round_inkwell.png   ← fond transparent (RGBA)
            02_pen_nib.png
            ...

        Args:
            results : sortie de generate_all() — liste (element_dict, image_bytes)
            brief   : CdC complet (pour assembly_guide, background_color, etc.)
            output_dir : répertoire racine des éléments

        Returns:
            Chemin du répertoire CdC créé.
        """
        from PIL import Image
        from trend_discovery.generators.pattern_assembler import PatternAssembler

        cdc_name = brief.get("name", "cdc")
        safe_cdc = _safe_name(cdc_name)
        cdc_dir = os.path.join(output_dir, safe_cdc)
        os.makedirs(cdc_dir, exist_ok=True)

        manifest_elements = []
        for element_dict, image_bytes in results:
            elem_id = element_dict.get("id", len(manifest_elements) + 1)
            elem_name = element_dict.get("name", f"element_{elem_id}")
            safe_elem = _safe_name(elem_name)
            filename = f"{int(elem_id):02d}_{safe_elem}.png"
            filepath = os.path.join(cdc_dir, filename)

            # Supprimer le fond blanc → RGBA transparent
            img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
            img_transparent = PatternAssembler._remove_white(img)
            img_transparent.save(filepath, format="PNG")

            manifest_elements.append({
                **{k: v for k, v in element_dict.items()},
                "file": filepath,
                "filename": filename,
            })
            logger.info("[element_gen] sauvegardé : %s", filepath)

        # Manifest JSON
        manifest = {
            "cdc_name": cdc_name,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "elements_dir": cdc_dir,
            "assembly_guide": brief.get("assembly_guide", {}),
            "elements": manifest_elements,
        }
        manifest_path = os.path.join(cdc_dir, "manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)

        logger.info(
            "[element_gen] manifest sauvegardé : %s (%d éléments)",
            manifest_path, len(manifest_elements),
        )
        return cdc_dir
