"""
Color Rewriter — génère des variantes de coloris d'un motif existant.

Principe : les patterns Spoonflower sont flat 2D / remplissages solides.
On identifie les N couleurs dominantes (k-means) et on les remplace par
une palette cible en espace LAB (correspondance perceptuelle).

Résultat : même motif exact, nouvelle palette, 0 appel Runware, 0 coût.

Usage :
    rewriter = ColorRewriter()
    paths = rewriter.recolor_file(
        "output/spoonflower/japanese_woodblock_1032.png",
        palette_names=["dark_moody", "pastel_soft", "earth_tones"],
        output_dir="output/colorways",
    )
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ── Palettes prédéfinies ────────────────────────────────────────────────────
# Format : liste de (HEX_fond, [HEX_couleur1, HEX_couleur2, ...])
# Le fond est séparé car il couvre la plus grande surface et guide les autres.

PALETTES: Dict[str, Dict] = {
    "dark_moody": {
        "label": "Dark & Moody",
        "background": "#1A1A2E",
        "colors": ["#E8B84B", "#C75C5C", "#5C8CB8", "#A8D8A8", "#F0E6D3"],
        "description": "fond nuit profonde, accents or, rouge, bleu, vert doux",
    },
    "pastel_soft": {
        "label": "Pastel Soft",
        "background": "#FFF8F0",
        "colors": ["#F4B8C1", "#B8D4F4", "#B8F4D4", "#F4E8B8", "#D4B8F4"],
        "description": "fond crème chaud, tons pastels doux",
    },
    "earth_tones": {
        "label": "Earth Tones",
        "background": "#F5ECD7",
        "colors": ["#8B4513", "#6B7C3E", "#C4973A", "#A0522D", "#2E4A1E"],
        "description": "fond sable, terracotta, vert forêt, ocre, brun",
    },
    "navy_mono": {
        "label": "Navy Monochrome",
        "background": "#0D1B4B",
        "colors": ["#FFFFFF", "#E8E0CC", "#89C4C7", "#C5A059", "#4A7BAD"],
        "description": "fond marine profond, blanc, crème, accent or et bleu clair",
    },
    "forest_green": {
        "label": "Forest Green",
        "background": "#1C3A1C",
        "colors": ["#F5F0E8", "#C4973A", "#7DB87D", "#E8855D", "#C8E6C9"],
        "description": "fond vert forêt, crème, or, vert clair, saumon",
    },
    "rose_blush": {
        "label": "Rose & Blush",
        "background": "#FDF0F5",
        "colors": ["#C2185B", "#E91E8C", "#F8BBD0", "#4A148C", "#880E4F"],
        "description": "fond rosé pâle, rose vif, framboise, prune",
    },
    "sage_cream": {
        "label": "Sage & Cream",
        "background": "#F2F0E8",
        "colors": ["#6B7C5E", "#A8B89A", "#3D5A3D", "#C4A882", "#8B7355"],
        "description": "fond crème cassé, verts sauge, brun naturel",
    },
    "midnight_gold": {
        "label": "Midnight Gold",
        "background": "#0A0A1A",
        "colors": ["#FFD700", "#FFA500", "#FF6B35", "#F5F0E8", "#888888"],
        "description": "fond noir profond, or vif, orange, ivoire — luxe",
    },
}


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))  # type: ignore


def _rgb_to_lab(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    """Conversion RGB → CIE L*a*b* (espace perceptuel)."""
    r, g, b = [x / 255.0 for x in rgb]
    # Linearize
    def lin(c):
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = lin(r), lin(g), lin(b)
    # RGB → XYZ (D65)
    x = r * 0.4124 + g * 0.3576 + b * 0.1805
    y = r * 0.2126 + g * 0.7152 + b * 0.0722
    z = r * 0.0193 + g * 0.1192 + b * 0.9505
    # XYZ → Lab
    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    xn, yn, zn = 0.95047, 1.00000, 1.08883
    L = 116 * f(y / yn) - 16
    a = 500 * (f(x / xn) - f(y / yn))
    b_ = 200 * (f(y / yn) - f(z / zn))
    return L, a, b_


def _lab_distance(lab1, lab2) -> float:
    return sum((a - b) ** 2 for a, b in zip(lab1, lab2)) ** 0.5


class ColorRewriter:
    """
    Ré-colorise un pattern PNG en remplaçant sa palette par une palette cible.

    Étapes :
      1. K-means sur les pixels → N couleurs dominantes (clusters)
      2. Chaque cluster source est associé à la couleur cible la plus proche (Lab)
      3. Chaque pixel est remplacé par sa couleur cible mappée
      4. Sauvegarde PNG 300 DPI Spoonflower-ready
    """

    def __init__(self, n_colors: int = 8):
        self.n_colors = n_colors

    def _quantize_colors(self, img_rgb):
        """K-means sur les pixels → liste de couleurs dominantes (RGB)."""
        import numpy as np
        from sklearn.cluster import KMeans

        arr = img_rgb.reshape(-1, 3).astype(float)
        # Sous-échantillonnage pour performance (max 50 000 pixels)
        if len(arr) > 50_000:
            idx = np.random.choice(len(arr), 50_000, replace=False)
            arr_sample = arr[idx]
        else:
            arr_sample = arr

        km = KMeans(n_clusters=self.n_colors, n_init=8, random_state=42)
        km.fit(arr_sample)
        # Assigne chaque pixel (du tableau complet) à un cluster
        labels_full = km.predict(arr)
        centers = km.cluster_centers_.astype(int)
        return centers, labels_full

    def _build_color_map(
        self,
        source_colors: list,
        target_palette: Dict,
    ) -> Dict[int, Tuple[int, int, int]]:
        """
        Associe chaque couleur source à la couleur cible la plus proche en Lab.

        La couleur la plus foncée/claire de chaque palette est prioritairement
        mappée vers le fond pour conserver la lisibilité.
        """
        bg_rgb = _hex_to_rgb(target_palette["background"])
        target_rgbs = [_hex_to_rgb(c) for c in target_palette["colors"]]
        target_pool = [bg_rgb] + target_rgbs

        # Tri des sources par luminosité (fond = plus clair ou plus sombre)
        import numpy as np
        src_luminances = [0.299 * r + 0.587 * g + 0.114 * b for r, g, b in source_colors]
        bg_lum = 0.299 * bg_rgb[0] + 0.587 * bg_rgb[1] + 0.114 * bg_rgb[2]

        color_map: Dict[int, Tuple[int, int, int]] = {}
        used_targets = set()

        # Le fond source (couleur la plus proche du fond cible) → fond cible
        bg_idx = min(
            range(len(source_colors)),
            key=lambda i: _lab_distance(
                _rgb_to_lab(source_colors[i]), _rgb_to_lab(bg_rgb)
            ),
        )
        color_map[bg_idx] = bg_rgb
        used_targets.add(0)  # index 0 = fond dans target_pool

        # Les autres couleurs → pool cible restant (plus proche en Lab)
        for i, src_rgb in enumerate(source_colors):
            if i == bg_idx:
                continue
            src_lab = _rgb_to_lab(src_rgb)
            best_j = None
            best_dist = float("inf")
            for j, tgt_rgb in enumerate(target_pool):
                if j in used_targets:
                    continue
                dist = _lab_distance(src_lab, _rgb_to_lab(tgt_rgb))
                if dist < best_dist:
                    best_dist = dist
                    best_j = j
            if best_j is not None:
                color_map[i] = target_pool[best_j]
                used_targets.add(best_j)
            else:
                # Pool épuisé : réutilise la couleur la plus proche (sans exclusion)
                best_j = min(
                    range(len(target_pool)),
                    key=lambda j: _lab_distance(src_lab, _rgb_to_lab(target_pool[j])),
                )
                color_map[i] = target_pool[best_j]

        return color_map

    def recolor(
        self,
        image_bytes: bytes,
        palette_name: str,
    ) -> Optional[bytes]:
        """
        Ré-colorise une image (bytes) selon une palette nommée.

        Returns:
            Bytes PNG ré-colorisé, ou None en cas d'erreur.
        """
        try:
            import io
            import numpy as np
            from PIL import Image

            palette = PALETTES.get(palette_name)
            if not palette:
                logger.error("[color_rewriter] palette inconnue: %s", palette_name)
                return None

            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            arr = np.array(img)
            h, w = arr.shape[:2]
            flat = arr.reshape(-1, 3)

            centers, labels = self._quantize_colors(flat)
            color_map = self._build_color_map([tuple(c) for c in centers], palette)

            # Remplace chaque pixel
            new_flat = flat.copy()
            for cluster_idx, target_rgb in color_map.items():
                mask = labels == cluster_idx
                new_flat[mask] = target_rgb

            new_arr = new_flat.reshape(h, w, 3).astype("uint8")
            new_img = Image.fromarray(new_arr)

            out = io.BytesIO()
            new_img.save(out, format="PNG", dpi=(300, 300))
            return out.getvalue()

        except Exception as exc:
            logger.error("[color_rewriter] erreur: %s", exc)
            return None

    def recolor_file(
        self,
        input_path: str,
        palette_names: Optional[List[str]] = None,
        output_dir: str = "./output/colorways",
    ) -> List[str]:
        """
        Ré-colorise un fichier PNG selon une ou plusieurs palettes.

        Args:
            input_path: chemin vers le PNG source (Spoonflower-ready)
            palette_names: liste de palettes à appliquer (défaut: toutes)
            output_dir: dossier de sortie

        Returns:
            Liste des chemins des fichiers générés.
        """
        os.makedirs(output_dir, exist_ok=True)
        palettes = palette_names or list(PALETTES.keys())

        with open(input_path, "rb") as fh:
            image_bytes = fh.read()

        stem = Path(input_path).stem
        generated = []

        for pal_name in palettes:
            pal_info = PALETTES.get(pal_name, {})
            logger.info(
                "[color_rewriter] '%s' → palette '%s' (%s)…",
                stem[:40], pal_name, pal_info.get("label", ""),
            )
            result = self.recolor(image_bytes, pal_name)
            if result:
                out_name = f"{stem}__{pal_name}.png"
                out_path = os.path.join(output_dir, out_name)
                with open(out_path, "wb") as fh:
                    fh.write(result)
                size_mb = os.path.getsize(out_path) / 1024 / 1024
                logger.info(
                    "[color_rewriter] ✅ %s | %.1f MB",
                    out_name, size_mb,
                )
                generated.append(out_path)
            else:
                logger.warning("[color_rewriter] ❌ %s palette='%s' échoué", stem, pal_name)

        return generated

    def batch_recolor(
        self,
        input_dir: str,
        palette_names: Optional[List[str]] = None,
        output_dir: str = "./output/colorways",
        glob_pattern: str = "*.png",
    ) -> Dict[str, List[str]]:
        """
        Ré-colorise tous les PNGs d'un dossier.

        Returns:
            Dict {source_filename: [chemins colorways générés]}
        """
        import glob as _glob
        files = sorted(_glob.glob(os.path.join(input_dir, glob_pattern)))
        logger.info(
            "[color_rewriter] batch: %d fichiers × %d palettes",
            len(files), len(palette_names or PALETTES),
        )
        results = {}
        for fp in files:
            generated = self.recolor_file(fp, palette_names, output_dir)
            results[os.path.basename(fp)] = generated
        return results
