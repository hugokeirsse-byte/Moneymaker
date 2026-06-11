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
    """Feuille d'érable du drapeau canadien — silhouette fidèle à 11 pointes,
    lobes pointus et échancrures profondes (demi-contour miroité + tige)."""
    half = [(0.000, -1.000),                       # pointe sommitale
            (0.060, -0.760), (0.260, -0.860),      # échancrure + lobe haut-droit
            (0.190, -0.560), (0.450, -0.700),      # échancrure + lobe droit sup.
            (0.360, -0.350), (0.755, -0.500),      # échancrure + grand lobe droit
            (0.620, -0.180), (1.000, -0.220),      # échancrure + pointe latérale
            (0.860,  0.080), (0.980,  0.180),      # creux + pointe basse latérale
            (0.520,  0.260), (0.560,  0.460),      # échancrure + lobe bas-droit
            (0.200,  0.320)]                       # vers la tige
    stem = [(0.050, 0.360), (0.045, 0.980), (-0.045, 0.980), (-0.050, 0.360)]
    pts = half + stem + [(-x, y) for x, y in reversed(half)]
    td.polygon([(cx + x * s, cy + y * s) for x, y in pts], fill=color)


def flag_canada(td, x0, y0, x1, y1):
    """Bandes rouge / blanc / rouge (1:2:1), feuille d'érable centrée occupant
    ~3/4 de la hauteur du carré blanc (proportions du drapeau officiel)."""
    red, white = (216, 30, 5), (255, 255, 255)
    w = x1 - x0
    td.rectangle([x0, y0, x0 + w / 4, y1], fill=red)
    td.rectangle([x0 + w / 4, y0, x1 - w / 4, y1], fill=white)
    td.rectangle([x1 - w / 4, y0, x1, y1], fill=red)
    _maple_leaf(td, (x0 + x1) / 2, (y0 + y1) / 2, (y1 - y0) * 0.38, red)


def flag_mexico(td, x0, y0, x1, y1):
    """Bandes verticales vert / blanc / rouge + aigle de profil sur cactus,
    serpent au bec, couronne de laurier — silhouette fidèle simplifiée."""
    green, white, red = (0, 104, 71), (255, 255, 255), (206, 17, 38)
    w = (x1 - x0) / 3
    for k, col in enumerate([green, white, red]):
        td.rectangle([x0 + k * w, y0, x0 + (k + 1) * w, y1], fill=col)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    s = (y1 - y0) * 0.20
    brown, dark = (121, 78, 40), (74, 46, 22)
    # corps de l'aigle de profil (tourné vers la gauche), aile relevée
    body = [(cx - 0.55 * s, cy - 0.05 * s), (cx - 0.42 * s, cy - 0.42 * s),  # poitrail→tête
            (cx - 0.62 * s, cy - 0.52 * s), (cx - 0.46 * s, cy - 0.56 * s),  # bec
            (cx - 0.25 * s, cy - 0.62 * s),                                   # crâne
            (cx + 0.10 * s, cy - 0.50 * s), (cx + 0.65 * s, cy - 0.80 * s),  # départ aile
            (cx + 0.95 * s, cy - 0.45 * s), (cx + 0.70 * s, cy - 0.30 * s),  # plumes
            (cx + 0.85 * s, cy - 0.05 * s), (cx + 0.55 * s, cy + 0.05 * s),  # bas d'aile
            (cx + 0.70 * s, cy + 0.35 * s), (cx + 0.30 * s, cy + 0.30 * s),  # queue
            (cx + 0.05 * s, cy + 0.55 * s), (cx - 0.20 * s, cy + 0.45 * s)]  # serres
    td.polygon(body, fill=brown)
    # serpent ondulé tenu au bec
    td.line([(cx - 0.60 * s, cy - 0.50 * s), (cx - 0.85 * s, cy - 0.30 * s),
             (cx - 0.62 * s, cy - 0.15 * s), (cx - 0.88 * s, cy + 0.02 * s)],
            fill=dark, width=max(2, int(s * 0.10)), joint="curve")
    # cactus sous les serres
    td.rectangle([cx - 0.10 * s, cy + 0.50 * s, cx + 0.12 * s, cy + 0.95 * s], fill=green)
    td.ellipse([cx - 0.30 * s, cy + 0.55 * s, cx - 0.06 * s, cy + 0.80 * s], fill=green)
    td.ellipse([cx + 0.08 * s, cy + 0.52 * s, cx + 0.32 * s, cy + 0.77 * s], fill=green)
    # couronne de laurier de part et d'autre
    td.arc([cx - 1.05 * s, cy - 0.10 * s, cx - 0.30 * s, cy + 1.05 * s], 290, 110,
           fill=green, width=max(2, int(s * 0.12)))
    td.arc([cx + 0.30 * s, cy - 0.10 * s, cx + 1.05 * s, cy + 1.05 * s], 70, 250,
           fill=green, width=max(2, int(s * 0.12)))


