"""
specimen_assembler.py — Assemble des illustrations individuelles en seamless repeat.

Prend N PNGs standalone (planches naturalistes, stickers, etc.) et les dispose
en scatter tossed sur un fond uni, avec wrapping seamless pour Spoonflower.

Le tile résultant est 4500×4500px 300DPI, seamless sur les 4 bords.

Principe seamless : chaque élément dont le bounding-box dépasse un bord du tile
est aussi collé décalé de ±tile_size de l'autre côté — les bords du tile
s'interlockent donc parfaitement en repeat.
"""
from __future__ import annotations

import logging
import math
import os
import random
from pathlib import Path
from typing import List, Optional, Tuple

from PIL import Image, ImageEnhance

logger = logging.getLogger(__name__)

# ── Palettes de fond prédéfinies ──────────────────────────────────────────────

BACKGROUNDS = {
    "navy":     "#1B2A3B",   # musée d'histoire naturelle (fond foncé)
    "charcoal": "#2A2A2A",   # cabinet de curiosités
    "forest":   "#1A2F1A",   # naturaliste forêt
    "ivory":    "#F5F0E8",   # herbarium / parchemin
    "cream":    "#FFF8E7",   # planche botanique claire
    "white":    "#FFFFFF",   # fond blanc pur
    "slate":    "#1F2535",   # ardoise foncée
}


def _hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    h = hex_color.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _load_specimen(path: str, max_dim: int) -> Optional[Image.Image]:
    """
    Charge un PNG specimen, le rend RGBA, retire éventuellement le fond blanc.
    Redimensionne à max_dim sur le grand côté.
    """
    try:
        img = Image.open(path).convert("RGBA")
        # Si le fond est blanc, on le rend transparent
        img = _remove_white_bg(img)
        # Redimensionne en préservant le ratio
        w, h = img.size
        scale = max_dim / max(w, h)
        new_w, new_h = int(w * scale), int(h * scale)
        img = img.resize((new_w, new_h), Image.LANCZOS)
        return img
    except Exception as exc:
        logger.warning("[assembler] impossible de charger %s : %s", path, exc)
        return None


def _remove_white_bg(img: Image.Image, threshold: int = 240) -> Image.Image:
    """
    Rend transparent le fond presque blanc (pour les stickers sur fond blanc).
    Utilise un masque simple basé sur la luminosité.
    Préserve les zones qui ne sont pas du fond.
    """
    img = img.convert("RGBA")
    data = img.getdata()
    new_data = []
    for r, g, b, a in data:
        if r > threshold and g > threshold and b > threshold:
            new_data.append((r, g, b, 0))
        else:
            new_data.append((r, g, b, a))
    img.putdata(new_data)
    return img


def _paste_seamless(
    canvas: Image.Image,
    element: Image.Image,
    cx: int,
    cy: int,
    tile: int,
) -> None:
    """
    Colle un élément centré en (cx, cy) et duplique les parties
    qui débordent du tile pour assurer la seamlessness.
    """
    w, h = element.size
    x0 = cx - w // 2
    y0 = cy - h // 2

    # Offsets à tester pour couvrir tous les bords et coins
    offsets = [(0, 0)]
    if x0 < 0:
        offsets.append((tile, 0))
    if x0 + w > tile:
        offsets.append((-tile, 0))
    if y0 < 0:
        offsets.append((0, tile))
    if y0 + h > tile:
        offsets.append((0, -tile))
    # Coins
    if x0 < 0 and y0 < 0:
        offsets.append((tile, tile))
    if x0 + w > tile and y0 < 0:
        offsets.append((-tile, tile))
    if x0 < 0 and y0 + h > tile:
        offsets.append((tile, -tile))
    if x0 + w > tile and y0 + h > tile:
        offsets.append((-tile, -tile))

    for dx, dy in offsets:
        canvas.paste(element, (x0 + dx, y0 + dy), element)


