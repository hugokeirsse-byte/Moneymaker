"""
Background Remover — supprime le fond blanc des illustrations Redbubble.

Technique : flood-fill depuis les 4 coins vers l'intérieur.
Préserve le blanc dans l'illustration elle-même (texte, reflets, highlights).
Uniquement pour les designs Redbubble (standalone, fond blanc uniforme).

Usage :
    remove_white_background("output/redbubble/frog.png", "output/redbubble/frog_transparent.png")
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


def remove_white_background(
    input_path: str,
    output_path: Optional[str] = None,
    tolerance: int = 28,
    feather: int = 2,
) -> str:
    """
    Supprime le fond blanc par flood-fill depuis les 4 coins.

    Args:
        input_path  : PNG source (fond blanc, illustration centrée)
        output_path : PNG destination (RGBA transparent). Défaut : *_transparent.png
        tolerance   : distance max du blanc pour être considéré fond (0-255)
        feather     : pixels de transition douce sur les bords (antialiasing)

    Returns:
        Chemin du fichier transparent généré.
    """
    from PIL import Image
    from collections import deque

    if output_path is None:
        stem = Path(input_path).stem
        output_path = os.path.join(
            os.path.dirname(input_path),
            f"{stem}_transparent.png",
        )

    img = Image.open(input_path).convert("RGBA")
    data = np.array(img, dtype=np.int32)
    h, w = data.shape[:2]

    # Masque des pixels "fond" — True = fond à rendre transparent
    is_bg = np.zeros((h, w), dtype=bool)

    # Couleur de fond = moyenne des 4 coins (≈ blanc pour nos designs)
    corners = [
        data[0, 0, :3], data[0, w-1, :3],
        data[h-1, 0, :3], data[h-1, w-1, :3],
    ]
    bg_color = np.mean(corners, axis=0)

    def _color_dist(px: np.ndarray) -> float:
        return float(np.sqrt(np.sum((px[:3].astype(float) - bg_color) ** 2)))

    # Flood-fill BFS depuis les 4 coins
    queue: deque = deque()
    visited = np.zeros((h, w), dtype=bool)

    seed_points = [(0, 0), (0, w-1), (h-1, 0), (h-1, w-1)]
    for r, c in seed_points:
        if not visited[r, c] and _color_dist(data[r, c]) <= tolerance * 1.73:
            queue.append((r, c))
            visited[r, c] = True

    neighbors = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    while queue:
        r, c = queue.popleft()
        is_bg[r, c] = True
        for dr, dc in neighbors:
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and not visited[nr, nc]:
                if _color_dist(data[nr, nc]) <= tolerance * 1.73:
                    visited[nr, nc] = True
                    queue.append((nr, nc))

    # Feathering — transition douce sur les bords du masque
    if feather > 0:
        from scipy.ndimage import distance_transform_edt, binary_erosion
        eroded = binary_erosion(is_bg, iterations=feather)
        dist = distance_transform_edt(is_bg) - distance_transform_edt(~is_bg)
        alpha_factor = np.clip((dist + feather) / (2 * feather), 0.0, 1.0)
        alpha_channel = np.where(is_bg, (alpha_factor * 255).astype(np.uint8), 255)
    else:
        alpha_channel = np.where(is_bg, 0, 255).astype(np.uint8)

    result = data.copy().astype(np.uint8)
    result[:, :, 3] = alpha_channel

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    Image.fromarray(result, "RGBA").save(output_path, format="PNG", dpi=(300, 300))

    size_kb = os.path.getsize(output_path) / 1024
    logger.info("[bg_remover] ✅ %s → %.0f KB", Path(output_path).name, size_kb)
    return output_path


def batch_remove_background(
    input_dir: str,
    output_dir: Optional[str] = None,
    tolerance: int = 28,
    suffix: str = "_transparent",
    skip_existing: bool = True,
) -> list:
    """
    Supprime le fond blanc de tous les PNG d'un dossier.

    Args:
        input_dir   : dossier source
        output_dir  : dossier destination (défaut = même que input_dir)
        tolerance   : tolérance couleur fond
        suffix      : suffixe ajouté avant .png
        skip_existing : ignore les fichiers déjà traités

    Returns:
        Liste des chemins générés.
    """
    import glob as _glob

    if output_dir is None:
        output_dir = input_dir
    os.makedirs(output_dir, exist_ok=True)

    files = sorted(_glob.glob(os.path.join(input_dir, "*.png")))
    # Ne traite pas les fichiers déjà transparents
    files = [f for f in files if suffix not in Path(f).stem]

    generated = []
    for fp in files:
        stem = Path(fp).stem
        out_path = os.path.join(output_dir, f"{stem}{suffix}.png")
        if skip_existing and os.path.exists(out_path):
            generated.append(out_path)
            continue
        try:
            path = remove_white_background(fp, out_path, tolerance=tolerance)
            generated.append(path)
        except Exception as exc:
            logger.warning("[bg_remover] %s échoué : %s", fp, exc)

    logger.info("[bg_remover] %d transparents générés → %s", len(generated), output_dir)
    return generated