def flag_brazil(td, x0, y0, x1, y1):
    """Proportions officielles : losange or à 1/12 des bords (presque pleine
    largeur), globe bleu de diamètre ~0.5×hauteur, bande blanche incurvée."""
    green, gold, blue, white = (0, 151, 57), (254, 221, 0), (0, 39, 118), (255, 255, 255)
    td.rectangle([x0, y0, x1, y1], fill=green)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    fw, fh = x1 - x0, y1 - y0
    # losange : marge officielle de 1/12 de la largeur sur chaque bord
    w, h = fw * (0.5 - 1 / 12), fh * (0.5 - 1 / 12)
    td.polygon([(cx, cy - h), (cx + w, cy), (cx, cy + h), (cx - w, cy)], fill=gold)
    # globe : diamètre = 0.5 × hauteur du drapeau
    r = fh * 0.25
    td.ellipse([cx - r, cy - r, cx + r, cy + r], fill=blue)
    # bande blanche incurvée, découpée au globe (jamais hors du cercle)
    band_w = max(3, int(r * 0.20))
    im = td._image
    overlay = Image.new("RGB", im.size, (0, 0, 0))
    od = ImageDraw.Draw(overlay)
    od.arc([cx - 2.6 * r, cy - 0.62 * r, cx + 1.04 * r, cy + 3.2 * r], 285, 357,
           fill=white, width=band_w)
    mask = Image.new("L", im.size, 0)
    md = ImageDraw.Draw(mask)
    md.ellipse([cx - r, cy - r, cx + r, cy + r], fill=255)
    band_mask = overlay.convert("L").point(lambda v: 255 if v > 10 else 0)
    from PIL import ImageChops
    final_mask = ImageChops.multiply(mask, band_mask)
    im.paste(white, (0, 0), final_mask)
    # étoiles : une au-dessus de la bande, le reste en dessous (esprit du vrai)
    _star(td, cx - 0.05 * r, cy - 0.55 * r, r * 0.085, white)
    for dx, dy in [(-0.55, 0.30), (-0.20, 0.52), (0.18, 0.38), (0.50, 0.55),
                   (-0.35, 0.75), (0.05, 0.80)]:
        _star(td, cx + dx * r, cy + dy * r, r * 0.075, white)


FLAGS["england"] = (flag_england, FLAGS["england"][1])
FLAGS["mexico"] = (flag_mexico, FLAGS["mexico"][1])
FLAGS["canada"] = (flag_canada, FLAGS["canada"][1])
FLAGS["germany"] = (flag_germany, FLAGS["germany"][1])
FLAGS["brazil"] = (flag_brazil, FLAGS["brazil"][1])


def flag_argentina(td, x0, y0, x1, y1):
    """Bandes horizontales ciel/blanc/ciel + Soleil de Mai doré au centre
    (disque rayonnant à 16 rayons triangulaires)."""
    sky, white, gold = (108, 172, 228), (255, 255, 255), (244, 180, 38)
    h = (y1 - y0) / 3
    for k, col in enumerate([sky, white, sky]):
        td.rectangle([x0, y0 + k * h, x1, y0 + (k + 1) * h], fill=col)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = (y1 - y0) * 0.115
    for k in range(16):
        a = k * math.pi / 8
        td.polygon([(cx + r * 0.9 * math.cos(a - 0.10), cy + r * 0.9 * math.sin(a - 0.10)),
                    (cx + r * 1.9 * math.cos(a), cy + r * 1.9 * math.sin(a)),
                    (cx + r * 0.9 * math.cos(a + 0.10), cy + r * 0.9 * math.sin(a + 0.10))],
                   fill=gold)
    td.ellipse([cx - r, cy - r, cx + r, cy + r], fill=gold)
    td.ellipse([cx - r * 0.55, cy - r * 0.55, cx + r * 0.55, cy + r * 0.55],
               outline=(180, 120, 20), width=max(2, int(r * 0.16)))


