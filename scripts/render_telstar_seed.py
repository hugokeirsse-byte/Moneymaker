#!/usr/bin/env python3
"""
render_telstar_seed.py — dessine un ballon Telstar mathématiquement exact
(icosaèdre tronqué : 12 pentagones + 20 hexagones) en projection orthographique,
pentagones remplis du drapeau du pays, hexagones crème, sur feutre sombre avec
anneau doré. Sert d'image de départ (img2img) pour FLUX.2 : la géométrie est
garantie par le code, le modèle n'ajoute que le rendu broderie.

Usage: python scripts/render_telstar_seed.py <country_id> <out.png> [--size 2048]
Les couleurs de drapeau par pays sont définies dans FLAGS (bandes verticales
ou motifs simples). Extensible pays par pays.
"""
import sys
import itertools
import numpy as np
from PIL import Image, ImageDraw
from scipy.spatial import ConvexHull

PHI = (1 + 5 ** 0.5) / 2

# drapeaux simplifiés : liste de bandes verticales (gauche→droite) par défaut
FLAGS = {
    "france": {"bands": [(0, 85, 164), (255, 255, 255), (239, 65, 53)]},
    # à étendre pays par pays une fois le gabarit France validé
}

FELT = (38, 36, 40)
CREAM = (244, 240, 228)
SEAM = (18, 18, 24)
GOLD = (212, 175, 55)
NAVY = (16, 24, 64)


def truncated_icosahedron():
    """Sommets + faces (listes d'indices) d'un icosaèdre tronqué unitaire."""
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
    # regroupe les triangles coplanaires en faces (pentagones/hexagones)
    groups = {}
    for simplex, eq in zip(hull.simplices, hull.equations):
        key = tuple(np.round(eq, 5))
        groups.setdefault(key, set()).update(simplex)
    faces = []
    for key, idx in groups.items():
        idx = list(idx)
        normal = np.array(key[:3])
        center = V[idx].mean(axis=0)
        # ordonne les sommets autour du centre de la face
        ref = V[idx[0]] - center
        ref -= normal * ref.dot(normal)
        ref /= np.linalg.norm(ref)
        ortho = np.cross(normal, ref)
        ang = [np.arctan2((V[i] - center).dot(ortho), (V[i] - center).dot(ref)) for i in idx]
        faces.append([i for _, i in sorted(zip(ang, idx))])
    return V, faces


def rotation_to_z(v):
    """Matrice qui amène le vecteur v sur +z."""
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
    flag = FLAGS[country]
    V, faces = truncated_icosahedron()

    # oriente un pentagone exactement face caméra
    pent = next(f for f in faces if len(f) == 5)
    R = rotation_to_z(V[pent].mean(axis=0))
    V = V @ R.T
    # redresse le pentagone central : axe de symétrie vertical, pointe en haut
    center = V[pent].mean(axis=0)
    a0 = np.arctan2(V[pent[0]][1] - center[1], V[pent[0]][0] - center[0])
    step = 2 * np.pi / 5
    delta = (np.pi / 2 - a0) % step
    if delta > step / 2:
        delta -= step
    c, s = np.cos(delta), np.sin(delta)
    Rz = np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])
    V = V @ Rz.T

    img = Image.new("RGB", (size, size), FELT)
    d = ImageDraw.Draw(img)

    cx = cy = size / 2
    ball_r = size * 0.355
    seam_w = max(3, size // 170)

    # anneau doré (le liseré cordelette sera détaillé par FLUX)
    ring_r = size * 0.46
    d.ellipse([cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r],
              outline=GOLD, width=int(size * 0.022))
    inner = ring_r - size * 0.018
    d.ellipse([cx - inner, cy - inner, cx + inner, cy + inner],
              outline=NAVY, width=max(2, size // 400))

    def proj(p):
        return (cx + p[0] * ball_r, cy - p[1] * ball_r)

    # disque de fond du ballon (zones de silhouette entre les panneaux du bord)
    d.ellipse([cx - ball_r, cy - ball_r, cx + ball_r, cy + ball_r], fill=SEAM)

    front = [f for f in faces if V[f].mean(axis=0)[2] > -0.05]
    front.sort(key=lambda f: V[f].mean(axis=0)[2])

    for f in front:
        pts = [proj(V[i]) for i in f]
        if len(f) == 6:
            d.polygon(pts, fill=CREAM, outline=SEAM)
        else:
            # pentagone → drapeau en bandes verticales, clip au polygone
            xs = [p[0] for p in pts]
            ys = [p[1] for p in pts]
            x0, x1 = min(xs), max(xs)
            y0, y1 = min(ys), max(ys)
            mask = Image.new("L", (size, size), 0)
            ImageDraw.Draw(mask).polygon(pts, fill=255)
            tile = Image.new("RGB", (size, size), CREAM)
            td = ImageDraw.Draw(tile)
            bands = flag["bands"]
            bw = (x1 - x0) / len(bands)
            for k, col in enumerate(bands):
                td.rectangle([x0 + k * bw, y0, x0 + (k + 1) * bw, y1], fill=col)
            img.paste(tile, (0, 0), mask)
        # coutures épaisses par-dessus
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
