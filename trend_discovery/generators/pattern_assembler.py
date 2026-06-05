"""
PatternAssembler — assemble des éléments PNG isolés en repeat pattern seamless.

Pipeline :
  1. Charge chaque élément (bytes → RGBA PIL Image)
  2. Supprime le fond (chroma-key sur vert lime, ou luminance pour compat legacy)
  3. Ajoute la bordure sticker (contour blanc propre)
  4. Redimensionne selon le rôle (hero/supporting/filler)
  5. Place selon le layout : sticker (grille jittérée), tessellate (carrelage offset), grid
  6. Applique le wrapping seamless
  7. Retourne en bytes PNG
"""
from __future__ import annotations

import io
import logging
import math
import random
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

# Couleur de fond pour la génération — vert lime pur, absent des illustrations normales
CHROMA_KEY_COLOR = (0, 255, 0)   # #00FF00


class PatternAssembler:
    """
    Assemble des éléments PNG isolés en un repeat pattern seamless.
    Utilise uniquement Pillow + numpy (gratuit, pas d'appel API).
    """

    CANVAS_SIZE = 2048

    ROLE_SCALE = {
        "hero": 0.18,
        "supporting": 0.11,
        "filler": 0.06,
    }

    # Bordure sticker par défaut (px sur le canvas 2048)
    STICKER_BORDER_PX = 14

    @staticmethod
    def _remove_background(img) -> "Image":
        """
        Supprime le fond d'une image PIL.

        Stratégie :
        - Si l'image a un fond vert lime (#00FF00) → chroma-key (propre, préserve blanc/crème)
        - Sinon → luminance-based hardened (compat legacy fond blanc)

        Le chroma-key préserve les éléments blancs/clairs (grues, mousse, neige)
        que la suppression par luminance effacerait par erreur.
        """
        try:
            import numpy as np
        except ImportError:
            logger.error("[assembler] numpy manquant — fond non supprimé")
            return img.convert("RGBA")

        from PIL import Image, ImageFilter

        rgba = img.convert("RGBA")
        arr = np.array(rgba, dtype=np.uint8)
        r = arr[:, :, 0].astype(np.float32)
        g = arr[:, :, 1].astype(np.float32)
        b = arr[:, :, 2].astype(np.float32)

        # Détecte si l'image a un fond chroma-key vert lime
        # Pixels de bord typiques d'un fond vert pur : g >> r et g >> b
        border_sample = np.concatenate([
            arr[0, :, :3], arr[-1, :, :3], arr[:, 0, :3], arr[:, -1, :3]
        ])
        green_excess_border = border_sample[:, 1].astype(float) - np.maximum(
            border_sample[:, 0], border_sample[:, 2]
        ).astype(float)
        is_chroma = float(np.mean(green_excess_border > 80)) > 0.5

        if is_chroma:
            # Chroma-key : supprime les pixels où le vert domine nettement
            green_excess = g - np.maximum(r, b)
            # Transition douce : totalement transparent au-delà de 120, opaque en-dessous de 60
            alpha_f = np.clip(1.0 - (green_excess - 60.0) / 80.0, 0.0, 1.0) * 255.0
        else:
            # Luminance-based (compat fond blanc)
            luminance = np.maximum(np.maximum(r, g), b)
            alpha_f = np.clip((255.0 - luminance) * 3.0, 0.0, 255.0)

        # Durcissement : bord net, pas de transparence partielle floue
        alpha_hard = np.where(alpha_f > 128, 255, 0).astype(np.uint8)
        arr_out = arr.copy()
        arr_out[:, :, 3] = alpha_hard

        result = Image.fromarray(arr_out, "RGBA")

        # Érosion 1px pour supprimer la frange d'antialiasing au bord
        a = result.split()[3].filter(ImageFilter.MinFilter(3))
        result.putalpha(a)

        return result

    # Compat alias — certains modules appellent encore _remove_white
    @staticmethod
    def _remove_white(img) -> "Image":
        return PatternAssembler._remove_background(img)

    @staticmethod
    def _add_sticker_border(img, border_px: int = 14, color=(255, 255, 255, 255)) -> "Image":
        """
        Ajoute un contour coloré autour d'un élément RGBA pour l'effet sticker.

        Algorithme : dilate le canal alpha par MaxFilter, colorie les pixels
        nouvellement couverts avec la couleur de bordure.

        Args:
            img: PIL Image RGBA (fond transparent)
            border_px: épaisseur de la bordure en pixels
            color: RGBA de la bordure (défaut blanc opaque)

        Returns:
            PIL Image RGBA agrandie de border_px de chaque côté.
        """
        try:
            import numpy as np
        except ImportError:
            return img

        from PIL import Image, ImageFilter

        w, h = img.size
        pad = border_px + 4

        # Canvas agrandi pour éviter le clipping
        padded = Image.new("RGBA", (w + pad * 2, h + pad * 2), (0, 0, 0, 0))
        padded.paste(img, (pad, pad), img)

        _, _, _, a = padded.split()

        # Dilation : MaxFilter avec taille impaire ≥ border_px*2+1
        filter_size = max(3, border_px * 2 + 1)
        # PIL MaxFilter accepte n'importe quelle taille impaire
        dilated = a.filter(ImageFilter.MaxFilter(filter_size))

        orig_arr = np.array(a, dtype=np.uint8)
        dil_arr = np.array(dilated, dtype=np.uint8)
        border_mask = (dil_arr > 0) & (orig_arr == 0)

        result_arr = np.array(padded, dtype=np.uint8)
        cr, cg, cb, ca = color
        result_arr[border_mask] = [cr, cg, cb, ca]

        return Image.fromarray(result_arr, "RGBA")

    @staticmethod
    def _scale_element(img, role: str, canvas_size: int) -> "Image":
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

    def _paste_with_wrap(self, canvas, element_img, x: int, y: int, canvas_size: int) -> None:
        """Colle un élément avec wrapping seamless sur les 4 bords + coins."""
        ew, eh = element_img.size
        offsets = [(0, 0)]
        if x < 0:
            offsets.append((canvas_size, 0))
        if y < 0:
            offsets.append((0, canvas_size))
        if x + ew > canvas_size:
            offsets.append((-canvas_size, 0))
        if y + eh > canvas_size:
            offsets.append((0, -canvas_size))
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

    def _place_sticker(
        self,
        elements_rgba: List[Tuple[dict, "Image"]],
        canvas_size: int,
        density: str,
    ) -> "Image":
        """
        Layout sticker : éléments répartis comme des patchs collés sur un fond.

        Utilise une grille jittérée : distribution uniforme (pas de cluster),
        rotation douce ±15°, espacement suffisant entre éléments.
        Chaque instance est légèrement rescalée (80-110%) pour la variété.
        """
        from PIL import Image

        density_map = {"sparse": 1, "medium": 2, "dense": 3}
        d = density_map.get(density, 2)

        canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))

        placements = []
        for element_dict, element_img in elements_rgba:
            role = element_dict.get("role", "supporting")
            n = d if role == "hero" else (d + 1 if role == "supporting" else d * 2 + 1)
            for _ in range(n):
                placements.append((element_dict, element_img))

        n = len(placements)
        if n == 0:
            return canvas

        random.shuffle(placements)

        cols = max(2, round(math.sqrt(n * 1.2)))
        rows = max(2, math.ceil(n / cols) + 1)
        cell_w = canvas_size // cols
        cell_h = canvas_size // rows

        grid_positions = [
            (c * cell_w + cell_w // 2, r * cell_h + cell_h // 2)
            for r in range(rows) for c in range(cols)
        ]
        random.shuffle(grid_positions)

        for i, (element_dict, element_img) in enumerate(placements):
            cx, cy = grid_positions[i % len(grid_positions)]

            # Jitter ±25% de la cellule
            jx = random.randint(-cell_w // 4, cell_w // 4)
            jy = random.randint(-cell_h // 4, cell_h // 4)

            # Légère variation de taille (stickers ne sont jamais identiques)
            scale_var = random.uniform(0.82, 1.08)
            w0, h0 = element_img.size
            new_w = max(1, int(w0 * scale_var))
            new_h = max(1, int(h0 * scale_var))
            elem = element_img.resize((new_w, new_h), Image.LANCZOS)

            angle = random.uniform(-15, 15)
            rotated = elem.rotate(angle, expand=True, resample=Image.BICUBIC)
            rw, rh = rotated.size

            x = cx + jx - rw // 2
            y = cy + jy - rh // 2

            self._paste_with_wrap(canvas, rotated, x, y, canvas_size)

        return canvas

    def _place_tessellate(
        self,
        elements_rgba: List[Tuple[dict, "Image"]],
        canvas_size: int,
        gap: int = 4,
    ) -> "Image":
        """
        Layout tessellation : carrelage offset (demi-brique) du motif principal.

        Idéal pour les écailles de sirène, les tuiles hexagonales, les motifs géométriques.
        Utilise l'élément hero comme tuile de base, répétée côte à côte avec offset.

        Le gap entre tuiles contrôle si c'est jointif (gap=0) ou aéré.
        """
        from PIL import Image

        canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))

        # Tuile principale = premier hero, ou premier élément
        tile_pair = next(
            ((d, img) for d, img in elements_rgba if d.get("role") == "hero"),
            elements_rgba[0] if elements_rgba else None,
        )
        if not tile_pair:
            return canvas

        _, tile_img = tile_pair
        tw, th = tile_img.size

        step_x = tw + gap
        step_y = th + gap

        cols = canvas_size // step_x + 3
        rows = canvas_size // step_y + 3

        for row in range(rows):
            for col in range(cols):
                # Offset demi-brique sur les rangées impaires
                offset_x = step_x // 2 if (row % 2 == 1) else 0
                x = col * step_x + offset_x - step_x
                y = row * step_y - step_y
                self._paste_with_wrap(canvas, tile_img, x, y, canvas_size)

        return canvas

    def _place_grid(
        self,
        elements_rgba: List[Tuple[dict, "Image"]],
        canvas_size: int,
    ) -> "Image":
        """Grille régulière NxM, sans rotation, éléments en alternance."""
        from PIL import Image

        canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        if not elements_rgba:
            return canvas

        max_dim = max(max(img.size) for _, img in elements_rgba)
        cell_size = max_dim + max(20, max_dim // 4)
        cols = max(1, canvas_size // cell_size)
        rows = max(1, canvas_size // cell_size)

        n_elements = len(elements_rgba)
        idx = 0
        for row in range(rows + 1):
            for col in range(cols + 1):
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
        Permet de réassembler sans re-générer.
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
        Assemble les éléments en un repeat pattern seamless PNG.

        assembly_guide keys :
          background_color  : hex du fond (ex: "#1B3A6B")
          layout            : "sticker" | "tessellate" | "grid" | "tossed" (alias sticker)
          density           : "sparse" | "medium" | "dense"
          sticker_border    : true/false (défaut true)
          sticker_border_color : hex (défaut "#FFFFFF")
        """
        from PIL import Image

        if not elements:
            logger.warning("[assembler] liste d'éléments vide — assemblage annulé")
            return None

        if element_ids is not None:
            elements = [(d, b) for d, b in elements if d.get("id") in element_ids]
            if not elements:
                logger.warning("[assembler] aucun élément aux IDs %s", element_ids)
                return None

        canvas_size = self.CANVAS_SIZE
        bg_color = assembly_guide.get("background_color", "#FFFFFF")
        layout = assembly_guide.get("layout", "sticker")
        density = assembly_guide.get("density", "medium")
        do_border = assembly_guide.get("sticker_border", True)
        border_hex = assembly_guide.get("sticker_border_color", "#FFFFFF")

        # Convertit hex border en RGBA
        try:
            bh = border_hex.lstrip("#")
            border_color = (int(bh[0:2], 16), int(bh[2:4], 16), int(bh[4:6], 16), 255)
        except Exception:
            border_color = (255, 255, 255, 255)

        # 1. Charger, supprimer fond, ajouter bordure sticker, redimensionner
        elements_rgba: List[Tuple[dict, "Image"]] = []
        for element_dict, image_bytes in elements:
            try:
                img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
                img_clean = self._remove_background(img)

                if do_border:
                    img_clean = self._add_sticker_border(
                        img_clean,
                        border_px=self.STICKER_BORDER_PX,
                        color=border_color,
                    )

                role = element_dict.get("role", "supporting")
                img_scaled = self._scale_element(img_clean, role, canvas_size)
                elements_rgba.append((element_dict, img_scaled))

            except Exception as exc:
                logger.warning(
                    "[assembler] chargement '%s' échoué: %s",
                    element_dict.get("name", "?"),
                    exc,
                )

        if not elements_rgba:
            logger.error("[assembler] aucun élément valide après chargement")
            return None

        logger.info(
            "[assembler] %d éléments → canvas %dx%d, layout=%s, border=%s",
            len(elements_rgba), canvas_size, canvas_size, layout, do_border,
        )

        # 2. Layout
        if layout == "tessellate":
            overlay = self._place_tessellate(elements_rgba, canvas_size)
        elif layout == "grid":
            overlay = self._place_grid(elements_rgba, canvas_size)
        else:
            # "sticker", "tossed", "half-drop", "stripe" → sticker grid-jitter
            overlay = self._place_sticker(elements_rgba, canvas_size, density)

        # 3. Fond coloré
        try:
            bg = Image.new("RGB", (canvas_size, canvas_size), bg_color)
        except (ValueError, AttributeError):
            logger.warning("[assembler] couleur fond invalide '%s' → blanc", bg_color)
            bg = Image.new("RGB", (canvas_size, canvas_size), "#FFFFFF")

        # 4. Composite
        bg_rgba = bg.convert("RGBA")
        bg_rgba.alpha_composite(overlay)
        final = bg_rgba.convert("RGB")

        # 5. PNG bytes
        buf = io.BytesIO()
        final.save(buf, format="PNG")
        buf.seek(0)
        result_bytes = buf.read()

        logger.info(
            "[assembler] terminé : %d bytes PNG (%dx%d)",
            len(result_bytes), canvas_size, canvas_size,
        )
        return result_bytes