def flag_spain(td, x0, y0, x1, y1):
    """Bandes rouge/or/rouge (1:2:1), petites armoiries simplifiées côté mât."""
    red, gold = (170, 21, 27), (241, 191, 0)
    h = y1 - y0
    td.rectangle([x0, y0, x1, y0 + h / 4], fill=red)
    td.rectangle([x0, y0 + h / 4, x1, y1 - h / 4], fill=gold)
    td.rectangle([x0, y1 - h / 4, x1, y1], fill=red)
    # écu décalé côté mât — GROS et simple pour rester identique d'un
    # pentagone à l'autre au rendu (quartiers rouge/or francs, contour épais)
    ex, ey = x0 + (x1 - x0) * 0.30, (y0 + y1) / 2
    s = h * 0.19
    dark = (90, 45, 15)
    shield = [(ex - s, ey - s), (ex + s, ey - s), (ex + s, ey + s * 0.45),
              (ex, ey + s * 1.05), (ex - s, ey + s * 0.45)]
    td.polygon(shield, fill=(255, 255, 255), outline=dark)
    lw = max(3, int(s * 0.14))
    td.line(shield + [shield[0]], fill=dark, width=lw, joint="curve")
    m = s * 0.16
    td.rectangle([ex - s + m, ey - s + m, ex - m / 2, ey - m / 2], fill=red)
    td.rectangle([ex + m / 2, ey - s + m, ex + s - m, ey - m / 2], fill=(244, 180, 38))
    td.rectangle([ex - s + m, ey + m / 2, ex - m / 2, ey + s * 0.45 - m / 2], fill=(244, 180, 38))
    td.rectangle([ex + m / 2, ey + m / 2, ex + s - m, ey + s * 0.45 - m / 2], fill=red)


def flag_netherlands(td, x0, y0, x1, y1):
    """Bandes horizontales rouge / blanc / bleu cobalt."""
    h = (y1 - y0) / 3
    for k, col in enumerate([(174, 28, 40), (255, 255, 255), (33, 70, 139)]):
        td.rectangle([x0, y0 + k * h, x1, y0 + (k + 1) * h], fill=col)


def flag_portugal(td, x0, y0, x1, y1):
    """Vert (2/5) / rouge (3/5) verticaux, sphère armillaire dorée portant
    l'écu blanc à bordure rouge, centrée sur la frontière des couleurs."""
    green, red, gold = (0, 102, 0), (218, 41, 28), (255, 204, 41)
    w = x1 - x0
    split = x0 + w * 0.4
    td.rectangle([x0, y0, split, y1], fill=green)
    td.rectangle([split, y0, x1, y1], fill=red)
    cy = (y0 + y1) / 2
    r = (y1 - y0) * 0.17
    ring_w = max(2, int(r * 0.22))
    td.ellipse([split - r, cy - r, split + r, cy + r], outline=gold, width=ring_w)
    td.line([(split - r * 0.7, cy - r * 0.7), (split + r * 0.7, cy + r * 0.7)],
            fill=gold, width=max(2, int(ring_w * 0.7)))
    s = r * 0.62
    td.polygon([(split - s * 0.7, cy - s), (split + s * 0.7, cy - s),
                (split + s * 0.7, cy + s * 0.4), (split, cy + s),
                (split - s * 0.7, cy + s * 0.4)],
               fill=(255, 255, 255), outline=(218, 41, 28))


def flag_japan(td, x0, y0, x1, y1):
    """Disque rouge cramoisi centré sur fond blanc pur (diamètre 3/5 hauteur)."""
    td.rectangle([x0, y0, x1, y1], fill=(255, 255, 255))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = (y1 - y0) * 0.30
    td.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(188, 0, 45))


FLAGS["argentina"] = (flag_argentina, ((108, 172, 228), (244, 180, 38)))   # ciel + or
FLAGS["spain"] = (flag_spain, ((170, 21, 27), (241, 191, 0)))              # rouge + or
FLAGS["netherlands"] = (flag_netherlands, ((232, 119, 34), (33, 70, 139))) # orange + navy
FLAGS["portugal"] = (flag_portugal, ((0, 102, 0), (218, 41, 28)))          # vert + rouge
FLAGS["japan"] = (flag_japan, ((188, 0, 45), (255, 255, 255)))             # rouge + blanc


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
