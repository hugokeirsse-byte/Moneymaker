#!/usr/bin/env python3
"""
audit_ball.py — contrôle qualité automatique des ballons Telstar générés.

Compare, panneau par panneau, la couleur moyenne de l'image générée à celle
de son SEED géométrique : si FLUX a respecté le blueprint, chaque polygone
(pentagone drapeau / hexagone crème) a une moyenne proche du seed. Les
polygones sont rétrécis de 25 % vers leur centre pour tolérer les petits
décalages et éviter les coutures. Verdict par panneau, exit 1 si FAIL.

Usage: python scripts/audit_ball.py <generee.png> <seed.png> [--tol 75]
"""
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, "scripts")
from render_telstar_seed import truncated_icosahedron, rotation_to_z  # noqa: E402


def front_faces(min_z: float = 0.05):
    V, faces = truncated_icosahedron()
    pent = next(f for f in faces if len(f) == 5)
    R = rotation_to_z(V[pent].mean(axis=0))
    V = V @ R.T
    center = V[pent].mean(axis=0)
    a0 = np.arctan2(V[pent[0]][1] - center[1], V[pent[0]][0] - center[0])
    step = 2 * np.pi / 5
    delta = (np.pi / 2 - a0) % step
    if delta > step / 2:
        delta -= step
    c, s = np.cos(delta), np.sin(delta)
    V = V @ np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]]).T
    out = []
    for f in faces:
        ctr = V[f].mean(axis=0)
        if ctr[2] >= min_z:
            pts = [(float(V[i][0]), float(V[i][1])) for i in f]
            out.append((len(f), pts))
    return out


def panel_mean(arr: np.ndarray, pts, shrink: float = 0.25):
    """Couleur moyenne dans le polygone rétréci vers son centroïde."""
    size = arr.shape[0]
    cx = cy = size / 2
    ball_r = size * 0.355
    gx = sum(p[0] for p in pts) / len(pts)
    gy = sum(p[1] for p in pts) / len(pts)
    poly = []
    for px, py in pts:
        qx = gx + (px - gx) * (1 - shrink)
        qy = gy + (py - gy) * (1 - shrink)
        poly.append((cx + qx * ball_r, cy - qy * ball_r))
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    m = np.array(mask, dtype=bool)
    return arr[m].mean(axis=0)


def audit(gen_path: str, seed_path: str, tol: float = 75.0) -> bool:
    def load(p):
        im = Image.open(p).convert("RGB")
        im = im.resize((1024, 1024), Image.LANCZOS)
        return np.array(im).astype(float)
    gen, seed = load(gen_path), load(seed_path)

    def chroma(v):
        """Chromaticité (proportions RGB) ×384 — invariante à l'ombrage."""
        s = max(v.sum(), 1e-6)
        return v / s * 384.0

    ok = True
    worst = 0.0
    for nsides, pts in front_faces():
        mg = panel_mean(gen, pts)
        ms = panel_mean(seed, pts)
        delta = float(np.abs(chroma(mg) - chroma(ms)).sum())
        worst = max(worst, delta)
        if delta > tol:
            kind = "pentagone" if nsides == 5 else "hexagone"
            gx = sum(p[0] for p in pts) / len(pts)
            gy = sum(p[1] for p in pts) / len(pts)
            print(f"  ❌ {kind} ({gx:+.2f},{gy:+.2f}) : Δcouleur {delta:.0f} > {tol:.0f} "
                  f"(seed {ms.astype(int)} vs généré {mg.astype(int)})")
            ok = False
    print(("✅ PASS" if ok else "🚫 FAIL") + f" — Δmax {worst:.0f} — {gen_path}")
    return ok


if __name__ == "__main__":
    tol = float(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[3] == "--tol" else 75.0
    sys.exit(0 if audit(sys.argv[1], sys.argv[2], tol) else 1)
