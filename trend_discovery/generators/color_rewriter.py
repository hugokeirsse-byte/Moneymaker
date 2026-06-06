"""
Color Rewriter v2 — variantes de coloris par rotation HSV.

Technique : rotation de la roue des teintes (H) + ajustements saturation/luminosité.
Résultat : même motif exact, nouvelle palette, ZÉRO postérisation, ZÉRO "négatif",
tous les dégradés/textures/détails préservés intégralement.

Fonctionne sur les deux types d'images :
  - Motifs IA flat (8 couleurs) : rotation propre
  - Motifs complexes (photos, aquarelle, dégradés) : rotation fluide sans artefact

Usage :
    rewriter = ColorRewriter()
    paths = rewriter.recolor_file(
        "output/spoonflower/art_deco_fans___base.png",
        palette_names=["cool_ocean", "forest_dusk", "rose_gold"],
        output_dir="output/colorways",
    )
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)


# ── Palettes — définies comme transformations HSV ───────────────────────────
# hue_shift    : degrés de rotation de la teinte (0-360, peut être négatif)
# sat_mult     : multiplicateur de saturation (1.0 = aucun changement)
# val_mult     : multiplicateur de luminosité (1.0 = aucun changement)
#
# Principe : pour une image chaleureuse (terre cuite, or, rose),
#   hue_shift=+160° → version froide (bleu-vert); +80° → verts; -40° → roses.
#   Les relations tonales (ombres/lumières/contrastes) restent IDENTIQUES.

PALETTES: Dict[str, Dict] = {
    "cool_ocean": {
        "label": "Cool Ocean",
        "hue_shift": 165,
        "sat_mult": 1.05,
        "val_mult": 0.88,
        "description": "shift vers bleus-teals profonds, luminosité légèrement réduite",
    },
    "forest_dusk": {
        "label": "Forest Dusk",
        "hue_shift": 100,
        "sat_mult": 0.90,
        "val_mult": 0.78,
        "description": "shift vers verts forêt sombres",
    },
    "rose_gold": {
        "label": "Rose Gold",
        "hue_shift": 50,
        "sat_mult": 0.92,
        "val_mult": 1.02,
        "description": "shift vers roses/dorés chauds",
    },
    "midnight": {
        "label": "Midnight",
        "hue_shift": 200,
        "sat_mult": 0.80,
        "val_mult": 0.55,
        "description": "bleu nuit profond, très sombre",
    },
    "lavender_mist": {
        "label": "Lavender Mist",
        "hue_shift": 220,
        "sat_mult": 0.65,
        "val_mult": 1.08,
        "description": "shift vers lavande/lilas clair, désaturé",
    },
    "earth_autumn": {
        "label": "Earth Autumn",
        "hue_shift": -25,
        "sat_mult": 0.88,
        "val_mult": 0.90,
        "description": "shift vers ocre/terracotta/brun, légèrement plus chaud",
    },
    "sage_morning": {
        "label": "Sage Morning",
        "hue_shift": 80,
        "sat_mult": 0.50,
        "val_mult": 1.12,
        "description": "sauge désaturé, très clair, matinal",
    },
    "deep_ruby": {
        "label": "Deep Ruby",
        "hue_shift": -60,
        "sat_mult": 1.10,
        "val_mult": 0.72,
        "description": "shift vers rouges/rubis profonds, saturé",
    },
}

# Alias pour compatibilité avec l'ancien code (noms legacy → nouveaux noms)
_PALETTE_ALIASES: Dict[str, str] = {
    "dark_moody":     "midnight",
    "pastel_soft":    "lavender_mist",
    "earth_tones":    "earth_autumn",
    "navy_mono":      "midnight",
    "forest_green":   "forest_dusk",
    "rose_blush":     "rose_gold",
    "sage_cream":     "sage_morning",
    "midnight_gold":  "deep_ruby",
}


def _resolve_palette(name: str) -> Optional[Dict]:
    resolved = _PALETTE_ALIASES.get(name, name)
    return PALETTES.get(resolved)


def _hsv_rotate(arr_rgb: np.ndarray, hue_shift: float, sat_mult: float, val_mult: float) -> np.ndarray:
    """
    Rotate/adjust HSV of an RGB image array.

    Args:
        arr_rgb   : float32 array shape (H, W, 3), values in [0, 1]
        hue_shift : hue rotation in degrees
        sat_mult  : saturation multiplier
        val_mult  : value (brightness) multiplier

    Returns:
        float32 array (H, W, 3) in [0, 1]
    """
    R = arr_rgb[:, :, 0]
    G = arr_rgb[:, :, 1]
    B = arr_rgb[:, :, 2]

    maxc = np.maximum(np.maximum(R, G), B)
    minc = np.minimum(np.minimum(R, G), B)
    V = maxc.copy()
    delta = maxc - minc

    # Saturation
    S = np.where(maxc > 1e-6, delta / maxc, 0.0)

    # Hue in [0, 6)
    H = np.zeros_like(R)
    eps = 1e-6
    safe_delta = np.where(delta < eps, eps, delta)

    mask_r = (maxc == R) & (delta > eps)
    mask_g = (maxc == G) & (delta > eps) & ~mask_r
    mask_b = ~mask_r & ~mask_g & (delta > eps)

    H[mask_r] = ((G[mask_r] - B[mask_r]) / safe_delta[mask_r]) % 6.0
    H[mask_g] = (B[mask_g] - R[mask_g]) / safe_delta[mask_g] + 2.0
    H[mask_b] = (R[mask_b] - G[mask_b]) / safe_delta[mask_b] + 4.0

    # Apply transformations
    H = (H / 6.0 + hue_shift / 360.0) % 1.0
    S = np.clip(S * sat_mult, 0.0, 1.0)
    V = np.clip(V * val_mult, 0.0, 1.0)

    # HSV → RGB (vectorised)
    h6 = H * 6.0
    i = np.floor(h6).astype(np.int32) % 6
    f = h6 - np.floor(h6)
    p = V * (1.0 - S)
    q = V * (1.0 - S * f)
    t = V * (1.0 - S * (1.0 - f))

    R2 = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5],
                   [V, q, p, p, t, V], default=V)
    G2 = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5],
                   [t, V, V, q, p, p], default=V)
    B2 = np.select([i == 0, i == 1, i == 2, i == 3, i == 4, i == 5],
                   [p, p, t, V, V, q], default=V)

    # Achromatic pixels (S ≈ 0): force grey
    ach = S < 1e-6
    R2[ach] = V[ach]
    G2[ach] = V[ach]
    B2[ach] = V[ach]

    return np.stack([R2, G2, B2], axis=2)


# ── Sélection intelligente de palette basée sur les hex couleurs du CDC ───────

# Plage de teinte (degrés) → palette la plus proche
_HUE_PALETTE_MAP: List[Tuple[Tuple[int, int], str]] = [
    ((0,   20),  "deep_ruby"),        # rouge
    ((20,  45),  "earth_autumn"),     # orange / ambre / terracotta
    ((45,  75),  "rose_gold"),        # jaune / or chaud
    ((75,  150), "forest_dusk"),      # vert
    ((150, 195), "cool_ocean"),       # teal / cyan
    ((195, 265), "midnight"),         # bleu
    ((265, 305), "lavender_mist"),    # violet / lavande
    ((305, 345), "rose_gold"),        # rose / magenta
    ((345, 360), "deep_ruby"),        # rouge (fin de cercle)
]


def _hex_to_hue(hex_color: str) -> Optional[float]:
    """Convertit un hex color en teinte HSV (0-360), ou None si achromatique."""
    try:
        h = hex_color.lstrip("#")
        if len(h) not in (6, 8):
            return None
        r, g, b = int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0
        maxc, minc = max(r, g, b), min(r, g, b)
        delta = maxc - minc
        if delta < 0.08 or maxc < 0.05:  # achromatique ou trop sombre
            return None
        if maxc == r:
            hue = ((g - b) / delta) % 6.0
        elif maxc == g:
            hue = (b - r) / delta + 2.0
        else:
            hue = (r - g) / delta + 4.0
        return (hue / 6.0) * 360.0
    except Exception:
        return None


def _extract_hex_colors(brief: dict) -> List[str]:
    """Extrait tous les codes hex du CDC (palette primaire + accent + fond)."""
    import re
    hexes = []
    vd = brief.get("visual_direction", {}) or {}
    cp = vd.get("color_palette", {}) or {}
    for source in [cp.get("primary", []), cp.get("accent", []), [cp.get("background", "")]]:
        if isinstance(source, list):
            for item in source:
                found = re.findall(r"#[0-9A-Fa-f]{6}", str(item))
                hexes.extend(found)
        elif isinstance(source, str):
            found = re.findall(r"#[0-9A-Fa-f]{6}", source)
            hexes.extend(found)
    # Also check assembly_guide and elements
    ag = brief.get("assembly_guide", {}) or {}
    for item in [ag.get("background_color", ""), str(ag.get("color_palette", []))]:
        hexes.extend(re.findall(r"#[0-9A-Fa-f]{6}", str(item)))
    return list(dict.fromkeys(hexes))  # deduplicate, preserve order


def _hue_to_palette(hue_deg: float) -> str:
    """Retourne le nom de palette le plus proche pour une teinte donnée."""
    for (lo, hi), pal in _HUE_PALETTE_MAP:
        if lo <= hue_deg < hi:
            return pal
    return "earth_autumn"


def select_palettes_for_cdc(hex_colors: List[str], n: int = 4) -> List[str]:
    """
    Sélectionne les n palettes HSV les plus pertinentes pour une liste de hex couleurs.

    Priorité : couleurs saturées et lisibles d'abord, achromatiques ignorées.
    Toujours retourne exactement n palettes (complétion avec palettes génériques si besoin).

    Args:
        hex_colors : liste de codes hex extraits du CDC
        n          : nombre de palettes à retourner (défaut 4)

    Returns:
        Liste de n noms de palettes de PALETTES.
    """
    defaults = ["cool_ocean", "earth_autumn", "midnight", "rose_gold"]
    if not hex_colors:
        return defaults[:n]

    selected = []
    for hex_col in hex_colors:
        hue = _hex_to_hue(hex_col)
        if hue is not None:
            pal = _hue_to_palette(hue)
            if pal not in selected:
                selected.append(pal)
        if len(selected) >= n:
            break

    # Complétion avec les defaults si pas assez de couleurs saturées
    for pal in defaults:
        if pal not in selected:
            selected.append(pal)
        if len(selected) >= n:
            break

    return selected[:n]


class ColorRewriter:
    """
    Ré-colorise un motif PNG par rotation HSV.

    Contrairement au k-means, cette technique :
    - Préserve 100 % du détail (dégradés, textures, anti-aliasing)
    - Évite toute postérisation ou effet "négatif"
    - Fonctionne sur motifs plats ET motifs complexes/aquarelle
    """

    def recolor(self, image_bytes: bytes, palette_name: str) -> Optional[bytes]:
        """
        Ré-colorise une image (bytes) selon une palette nommée.

        Returns:
            Bytes PNG ré-colorisé, ou None en cas d'erreur.
        """
        try:
            import io
            from PIL import Image

            palette = _resolve_palette(palette_name)
            if not palette:
                logger.error("[color_rewriter] palette inconnue: %s", palette_name)
                return None

            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            arr = np.array(img).astype(np.float32) / 255.0

            new_arr = _hsv_rotate(
                arr,
                hue_shift=palette["hue_shift"],
                sat_mult=palette["sat_mult"],
                val_mult=palette["val_mult"],
            )

            new_arr = np.clip(new_arr * 255.0, 0, 255).astype(np.uint8)
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
            input_path    : chemin vers le PNG source
            palette_names : liste de palettes (défaut: toutes)
            output_dir    : dossier de sortie

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
            pal_info = _resolve_palette(pal_name) or {}
            logger.info(
                "[color_rewriter] '%s' → '%s' (%s)…",
                stem[:40], pal_name, pal_info.get("label", ""),
            )
            result = self.recolor(image_bytes, pal_name)
            if result:
                out_name = f"{stem}__{pal_name}.png"
                out_path = os.path.join(output_dir, out_name)
                with open(out_path, "wb") as fh:
                    fh.write(result)
                size_mb = os.path.getsize(out_path) / 1024 / 1024
                logger.info("[color_rewriter] ✅ %s | %.1f MB", out_name, size_mb)
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
        """Ré-colorise tous les PNGs d'un dossier."""
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

    def batch_recolor_smart(
        self,
        input_dir: str,
        reports_dir: str = "./reports",
        output_dir: str = "./output/colorways",
        glob_pattern: str = "*.png",
        fallback_palettes: Optional[List[str]] = None,
    ) -> Dict[str, List[str]]:
        """
        Ré-colorise tous les PNGs en sélectionnant automatiquement les 4 palettes
        les plus pertinentes pour chaque design selon les hex couleurs de son CDC.

        Si aucun CDC correspondant n'est trouvé, repli sur fallback_palettes
        (défaut: cool_ocean, earth_autumn, midnight, rose_gold).
        """
        import glob as _glob
        from trend_discovery.generators.listing_generator import load_all_briefs, _slug

        fallback = fallback_palettes or ["cool_ocean", "earth_autumn", "midnight", "rose_gold"]
        sf_briefs, _ = load_all_briefs(reports_dir)
        files = sorted(_glob.glob(os.path.join(input_dir, glob_pattern)))
        results = {}

        for fp in files:
            stem = Path(fp).stem
            # Extraire le slug niche depuis le nom de fichier
            import re
            m = re.match(r"^(.+?)___base_", stem)
            niche_slug = m.group(1) if m else stem

            # Chercher le CDC correspondant
            brief = None
            for b in sf_briefs:
                if _slug(b.get("name", "")) == niche_slug:
                    brief = b
                    break

            if brief:
                hex_colors = _extract_hex_colors(brief)
                palettes = select_palettes_for_cdc(hex_colors) if hex_colors else fallback
                logger.info(
                    "[color_rewriter] %s → palettes CDC: %s", stem[:40], palettes
                )
            else:
                palettes = fallback
                logger.debug("[color_rewriter] %s → palettes génériques (CDC non trouvé)", stem[:40])

            generated = self.recolor_file(fp, palettes, output_dir)
            results[os.path.basename(fp)] = generated

        return results