def assemble_naturalist_pattern(
    specimen_paths: List[str],
    output_path: str,
    tile_size: int = 4500,
    background: str = "navy",
    n_specimens: int = 9,
    scale_min: float = 0.14,
    scale_max: float = 0.30,
    rotation_range: float = 18.0,
    min_margin_pct: float = 0.05,
    dpi: int = 300,
    seed: int = 42,
    density_mode: str = "scatter",  # "scatter" | "grid"
    opacity_variation: bool = True,
) -> str:
    """
    Assemble des specimens en seamless repeat tossed/scattered.

    Args:
        specimen_paths:  Liste de chemins vers les PNGs individuels.
        output_path:     Chemin de sortie du tile seamless.
        tile_size:       Taille du tile carré en pixels (défaut : 4500).
        background:      Clé de BACKGROUNDS ou #HEXCODE direct.
        n_specimens:     Nombre de specimens à placer dans le tile.
        scale_min/max:   Plage de taille des specimens en fraction du tile.
        rotation_range:  Rotation max en degrés (±).
        min_margin_pct:  Centre des specimens ≥ cette marge depuis les bords.
        dpi:             DPI de sortie (300 pour Spoonflower).
        seed:            Graine aléatoire pour reproductibilité.
        density_mode:    "scatter" = aléatoire, "grid" = grille régulière.
        opacity_variation: légère variation d'opacité entre specimens (profondeur).

    Returns:
        output_path
    """
    rng = random.Random(seed)

    # Résolution du fond
    bg_hex = BACKGROUNDS.get(background, background)
    bg_rgb = _hex_to_rgb(bg_hex)
    canvas = Image.new("RGB", (tile_size, tile_size), bg_rgb)

    if not specimen_paths:
        logger.error("[assembler] aucun specimen fourni")
        return output_path

    # Charge les specimens disponibles
    max_specimen_dim = int(tile_size * scale_max)
    loaded = []
    for p in specimen_paths:
        img = _load_specimen(p, max_specimen_dim)
        if img:
            loaded.append(img)

    if not loaded:
        logger.error("[assembler] aucun specimen chargé")
        return output_path

    logger.info("[assembler] %d specimens chargés, %d à placer", len(loaded), n_specimens)

    margin = int(tile_size * min_margin_pct)

    # Génère les positions
    if density_mode == "grid":
        positions = _grid_positions(n_specimens, tile_size, margin, rng)
    else:
        positions = _scatter_positions(n_specimens, tile_size, margin, rng)

    # Place chaque specimen
    for i, (cx, cy) in enumerate(positions):
        # Cycle sur les specimens disponibles si n_specimens > len(loaded)
        specimen = loaded[i % len(loaded)]

        # Scale aléatoire
        scale = rng.uniform(scale_min, scale_max)
        target_dim = int(tile_size * scale)
        w, h = specimen.size
        factor = target_dim / max(w, h)
        new_w, new_h = max(1, int(w * factor)), max(1, int(h * factor))
        scaled = specimen.resize((new_w, new_h), Image.LANCZOS)

        # Rotation aléatoire
        angle = rng.uniform(-rotation_range, rotation_range)
        if abs(angle) > 0.5:
            scaled = scaled.rotate(angle, expand=True, resample=Image.BICUBIC)

        # Opacité légèrement variée (effet de profondeur)
        if opacity_variation:
            opacity = rng.uniform(0.82, 1.0)
            if opacity < 0.99:
                r, g, b, a = scaled.split()
                a = a.point(lambda x: int(x * opacity))
                scaled = Image.merge("RGBA", (r, g, b, a))

        _paste_seamless(canvas, scaled, cx, cy, tile_size)

    # Sauvegarde 300 DPI
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    canvas.save(output_path, format="PNG", dpi=(dpi, dpi))
    logger.info("[assembler] tile seamless → %s (%dx%d, %d DPI)",
                output_path, tile_size, tile_size, dpi)
    return output_path


def _scatter_positions(
    n: int, tile: int, margin: int, rng: random.Random
) -> List[Tuple[int, int]]:
    """Positions aléatoires, centres dans [margin, tile-margin]."""
    lo, hi = margin, tile - margin
    return [(rng.randint(lo, hi), rng.randint(lo, hi)) for _ in range(n)]


def _grid_positions(
    n: int, tile: int, margin: int, rng: random.Random
) -> List[Tuple[int, int]]:
    """
    Grille régulière légèrement perturbée — look moins mécanique
    qu'un grid strict mais plus régulier que scatter pur.
    """
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    cell_w = (tile - 2 * margin) // cols
    cell_h = (tile - 2 * margin) // rows
    jitter_x = cell_w // 5
    jitter_y = cell_h // 5
    positions = []
    idx = 0
    for row in range(rows):
        for col in range(cols):
            if idx >= n:
                break
            cx = margin + col * cell_w + cell_w // 2 + rng.randint(-jitter_x, jitter_x)
            cy = margin + row * cell_h + cell_h // 2 + rng.randint(-jitter_y, jitter_y)
            positions.append((cx, cy))
            idx += 1
    return positions


# ── CLI batch ──────────────────────────────────────────────────────────────────

def batch_assemble(
    input_dir: str,
    output_dir: str,
    background: str = "navy",
    n_specimens: int = 9,
    scale_min: float = 0.14,
    scale_max: float = 0.30,
    rotation_range: float = 18.0,
    tile_size: int = 4500,
    seed: int = 42,
    glob_pattern: str = "*.png",
    variants: int = 1,
) -> List[str]:
    """
    Assemble tous les PNGs d'un dossier en un ou plusieurs tiles seamless.

    Args:
        input_dir:    Dossier des specimens individuels.
        output_dir:   Dossier de sortie.
        background:   Fond (clé ou #HEX).
        n_specimens:  Specimens par tile.
        variants:     Nombre de tiles avec seeds différentes (ex: 3 = 3 compositions).

    Returns:
        Liste des fichiers générés.
    """
    from pathlib import Path as _P
    specimens = sorted(_P(input_dir).glob(glob_pattern))
    specimens = [str(p) for p in specimens if not p.stem.endswith("_seamless")]

    if not specimens:
        logger.warning("[assembler] aucun PNG trouvé dans %s", input_dir)
        return []

    _P(output_dir).mkdir(parents=True, exist_ok=True)
    results = []

    for v in range(variants):
        bg_name = background.lstrip("#")[:8]
        out_name = f"naturalist_seamless_{bg_name}_v{v+1:02d}.png"
        out_path = str(_P(output_dir) / out_name)

        assemble_naturalist_pattern(
            specimen_paths=specimens,
            output_path=out_path,
            tile_size=tile_size,
            background=background,
            n_specimens=n_specimens,
            scale_min=scale_min,
            scale_max=scale_max,
            rotation_range=rotation_range,
            seed=seed + v * 1337,
        )
        results.append(out_path)
        logger.info("[assembler] variant %d/%d → %s", v + 1, variants, out_name)

    return results
