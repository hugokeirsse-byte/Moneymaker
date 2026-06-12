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

    # balayage radial : dernier rayon où l'anneau contient encore du non-feutre.
    # Seuil bas (8 %) + continuité sur 3 anneaux : les liserés sombres à
    # pointillés dorés (Allemagne, Belgique…) n'ont que ~20 % de pixels clairs.
    rmax = min(h, w) / 2
    radius = 0.0
    radii = np.arange(rmax - 2, min(h, w) * 0.2, -4)
    fracs = []
    for r in radii:
        ring = (dist >= r - 4) & (dist < r)
        fracs.append(not_felt[ring].mean())
    for i, r in enumerate(radii[:-3]):
        if fracs[i] > 0.08 and fracs[i + 1] > 0.05 and fracs[i + 2] > 0.05:
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


def cutout_felt(in_path: str, out_path: str, feather: int = 3) -> None:
    """Détourage forme libre : tout ce qui a la couleur du feutre (échantillonnée
    sur les bords) ET touche le bord devient transparent. Préserve les éléments
    du design qui débordent (capes, objets…) contrairement au masque cercle.
    Gère les ombres portées : un pixel est « feutre » s'il est proche du RAYON
    de couleur du feutre (feutre assombri/éclairci compris). Pixels intacts."""
    
    img = Image.open(in_path).convert("RGB")
    arr = np.array(img)
    h, w = arr.shape[:2]
    k = max(8, int(min(h, w) * 0.04))
    corners = np.concatenate([
        arr[:k, :k].reshape(-1, 3), arr[:k, -k:].reshape(-1, 3),
        arr[-k:, :k].reshape(-1, 3), arr[-k:, -k:].reshape(-1, 3),
    ]).astype(float)
    felt = corners.mean(axis=0)
    tol = max(30.0, corners.std(axis=0).mean() * 4) * 3

    # projection de chaque pixel sur le rayon de couleur du feutre :
    # p ≈ t·felt avec t ∈ [0.35, 1.45] couvre feutre + ombres + fibres claires
    p = arr.astype(float)
    f2 = float(felt.dot(felt))
    t = np.clip((p @ felt) / f2, 0.35, 1.45)
    residual = np.abs(p - t[..., None] * felt[None, None, :]).sum(axis=2)
    feltlike = residual <= tol

    # fond = composantes connexes « feutre » touchant le bord (vectorisé : ms
    # au lieu de minutes — le BFS Python pur dépassait le timeout CI)
    from scipy.ndimage import label as cc_label
    labels, _ = cc_label(feltlike)
    border_labels = np.unique(np.concatenate([
        labels[0, :], labels[-1, :], labels[:, 0], labels[:, -1]]))
    border_labels = border_labels[border_labels != 0]
    bg = np.isin(labels, border_labels)

    # adoucissement du bord : érosion progressive sur `feather` px
    alpha = np.where(bg, 0, 255).astype(float)
    try:
        from scipy.ndimage import distance_transform_edt
        dist_in = distance_transform_edt(~bg)
        alpha = np.clip(dist_in / feather, 0.0, 1.0) * 255
    except ImportError:
        pass
    pct = 100 * bg.mean()
    # garde-fou : <5% = pas de vrai fond uni ; >75% = la scène serait détruite
    if pct < 5 or pct > 75:
        raise RuntimeError(f"fond {pct:.0f}% — non détourable proprement, ignorée")
    rgba = np.dstack([arr, alpha.astype(np.uint8)])
    Image.fromarray(rgba, "RGBA").save(out_path, format="PNG", dpi=(300, 300), optimize=False)
    print(f"+ {os.path.basename(out_path)} : fond {pct:.0f}% transparent (forme libre)")


def shrink_to_limit(in_path: str, out_path: str, limit_mb: float = 19.0) -> None:
    """Variante plateforme à taille plafonnée (TeePublic < 20 Mo) : PNG optimisé,
    puis réduction LANCZOS progressive jusqu'à passer sous la limite. Le mode
    couleur (RGB/RGBA) et le DPI sont préservés ; l'original n'est pas modifié."""
    img = Image.open(in_path)
    limit = limit_mb * 1024 * 1024
    # >12 MP en RGBA ne passe jamais sous 19 Mo : inutile de tenter la taille
    # native (l'encodage PNG 20 MP + optimize prenait ~2 min/image et faisait
    # sauter le timeout CI). On part directement de 3500 px, sans optimize.
    candidates = [s for s in (img.size[0], 3500, 3000, 2600, 2200)
                  if s * s <= 12_000_000 or s != img.size[0]]
    for side in candidates:
        im = img if side >= img.size[0] else img.resize(
            (side, int(img.size[1] * side / img.size[0])), Image.LANCZOS)
        im.save(out_path, format="PNG", dpi=(300, 300), optimize=False)
        size = os.path.getsize(out_path)
        if size <= limit:
            print(f"+ {os.path.basename(out_path)} : {im.size[0]}px, {size/1e6:.1f} Mo")
            return
    raise RuntimeError(f"{in_path}: impossible de passer sous {limit_mb} Mo")


def main() -> int:
    if sys.argv[1] == "--batch":
        src, dst = sys.argv[2], sys.argv[3]
        mode = sys.argv[5] if len(sys.argv) > 5 and sys.argv[4] == "--mode" else "circle"
        os.makedirs(dst, exist_ok=True)
        ok, ko = 0, []
        for root, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d != "thumbnails"]
            for f in sorted(files):
                if not f.lower().endswith(".png"):
                    continue
                out = os.path.join(dst, f)
                try:
                    if mode == "felt":
                        cutout_felt(os.path.join(root, f), out)
                    elif mode == "shrink":
                        shrink_to_limit(os.path.join(root, f), out)
                    else:
                        cutout(os.path.join(root, f), out)
                    ok += 1
                except Exception as exc:  # noqa: BLE001
                    ko.append((f, str(exc)))
        print(f"{ok} images détourées → {dst}")
        for f, e in ko:
            print(f"  ⏭️ {f}: {e}")
        return 0
    pad = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[3] == "--pad" else 6
    cutout(sys.argv[1], sys.argv[2], pad=pad)
    return 0


if __name__ == "__main__":
    sys.exit(main())
