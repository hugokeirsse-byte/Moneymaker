#!/usr/bin/env python3
"""
render_telstar_seed.py — ballon Telstar mathématiquement exact (icosaèdre
tronqué : 12 pentagones + 20 hexagones), pentagones remplis du drapeau EXACT
du pays, hexagones crème, anneau aux couleurs du pays sur feutre sombre.
Sert d'image de référence (FLUX.2 referenceImages) : géométrie et drapeaux
garantis par le code, le modèle n'ajoute que le rendu broderie.

Usage: python scripts/render_telstar_seed.py <country_id> <out.png> [--size 2048]
"""
import sys
import math
import itertools
import numpy as np
from PIL import Image, ImageDraw
from scipy.spatial import ConvexHull

PHI = (1 + 5 ** 0.5) / 2

FELT = (38, 36, 40)
CREAM = (244, 240, 228)
SEAM = (18, 18, 24)


# ───────────────────────── peintres de drapeaux EXACTS ─────────────────────────
# Chaque peintre remplit le rectangle (x0,y0,x1,y1) avec la vraie structure du
# drapeau ; le masque pentagone fait le découpage ensuite.

def _star(td, cx, cy, r, color, points=5, rot=-math.pi / 2):
    pts = []
    for k in range(points * 2):
        rad = r if k % 2 == 0 else r * 0.4
        a = rot + k * math.pi / points
        pts.append((cx + rad * math.cos(a), cy + rad * math.sin(a)))
    td.polygon(pts, fill=color)


def flag_france(td, x0, y0, x1, y1):
    w = (x1 - x0) / 3
    for k, col in enumerate([(0, 85, 164), (255, 255, 255), (239, 65, 53)]):
        td.rectangle([x0 + k * w, y0, x0 + (k + 1) * w, y1], fill=col)


def flag_usa(td, x0, y0, x1, y1):
    red, white, navy = (178, 34, 52), (255, 255, 255), (60, 59, 110)
    h = y1 - y0
    stripe = h / 13
    for i in range(13):
        td.rectangle([x0, y0 + i * stripe, x1, y0 + (i + 1) * stripe],
                     fill=red if i % 2 == 0 else white)
    cw = (x1 - x0) * 0.45
    ch = 7 * stripe
    td.rectangle([x0, y0, x0 + cw, y0 + ch], fill=navy)
    # 9 rangées alternées 6/5 — layout réel des 50 étoiles
    rstar = min(cw / 14, ch / 20)
    for row in range(9):
        n = 6 if row % 2 == 0 else 5
        cy = y0 + ch * (row + 1) / 10
        for col in range(n):
            cx = x0 + cw * (col + 1) / (n + 1) + (0 if row % 2 == 0 else cw * 0.0)
            _star(td, cx, cy, rstar, white)


FLAGS = {
    # pays: (peintre, (couleur anneau extérieur, couleur anneau intérieur))
    "france": (flag_france, ((212, 175, 55), (16, 24, 64))),       # or + navy
    "usa": (flag_usa, ((60, 59, 110), (178, 34, 52))),             # navy + rouge
    "england": (None, ((200, 16, 46), (255, 255, 255))),           # rouge + blanc
    "mexico": (None, ((0, 104, 71), (206, 17, 38))),               # vert + rouge
    "canada": (None, ((216, 30, 5), (255, 255, 255))),             # rouge + blanc
    "germany": (None, ((0, 0, 0), (255, 206, 0))),                 # noir + or
    "brazil": (None, ((0, 151, 57), (254, 221, 0))),               # vert + or
}


def flag_england(td, x0, y0, x1, y1):
    """Croix de St George : croix rouge (largeur 1/5 de la hauteur) sur blanc."""
    red, white = (200, 16, 46), (255, 255, 255)
    td.rectangle([x0, y0, x1, y1], fill=white)
    h = y1 - y0
    bar = h / 5
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    td.rectangle([x0, cy - bar / 2, x1, cy + bar / 2], fill=red)
    td.rectangle([cx - bar / 2, y0, cx + bar / 2, y1], fill=red)


