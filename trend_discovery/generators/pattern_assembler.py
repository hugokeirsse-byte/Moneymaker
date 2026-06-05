"""
PatternAssembler — assemble des éléments PNG isolés en repeat pattern seamless.

Concept : chaque élément est traité comme un STICKER physique — une image complète
avec son propre fond, découpée au plus près du contenu et posée sur un fond uni.
L'effet est celui de vraies étiquettes ou patchs collés, pas d'un dessin sur fond.

Pipeline :
  1. Charge chaque élément (bytes → PIL Image)
  2. Découpe au contenu (crop serré + padding)
  3. Ajoute une ombre portée douce (effet sticker relevé)
  4. Redimensionne selon le rôle (hero / supporting / filler)
  5. Place selon le layout (sticker = grille jittérée, tessellate = carrelage offset, grid)
  6. Wrapping seamless sur les bords
  7. Retourne en bytes PNG
"""
from __future__ import annotations

import io
import logging
import math
import random
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)


class PatternAssembler:
    """
    Assemble des éléments PNG en un repeat pattern seamless.
    Approche sticker : chaque élément garde son propre fond, posé sur le canvas comme un patch collé.
    Utilise uniquement Pillow + numpy (gratuit, zéro appel API).
    """

    CANVAS_SIZE = 2048

    ROLE_SCALE = {
        "hero":       0.18,
        "supporting": 0.12,
        "filler":     0.07,
    }

    SHADOW_PX = 12   # rayon de l'ombre portée

    # ── Extraction du contenu ────────────────────────────────────────────────

    @staticmethod
    def _find_content_bbox(img) -> Tuple[int, int, int, int]:
        """
        Retourne (left, top, right, bottom) du contenu non-blanc/non-vert de l'image.
        Utilisé pour cropper au plus près de l'élément dessiné.
        """
        try:
            import numpy as np
        except ImportError:
            w, h = img.size
            return (0, 0, w, h)

        arr = img.convert("RGB") if img.mode != "RGB" else img
        arr = __import__("numpy").array(arr, dtype="uint8")
        r, g, b = arr[:, :, 0].astype(float), arr[:, :, 1].astype(float), arr[:, :, 2].astype(float)

        # Pixel « fond » = très clair (blanc) OU très vert (chroma-key)
        is_white = (r > 220) & (g > 220) & (b > 220)
        is_green = (g - __import__("numpy").maximum(r, b)) > 80   # fond lime green
        is_bg = is_white | is_green

        content = ~is_bg
        rows = __import__("numpy").any(content, axis=1)
        cols = __import__("numpy").any(content, axis=0)

        if not rows.any():
            w, h = img.size
            return (0, 0, w, h)

        rmin = int(__import__("numpy").where(rows)[0][0])
        rmax = int(__import__("numpy").where(rows)[0][-1])
        cmin = int(__import__("numpy").where(cols)[0][0])
        cmax = int(__import__("numpy").where(cols)[0][-1])

        h_img, w_img = arr.shape[:2]
        pad = max(18, (rmax - rmin) // 8)
        return (
            max(0, cmin - pad),
            max(0, rmin - pad),
            min(w_img, cmax + pad + 1),
            min(h_img, rmax + pad + 1),
        )

    @staticmethod
    def _to_sticker(img) -> "Image":
        """
        Transforme une image générée en sticker physique :
          1. Crop serré au contenu (détecte fond blanc ou vert lime)
          2. Conserve le fond original de l'élément (ne le supprime PAS)
          3. Ajoute une ombre portée douce sous le rectangle

        Le résultat ressemble à un patch ou une étiquette posée sur une surface.

        Args:
            img: PIL Image (fond blanc ou vert lime depuis Runware)

        Returns:
            PIL Image RGBA en mode sticker avec ombre portée.
        """
        from PIL import Image, ImageFilter

        rgba = img.convert("RGBA")
        bbox = PatternAssembler._find_content_bbox(rgba)
        left, top, right, bottom = bbox

        # Crop serré au contenu
        cropped = rgba.crop(bbox)
        cw, ch = cropped.size

        if cw < 4 or ch < 4:
            return rgba

        # ── Ombre portée ───────────────────────────────────────────────────
        shadow_px = PatternAssembler.SHADOW_PX
        offset_x, offset_y = shadow_px // 2 + 3, shadow_px // 2 + 3
        total_w = cw + offset_x + shadow_px
        total_h = ch + offset_y + shadow_px

        # Canvas transparent pour le sticker final
        result = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))

        # Couche d'ombre : rectangle sombre semi-transparent, flou gaussien
        shadow_layer = Image.new("RGBA", (total_w, total_h), (0, 0, 0, 0))
        shadow_rect = Image.new("RGBA", (cw, ch), (15, 15, 15, 130))
        shadow_layer.paste(shadow_rect, (offset_x, offset_y))
        shadow_blurred = shadow_layer.filter(
            ImageFilter.GaussianBlur(radius=shadow_px // 2)
        )

        # Composite : ombre d'abord, sticker par-dessus
        result.alpha_composite(shadow_blurred)
        result.alpha_composite(cropped, dest=(0, 0))

        return result

    @staticmethod
    def _scale_element(img, role: str, canvas_size: int) -> "Image":
        from PIL import Image
        scale = PatternAssembler.ROLE_SCALE.get(role, PatternAssembler.ROLE_SCALE["supporting"])
        target = int(scale * canvas_size)
        w, h = img.size
        if w == 0 or h == 0:
            return img
        if w >= h:
            nw, nh = target, max(1, int(h * target / w))
        else:
            nh, nw = target, max(1, int(w * target / h))
        return img.resize((nw, nh), Image.LANCZOS)

    # ── Wrapping seamless ────────────────────────────────────────────────────

    def _paste_with_wrap(self, canvas, element_img, x: int, y: int, canvas_size: int) -> None:
        """Colle un élément avec wrapping seamless sur les 4 bords + coins."""
        ew, eh = element_img.size
        offsets = [(0, 0)]
        if x < 0:                   offsets.append((canvas_size, 0))
        if y < 0:                   offsets.append((0, canvas_size))
        if x + ew > canvas_size:    offsets.append((-canvas_size, 0))
        if y + eh > canvas_size:    offsets.append((0, -canvas_size))
        if x < 0 and y < 0:                        offsets.append((canvas_size, canvas_size))
        if x + ew > canvas_size and y + eh > canvas_size: offsets.append((-canvas_size, -canvas_size))
        if x < 0 and y + eh > canvas_size:         offsets.append((canvas_size, -canvas_size))
        if x + ew > canvas_size and y < 0:         offsets.append((-canvas_size, canvas_size))
        for dx, dy in offsets:
            canvas.alpha_composite(element_img, dest=(x + dx, y + dy))

    # ── Layouts ──────────────────────────────────────────────────────────────

    def _place_sticker(
        self,
        elements_rgba: List[Tuple[dict, "Image"]],
        canvas_size: int,
        density: str,
    ) -> "Image":
        """
        Dispose les stickers comme des patchs collés sur une surface :
        grille jittérée (distribution uniforme), rotation légère (±18°),
        légère variation de taille (85–108%) pour l'aspect naturel.
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

            jx = random.randint(-cell_w // 4, cell_w // 4)
            jy = random.randint(-cell_h // 4, cell_h // 4)

            # Variation de taille naturelle
            sv = random.uniform(0.85, 1.08)
            w0, h0 = element_img.size
            elem = element_img.resize((max(1, int(w0 * sv)), max(1, int(h0 * sv))), Image.LANCZOS)

            # Rotation légère
            angle = random.uniform(-18, 18)
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
        gap: int = 2,
    ) -> "Image":
        """
        Carrelage offset (demi-brique) : un motif répété côte à côte.
        Parfait pour les écailles de sirène, tuiles hexagonales, motifs géométriques.
        Utilise l'élément hero comme tuile de base.
        """
        from PIL import Image

        canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))

        tile_pair = next(
            ((d, img) for d, img in elements_rgba if d.get("role") == "hero"),
            elements_rgba[0] if elements_rgba else None,
        )
        if not tile_pair:
            return canvas

        _, tile_img = tile_pair
        tw, th = tile_img.size
        sx, sy = tw + gap, th + gap

        cols = canvas_size // sx + 3
        rows = canvas_size // sy + 3

        for row in range(rows):
            for col in range(cols):
                offset_x = sx // 2 if (row % 2 == 1) else 0
                x = col * sx + offset_x - sx
                y = row * sy - sy
                self._paste_with_wrap(canvas, tile_img, x, y, canvas_size)

        return canvas

    def _place_grid(
        self,
        elements_rgba: List[Tuple[dict, "Image"]],
        canvas_size: int,
    ) -> "Image":
        """Grille régulière NxM, éléments en alternance, sans rotation."""
        from PIL import Image

        canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        if not elements_rgba:
            return canvas

        max_dim = max(max(img.size) for _, img in elements_rgba)
        cell = max_dim + max(24, max_dim // 4)
        cols = max(1, canvas_size // cell)
        rows = max(1, canvas_size // cell)
        idx = 0
        n = len(elements_rgba)

        for row in range(rows + 1):
            for col in range(cols + 1):
                _, elem = elements_rgba[idx % n]
                idx += 1
                ew, eh = elem.size
                x = col * cell + (cell - ew) // 2
                y = row * cell + (cell - eh) // 2
                self._paste_with_wrap(canvas, elem, x, y, canvas_size)

        return canvas

    # ── API publique ─────────────────────────────────────────────────────────

    @classmethod
    def load_from_manifest(
        cls,
        manifest_path: str,
        element_ids: Optional[List[int]] = None,
    ) -> Tuple[List[Tuple[dict, bytes]], dict]:
        """Charge des éléments sauvegardés depuis un manifest JSON."""
        import json as _json, os as _os

        with open(manifest_path, encoding="utf-8") as f:
            manifest = _json.load(f)

        assembly_guide = manifest.get("assembly_guide", {})
        raw_elements = manifest.get("elements", [])

        if element_ids is not None:
            raw_elements = [e for e in raw_elements if e.get("id") in element_ids]

        results: List[Tuple[dict, bytes]] = []
        for elem in raw_elements:
            fp = elem.get("file", "")
            if not fp or not _os.path.exists(fp):
                logger.warning("[assembler] fichier manquant : %s", fp)
                continue
            with open(fp, "rb") as f:
                results.append((elem, f.read()))

        logger.info("[assembler] %d/%d éléments chargés depuis %s",
                    len(results), len(raw_elements), manifest_path)
        return results, assembly_guide

    def assemble(
        self,
        elements: List[Tuple[dict, bytes]],
        assembly_guide: dict,
        element_ids: Optional[List[int]] = None,
    ) -> Optional[bytes]:
        """
        Assemble les éléments en pattern seamless PNG.

        Chaque élément est converti en sticker (crop serré + ombre portée)
        avant d'être posé sur le canvas de fond.

        assembly_guide keys :
          background_color : hex du fond  (ex: "#1B3A6B")
          layout           : "sticker" | "tessellate" | "grid"
          density          : "sparse" | "medium" | "dense"
        """
        from PIL import Image

        if not elements:
            logger.warning("[assembler] liste d'éléments vide")
            return None

        if element_ids is not None:
            elements = [(d, b) for d, b in elements if d.get("id") in element_ids]
            if not elements:
                logger.warning("[assembler] aucun élément aux IDs %s", element_ids)
                return None

        canvas_size = self.CANVAS_SIZE
        bg_color    = assembly_guide.get("background_color", "#FFFFFF")
        layout      = assembly_guide.get("layout", "sticker")
        density     = assembly_guide.get("density", "medium")

        # 1. Charger → sticker → redimensionner
        elements_rgba: List[Tuple[dict, "Image"]] = []
        for element_dict, image_bytes in elements:
            try:
                img    = Image.open(io.BytesIO(image_bytes))
                sticker = self._to_sticker(img)
                role   = element_dict.get("role", "supporting")
                scaled = self._scale_element(sticker, role, canvas_size)
                elements_rgba.append((element_dict, scaled))
            except Exception as exc:
                logger.warning("[assembler] '%s' échoué : %s",
                               element_dict.get("name", "?"), exc)

        if not elements_rgba:
            logger.error("[assembler] aucun élément valide")
            return None

        logger.info("[assembler] %d éléments → %dx%d layout=%s",
                    len(elements_rgba), canvas_size, canvas_size, layout)

        # 2. Layout
        if layout == "tessellate":
            overlay = self._place_tessellate(elements_rgba, canvas_size)
        elif layout == "grid":
            overlay = self._place_grid(elements_rgba, canvas_size)
        else:
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

        logger.info("[assembler] terminé : %d bytes (%dx%d)", len(result_bytes), canvas_size, canvas_size)
        return result_bytes

    # ── Compat alias ─────────────────────────────────────────────────────────

    @staticmethod
    def _remove_white(img) -> "Image":
        """Alias de compat pour les modules qui appellent encore _remove_white."""
        from PIL import Image
        rgba = img.convert("RGBA")
        try:
            import numpy as np
            arr = np.array(rgba, dtype=np.uint8)
            lum = np.maximum(np.maximum(arr[:,:,0], arr[:,:,1]), arr[:,:,2]).astype(float)
            alpha = np.where(np.clip((255.0 - lum) * 3.0, 0, 255) > 128, 255, 0).astype(np.uint8)
            arr[:,:,3] = alpha
            return Image.fromarray(arr, "RGBA")
        except ImportError:
            return rgba
