"""
PatternAssembler — assemble des éléments PNG isolés en repeat pattern seamless.

Pipeline :
  1. Charge chaque élément (bytes → RGBA PIL Image)
  2. Supprime le fond blanc (pixels clairs → transparents)
  3. Redimensionne selon le rôle (hero/supporting/filler)
  4. Place sur un canvas coloré selon le layout (tossed/grid/half-drop)
  5. Applique le wrapping seamless (les éléments qui dépassent réapparaissent de l'autre côté)
  6. Retourne en bytes PNG
"""
from __future__ import annotations

import io
import logging
import random
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class PatternAssembler:
    """
    Assemble des éléments PNG isolés (fond blanc) en un repeat pattern seamless.

    Utilise uniquement Pillow + numpy (gratuit, pas d'appel API).
    """

    CANVAS_SIZE = 2048

    ROLE_SCALE = {
        "hero": 0.20,
        "supporting": 0.13,
        "filler": 0.07,
    }

    @staticmethod
    def _remove_white(img) -> "Image":
        """
        Supprime le fond blanc d'une image PIL en la convertissant en RGBA.

        Algorithme : luminance = max(R, G, B) par pixel.
        Les pixels très clairs (luminance proche de 255) deviennent transparents.
        Les pixels colorés restent opaques.

        Args:
            img: PIL Image (n'importe quel mode)

        Returns:
            PIL Image en mode RGBA avec fond blanc supprimé.
        """
        try:
            import numpy as np
        except ImportError:
            logger.error("[assembler] numpy non disponible — suppression fond blanc impossible")
            return img.convert("RGBA")

        from PIL import Image

        rgba = img.convert("RGBA")
        arr = np.array(rgba, dtype=np.uint8)

        r, g, b = arr[:, :, 0], arr[:, :, 1], arr[:, :, 2]
        luminance = np.maximum(np.maximum(r, g), b).astype(np.float32)

        alpha = np.clip((255.0 - luminance) * 3.0, 0, 255).astype(np.uint8)
        arr[:, :, 3] = alpha

        return Image.fromarray(arr, "RGBA")

    @staticmethod
    def _scale_element(img, role: str, canvas_size: int) -> "Image":
        """
        Redimensionne un élément selon son rôle et la taille du canvas.

        Args:
            img: PIL Image RGBA
            role: "hero", "supporting" ou "filler"
            canvas_size: taille du canvas carré en pixels

        Returns:
            PIL Image redimensionnée.
        """
        from PIL import Image

        scale = PatternAssembler.ROLE_SCALE.get(role, PatternAssembler.ROLE_SCALE["supporting"])
        target_size = int(scale * canvas_size)

        w, h = img.size
        if w == 0 or h == 0:
            return img

        if w >= h:
            new_w = target_size
            new_h = max(1, int(h * target_size / w))
        else:
            new_h = target_size
            new_w = max(1, int(w * target_size / h))

        return img.resize((new_w, new_h), Image.LANCZOS)

    def _paste_with_wrap(
        self,
        canvas,
        element_img,
        x: int,
        y: int,
        canvas_size: int,
    ) -> None:
        """
        Colle un élément sur le canvas avec wrapping seamless.

        Si l'élément dépasse un bord, il réapparaît de l'autre côté
        (principe du tiling seamless).

        Args:
            canvas: PIL Image RGBA (canvas cible)
            element_img: PIL Image RGBA à coller
            x, y: position du coin supérieur gauche de l'élément
            canvas_size: taille du canvas carré
        """
        ew, eh = element_img.size

        # Liste des positions wrap (original + décalages pour continuité)
        offsets = [(0, 0)]
        if x < 0:
            offsets.append((canvas_size, 0))
        if y < 0:
            offsets.append((0, canvas_size))
        if x + ew > canvas_size:
            offsets.append((-canvas_size, 0))
        if y + eh > canvas_size:
            offsets.append((0, -canvas_size))
        # Coins
        if x < 0 and y < 0:
            offsets.append((canvas_size, canvas_size))
        if x + ew > canvas_size and y + eh > canvas_size:
            offsets.append((-canvas_size, -canvas_size))
        if x < 0 and y + eh > canvas_size:
            offsets.append((canvas_size, -canvas_size))
        if x + ew > canvas_size and y < 0:
            offsets.append((-canvas_size, canvas_size))

        for dx, dy in offsets:
            canvas.alpha_composite(element_img, dest=(x + dx, y + dy))

    def _place_tossed(
        self,
        elements_rgba: List[Tuple[dict, "Image"]],
        canvas_size: int,
        density: str,
    ) -> "Image":
        """
        Place les éléments en disposition aléatoire (tossed layout).

        Chaque élément est placé à une position aléatoire avec une rotation aléatoire.
        Le nombre d'instances dépend du rôle et de la densité.

        Args:
            elements_rgba: liste de (element_dict, PIL Image RGBA redimensionnée)
            canvas_size: taille du canvas carré
            density: "sparse", "medium" ou "dense"

        Returns:
            PIL Image RGBA du canvas assemblé.
        """
        from PIL import Image

        density_map = {"sparse": 1, "medium": 2, "dense": 3}
        density_instances = density_map.get(density, 2)

        canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))

        for element_dict, element_img in elements_rgba:
            role = element_dict.get("role", "supporting")

            if role == "hero":
                n_instances = 1
            elif role == "supporting":
                n_instances = density_instances
            else:
                # filler
                n_instances = density_instances * 2

            ew, eh = element_img.size

            for _ in range(n_instances):
                angle = random.uniform(-25, 25)
                rotated = element_img.rotate(angle, expand=True, resample=Image.BICUBIC)
                rw, rh = rotated.size

                x = random.randint(-rw // 4, canvas_size - rw * 3 // 4)
                y = random.randint(-rh // 4, canvas_size - rh * 3 // 4)

                self._paste_with_wrap(canvas, rotated, x, y, canvas_size)

        return canvas

    def _place_grid(
        self,
        elements_rgba: List[Tuple[dict, "Image"]],
        canvas_size: int,
    ) -> "Image":
        """
        Place les éléments en grille régulière (grid layout).

        Les éléments alternent en grille NxM, sans rotation.

        Args:
            elements_rgba: liste de (element_dict, PIL Image RGBA redimensionnée)
            canvas_size: taille du canvas carré

        Returns:
            PIL Image RGBA du canvas assemblé.
        """
        from PIL import Image

        canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))

        if not elements_rgba:
            return canvas

        # Calcule la taille de cellule basée sur l'élément le plus grand
        max_dim = max(max(img.size) for _, img in elements_rgba) if elements_rgba else 100
        cell_size = max_dim + max(20, max_dim // 4)

        cols = max(1, canvas_size // cell_size)
        rows = max(1, canvas_size // cell_size)

        n_elements = len(elements_rgba)
        idx = 0
        for row in range(rows + 1):
            for col in range(cols + 1):
                if n_elements == 0:
                    break
                _, element_img = elements_rgba[idx % n_elements]
                idx += 1

                ew, eh = element_img.size
                x = col * cell_size + (cell_size - ew) // 2
                y = row * cell_size + (cell_size - eh) // 2

                self._paste_with_wrap(canvas, element_img, x, y, canvas_size)

        return canvas

    @classmethod
    def load_from_manifest(
        cls,
        manifest_path: str,
        element_ids: Optional[List[int]] = None,
    ) -> Tuple[List[Tuple[dict, bytes]], dict]:
        """
        Charge des éléments sauvegardés depuis un manifest JSON.

        Permet de réassembler sans re-générer : on charge les PNGs transparents
        du disque et on les repasse à assemble() avec n'importe quel assembly_guide.

        Args:
            manifest_path : chemin vers le manifest.json d'un CdC
            element_ids   : liste d'IDs d'éléments à charger (None = tous)

        Returns:
            (elements, assembly_guide) prêts à passer à assemble()
        """
        import json as _json

        with open(manifest_path, encoding="utf-8") as f:
            manifest = _json.load(f)

        assembly_guide = manifest.get("assembly_guide", {})
        raw_elements = manifest.get("elements", [])

        if element_ids is not None:
            raw_elements = [e for e in raw_elements if e.get("id") in element_ids]

        results: List[Tuple[dict, bytes]] = []
        for elem in raw_elements:
            filepath = elem.get("file", "")
            if not filepath or not __import__("os").path.exists(filepath):
                logger.warning("[assembler] fichier élément manquant : %s", filepath)
                continue
            with open(filepath, "rb") as f:
                image_bytes = f.read()
            results.append((elem, image_bytes))

        logger.info(
            "[assembler] %d/%d éléments chargés depuis %s",
            len(results), len(raw_elements), manifest_path,
        )
        return results, assembly_guide

    def assemble(
        self,
        elements: List[Tuple[dict, bytes]],
        assembly_guide: dict,
        element_ids: Optional[List[int]] = None,
    ) -> Optional[bytes]:
        """
        Assemble les éléments générés en un repeat pattern seamless PNG.

        Args:
            elements: liste de (element_dict, image_bytes)
            assembly_guide: dict avec background_color, layout, density, etc.

        Returns:
            bytes PNG du pattern assemblé, ou None en cas d'erreur.
        """
        from PIL import Image

        if not elements:
            logger.warning("[assembler] liste d'éléments vide — assemblage annulé")
            return None

        # Filtrer par IDs si spécifié
        if element_ids is not None:
            elements = [(d, b) for d, b in elements if d.get("id") in element_ids]
            if not elements:
                logger.warning("[assembler] aucun élément correspondant aux IDs %s", element_ids)
                return None

        canvas_size = self.CANVAS_SIZE
        bg_color = assembly_guide.get("background_color", "#FFFFFF")
        layout = assembly_guide.get("layout", "tossed")
        density = assembly_guide.get("density", "medium")

        # 1. Charger et dépouiller le fond blanc de chaque élément
        elements_rgba: List[Tuple[dict, "Image"]] = []
        for element_dict, image_bytes in elements:
            try:
                img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
                img_no_bg = self._remove_white(img)
                role = element_dict.get("role", "supporting")
                img_scaled = self._scale_element(img_no_bg, role, canvas_size)
                elements_rgba.append((element_dict, img_scaled))
            except Exception as exc:
                logger.warning(
                    "[assembler] chargement élément '%s' échoué: %s",
                    element_dict.get("name", "?"),
                    exc,
                )

        if not elements_rgba:
            logger.error("[assembler] aucun élément valide après chargement")
            return None

        logger.info(
            "[assembler] %d éléments → canvas %dx%d, layout=%s",
            len(elements_rgba),
            canvas_size,
            canvas_size,
            layout,
        )

        # 2. Placer les éléments selon le layout
        if layout == "grid":
            overlay = self._place_grid(elements_rgba, canvas_size)
        else:
            # tossed par défaut (inclut half-drop et stripe qui tombent sur tossed)
            overlay = self._place_tossed(elements_rgba, canvas_size, density)

        # 3. Créer le fond coloré
        try:
            bg = Image.new("RGB", (canvas_size, canvas_size), bg_color)
        except (ValueError, AttributeError):
            logger.warning("[assembler] couleur de fond invalide '%s' — blanc par défaut", bg_color)
            bg = Image.new("RGB", (canvas_size, canvas_size), "#FFFFFF")

        # 4. Compositer RGBA sur le fond RGB
        bg_rgba = bg.convert("RGBA")
        bg_rgba.alpha_composite(overlay)
        final = bg_rgba.convert("RGB")

        # 5. Exporter en PNG bytes
        buf = io.BytesIO()
        final.save(buf, format="PNG")
        buf.seek(0)
        result_bytes = buf.read()

        logger.info(
            "[assembler] assemblage terminé : %d bytes PNG (%dx%d)",
            len(result_bytes),
            canvas_size,
            canvas_size,
        )
        return result_bytes