def flag_germany(td, x0, y0, x1, y1):
    """Trois bandes horizontales noir / rouge / or."""
    h = (y1 - y0) / 3
    for k, col in enumerate([(0, 0, 0), (221, 0, 0), (255, 206, 0)]):
        td.rectangle([x0, y0 + k * h, x1, y0 + (k + 1) * h], fill=col)


def _maple_leaf(td, cx, cy, s, color):
    """Feuille d'érable stylisée (silhouette symétrique à 11 pointes)."""
    half = [(0.00, -1.00), (0.10, -0.62), (0.32, -0.78), (0.26, -0.42),
            (0.58, -0.52), (0.48, -0.22), (0.92, -0.26), (0.66, 0.06),
            (0.84, 0.30), (0.40, 0.26), (0.46, 0.62), (0.12, 0.40),
            (0.06, 0.42)]
    pts = half + [(0.04, 1.00), (-0.04, 1.00)] + [(-x, y) for x, y in reversed(half)]
    td.polygon([(cx + x * s, cy + y * s) for x, y in pts], fill=color)


def flag_canada(td, x0, y0, x1, y1):
    """Bandes rouge / blanc / rouge (1:2:1) + feuille d'érable rouge au centre."""
    red, white = (216, 30, 5), (255, 255, 255)
    w = x1 - x0
    td.rectangle([x0, y0, x0 + w / 4, y1], fill=red)
    td.rectangle([x0 + w / 4, y0, x1 - w / 4, y1], fill=white)
    td.rectangle([x1 - w / 4, y0, x1, y1], fill=red)
    _maple_leaf(td, (x0 + x1) / 2, (y0 + y1) / 2, (y1 - y0) * 0.30, red)


def flag_mexico(td, x0, y0, x1, y1):
    """Bandes verticales vert / blanc / rouge + emblème aigle simplifié au centre."""
    green, white, red = (0, 104, 71), (255, 255, 255), (206, 17, 38)
    w = (x1 - x0) / 3
    for k, col in enumerate([green, white, red]):
        td.rectangle([x0 + k * w, y0, x0 + (k + 1) * w, y1], fill=col)
    # aigle stylisé brun-doré perché, ailes ouvertes (silhouette simple)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    s = (y1 - y0) * 0.16
    brown = (107, 68, 35)
    td.polygon([(cx - s, cy), (cx - s * 0.3, cy - s * 0.7), (cx, cy - s * 0.4),
                (cx + s * 0.3, cy - s * 0.7), (cx + s, cy), (cx + s * 0.4, cy + s * 0.3),
                (cx, cy + s * 0.7), (cx - s * 0.4, cy + s * 0.3)], fill=brown)
    td.arc([cx - s, cy + s * 0.4, cx + s, cy + s * 1.1], 200, 340,
           fill=(0, 104, 71), width=max(2, int(s * 0.18)))


def flag_brazil(td, x0, y0, x1, y1):
    """Champ vert, losange or, cercle bleu avec bande blanche (sans texte)."""
    green, gold, blue, white = (0, 151, 57), (254, 221, 0), (0, 39, 118), (255, 255, 255)
    td.rectangle([x0, y0, x1, y1], fill=green)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    w, h = (x1 - x0) * 0.42, (y1 - y0) * 0.42
    td.polygon([(cx, cy - h), (cx + w, cy), (cx, cy + h), (cx - w, cy)], fill=gold)
    r = min(w, h) * 0.62
    td.ellipse([cx - r, cy - r, cx + r, cy + r], fill=blue)
    td.arc([cx - r * 1.05, cy - r * 0.55, cx + r * 1.05, cy + r * 1.45], 200, 320,
           fill=white, width=max(2, int(r * 0.18)))
    for dx, dy in [(-0.4, 0.35), (0.1, 0.5), (0.45, 0.2), (-0.1, -0.05), (0.25, 0.65)]:
        _star(td, cx + dx * r, cy + dy * r, r * 0.07, white)


FLAGS["england"] = (flag_england, FLAGS["england"][1])
FLAGS["mexico"] = (flag_mexico, FLAGS["mexico"][1])
FLAGS["canada"] = (flag_canada, FLAGS["canada"][1])
FLAGS["germany"] = (flag_germany, FLAGS["germany"][1])
FLAGS["brazil"] = (flag_brazil, FLAGS["brazil"][1])


