#!/usr/bin/env python3
"""
cutout_circle.py — détourage circulaire sans perte pour les patchs ronds.

Les patchs sont des cercles centrés sur fond feutre : on détecte le rayon réel
du patch (transition feutre → cordelette) puis on rend transparent tout ce qui
est hors du cercle, avec un bord adouci de quelques pixels (anti-crénelage).
Aucune retouche des pixels intérieurs : qualité d'origine intacte.

Usage:
    python scripts/cutout_circle.py <in.png> <out.png> [--pad 6]
    python scripts/cutout_circle.py --batch <dossier_in> <dossier_out>
"""
import os
import sys

import numpy as np
from PIL import Image


def detect_radius(arr: np.ndarray) -> float:
    """Rayon du patch : distance au centre où l'on quitte la couleur du feutre."""
    h, w = arr.shape[:2]
    cy, cx = h / 2, w / 2
    # couleur du feutre = moyenne des 4 coins (carrés de 4 % du côté)
    k = max(8, int(min(h, w) * 0.04))
    corners = np.concatenate([
        arr[:k, :k].reshape(-1, 3), arr[:k, -k:].reshape(-1, 3),
        arr[-k:, :k].reshape(-1, 3), arr[-k:, -k:].reshape(-1, 3),
    ]).astype(float)
    felt = corners.mean(axis=0)
    tol = max(34.0, corners.std(axis=0).mean() * 4)

    yy, xx = np.ogrid[:h, :w]
    dist = np.sqrt((yy - cy) ** 2 + (xx - cx) ** 2)
    not_felt = (np.abs(arr.astype(float) - felt).sum(axis=2) > tol * 3)

    # balayage radial : dernier rayon où l'anneau contient encore du non-feutre
    rmax = min(h, w) / 2
    radius = 0.0
    for r in np.arange(rmax - 2, min(h, w) * 0.2, -4):
        ring = (dist >= r - 4) & (dist < r)
        if not_felt[ring].mean() > 0.35:
            radius = float(r)
            break
    if not radius:
        raise RuntimeError("cercle du patch introuvable")
    return radius


def cutout(in_path: str, out_path: str, pad: int = 6, feather: int = 3) -> None:
    img = Image.open(in_path).convert("RGB")
    arr = np.array(img)
    h, w = arr.shape[:2]
    radius = detect_radius(arr) + pad

    yy, xx = np.ogrid[:h, :w]
    dist = np.sqrt((yy - h / 2) ** 2 + (xx - w / 2) ** 2)
    # alpha : 255 dedans, 0 dehors, transition linéaire sur `feather` px
    alpha = np.clip((radius - dist) / feather, 0.0, 1.0) * 255

    rgba = np.dstack([arr, alpha.astype(np.uint8)])
    out = Image.fromarray(rgba, "RGBA")
    out.save(out_path, format="PNG", dpi=(300, 300), optimize=False)
    print(f"+ {os.path.basename(out_path)} : rayon {radius:.0f}px / {w}px, fond transparent")


def main() -> int:
    if sys.argv[1] == "--batch":
        src, dst = sys.argv[2], sys.argv[3]
        os.makedirs(dst, exist_ok=True)
        n = 0
        for f in sorted(os.listdir(src)):
            if f.lower().endswith(".png"):
                cutout(os.path.join(src, f), os.path.join(dst, f))
                n += 1
        print(f"{n} images détourées → {dst}")
        return 0
    pad = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[3] == "--pad" else 6
    cutout(sys.argv[1], sys.argv[2], pad=pad)
    return 0


if __name__ == "__main__":
    sys.exit(main())