# ───────────────────────── géométrie icosaèdre tronqué ─────────────────────────

def truncated_icosahedron():
    base = [(0, 1, 3 * PHI), (1, 2 + PHI, 2 * PHI), (PHI, 2, 2 * PHI + 1)]
    verts = set()
    for x, y, z in base:
        for sx, sy, sz in itertools.product((1, -1), repeat=3):
            v = (sx * x, sy * y, sz * z)
            for p in ((v[0], v[1], v[2]), (v[1], v[2], v[0]), (v[2], v[0], v[1])):
                verts.add(tuple(round(c, 9) for c in p))
    V = np.array(sorted(verts))
    V /= np.linalg.norm(V, axis=1).max()

    hull = ConvexHull(V)
    groups = {}
    for simplex, eq in zip(hull.simplices, hull.equations):
        key = tuple(np.round(eq, 5))
        groups.setdefault(key, set()).update(simplex)
    faces = []
    for key, idx in groups.items():
        idx = list(idx)
        normal = np.array(key[:3])
        center = V[idx].mean(axis=0)
        ref = V[idx[0]] - center
        ref -= normal * ref.dot(normal)
        ref /= np.linalg.norm(ref)
        ortho = np.cross(normal, ref)
        ang = [np.arctan2((V[i] - center).dot(ortho), (V[i] - center).dot(ref)) for i in idx]
        faces.append([i for _, i in sorted(zip(ang, idx))])
    return V, faces


def rotation_to_z(v):
    v = v / np.linalg.norm(v)
    z = np.array([0.0, 0.0, 1.0])
    axis = np.cross(v, z)
    s = np.linalg.norm(axis)
    if s < 1e-9:
        return np.eye(3) if v[2] > 0 else np.diag([1.0, -1.0, -1.0])
    axis /= s
    c = v.dot(z)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + s * K + (1 - c) * K @ K


def render(country: str, out_path: str, size: int = 2048):
    painter, (ring_outer, ring_inner) = FLAGS[country]
    V, faces = truncated_icosahedron()

    # pentagone face caméra, puis redressé (pointe en haut, axe vertical)
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

    img = Image.new("RGB", (size, size), FELT)
    d = ImageDraw.Draw(img)

    cx = cy = size / 2
    ball_r = size * 0.355
    seam_w = max(3, size // 170)

    ring_r = size * 0.46
    d.ellipse([cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
              outline=ring_outer, width=int(size * 0.022))
    inner = ring_r - size * 0.018
    d.ellipse([cx - inner, cy - inner, cx + inner, cy + inner],
              outline=ring_inner, width=max(2, size // 400))

    def proj(p):
        return (cx + p[0] * ball_r, cy - p[1] * ball_r)

    d.ellipse([cx - ball_r, cy - ball_r, cx + ball_r, cy + ball_r], fill=SEAM)

    front = [f for f in faces if V[f].mean(axis=0)[2] > -0.05]
    front.sort(key=lambda f: V[f].mean(axis=0)[2])

    for f in front:
        pts = [proj(V[i]) for i in f]
        if len(f) == 6:
            d.polygon(pts, fill=CREAM, outline=SEAM)
        else:
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            mask = Image.new("L", (size, size), 0)
            ImageDraw.Draw(mask).polygon(pts, fill=255)
            tile = Image.new("RGB", (size, size), CREAM)
            painter(ImageDraw.Draw(tile), min(xs), min(ys), max(xs), max(ys))
            img.paste(tile, (0, 0), mask)
        d.line(pts + [pts[0]], fill=SEAM, width=seam_w, joint="curve")

    img.save(out_path, format="PNG", dpi=(300, 300))
    pent_front = sum(1 for f in front if len(f) == 5)
    hexa_front = sum(1 for f in front if len(f) == 6)
    print(f"{out_path} : {size}x{size}, faces visibles = {pent_front} pentagones + {hexa_front} hexagones")


if __name__ == "__main__":
    country = sys.argv[1]
    out = sys.argv[2]
    size = int(sys.argv[4]) if len(sys.argv) > 4 and sys.argv[3] == "--size" else 2048
    render(country, out, size)
