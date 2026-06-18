#!/usr/bin/env python3
"""
gen_symbol_mosaic.py — mosaïque TONALE : un grand symbole (et un mot dessous)
rendus par une nuée de petits symboles qui se chevauchent, avec un effet de
VOLUME. Aucune IA, aucun coût : tout est dessiné avec Pillow.

Principe (amoncellement, pas une grille !) :
  1) silhouette pleine du symbole (+ mot dessous) = zone à remplir ;
  2) on EMPILE des milliers de petits symboles qui se CHEVAUCHENT : une couche
     de couverture (jitterée, pas < taille => aucun trou de fond) puis une
     couche organique de gros ET petits par-dessus. Aucun espace blanc hormis
     l'intérieur des symboles eux-mêmes ;
  3) un ombrage volumétrique (dôme éclairé en haut-gauche) module la luminosité
     des symboles => l'objet prend du VOLUME (côté clair / côté ombre).

Le mot du bas (ex. « LOVE » sous le cœur) est lui aussi rempli des mêmes petits
symboles.

Symboles : peace, anarchy, heart, recycle, female, male, infinity, star.

Exemples :
    python scripts/gen_symbol_mosaic.py --symbol heart --label LOVE \
        --colors candy --font-path assets/fonts/Anton.ttf \
        --out produits/symbol_mosaics --sheet /tmp/heart.png
    python scripts/gen_symbol_mosaic.py --symbol peace --label PEACE \
        --colors tropical --out produits/symbol_mosaics
"""
import argparse
import colorsys
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SS = 3  # suréchantillonnage des petites tuiles (anti-crénelage)


# ----------------------------------------------------------- dessin emblèmes
def draw_peace(d, box, color, w):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = (x1 - x0) / 2 - w
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=w)
    d.line([cx, cy - r, cx, cy + r], fill=color, width=w)
    dx = r * math.cos(math.radians(45))
    d.line([cx, cy, cx - dx, cy + dx], fill=color, width=w)
    d.line([cx, cy, cx + dx, cy + dx], fill=color, width=w)


def draw_anarchy(d, box, color, w):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = (x1 - x0) / 2 - w
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=w)
    top = (cx, cy - r * 0.78)
    bl = (cx - r * 0.62, cy + r * 0.72)
    br = (cx + r * 0.62, cy + r * 0.72)
    d.line([top, bl], fill=color, width=w)
    d.line([top, br], fill=color, width=w)
    d.line([cx - r * 1.15, cy + r * 0.18, cx + r * 1.15, cy + r * 0.18],
           fill=color, width=w)


def _heart_pts(box):
    x0, y0, x1, y1 = box
    sx, sy = (x1 - x0), (y1 - y0)
    pts = []
    for t in [i / 120 * 2 * math.pi for i in range(121)]:
        hx = 16 * math.sin(t) ** 3
        hy = (13 * math.cos(t) - 5 * math.cos(2 * t)
              - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((x0 + sx * (0.5 + hx / 36.0), y0 + sy * (0.46 - hy / 36.0)))
    return pts


def draw_heart(d, box, color, w):
    d.polygon(_heart_pts(box), fill=color)


def draw_recycle(d, box, color, w):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = (x1 - x0) / 2 - w
    for k in range(3):
        a = math.radians(90 + k * 120)
        a2 = math.radians(90 + k * 120 + 80)
        p1 = (cx + r * math.cos(a), cy - r * math.sin(a))
        p2 = (cx + r * math.cos(a2), cy - r * math.sin(a2))
        d.line([p1, p2], fill=color, width=w)
        d.line([p2, (cx + r * 0.45 * math.cos(a2), cy - r * 0.45 * math.sin(a2))],
               fill=color, width=w)


def draw_venus(d, box, color, w):
    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2
    r = (x1 - x0) / 2 - w
    top = y0 + w
    d.ellipse([cx - r * 0.6, top, cx + r * 0.6, top + r * 1.2], outline=color, width=w)
    cy = top + r * 1.2
    d.line([cx, cy, cx, y1 - w], fill=color, width=w)
    d.line([cx - r * 0.4, (cy + y1) / 2, cx + r * 0.4, (cy + y1) / 2], fill=color, width=w)


def draw_mars(d, box, color, w):
    x0, y0, x1, y1 = box
    r = (x1 - x0) / 2.6
    d.ellipse([x0 + w, y1 - 2 * r - w, x0 + 2 * r + w, y1 - w], outline=color, width=w)
    arrow_o = (x0 + 2 * r, y1 - 2 * r)
    tip = (x1 - w, y0 + w)
    d.line([arrow_o, tip], fill=color, width=w)
    d.line([tip[0] - r * 0.9, tip[1], tip[0], tip[1]], fill=color, width=w)
    d.line([tip[0], tip[1], tip[0], tip[1] + r * 0.9], fill=color, width=w)


def draw_infinity(d, box, color, w):
    x0, y0, x1, y1 = box
    cy = (y0 + y1) / 2
    r = (y1 - y0) / 2 - w
    d.ellipse([x0 + w, cy - r, x0 + w + 2 * r, cy + r], outline=color, width=w)
    d.ellipse([x1 - w - 2 * r, cy - r, x1 - w, cy + r], outline=color, width=w)


def draw_star(d, box, color, w):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    R = (x1 - x0) / 2 - w
    pts = []
    for i in range(10):
        rad = R if i % 2 == 0 else R * 0.42
        a = math.pi / 2 + i * math.pi / 5
        pts.append((cx + rad * math.cos(a), cy - rad * math.sin(a)))
    d.polygon(pts, fill=color)


SYMBOLS = {
    "peace": draw_peace, "anarchy": draw_anarchy, "heart": draw_heart,
    "recycle": draw_recycle, "female": draw_venus, "male": draw_mars,
    "infinity": draw_infinity, "star": draw_star,
}
# fraction du trait quand on dessine la SILHOUETTE pleine (carte de couverture)
SOLID = {"heart", "star"}


# ----------------------------------------------------------- couleurs
# Chaque palette = ~5 couleurs qui se MARIENT, piochées au hasard et mêlées
# PARTOUT (pas de dégradé positionnel). C'est le mélange local de plusieurs
# couleurs distinctes qui rend le design propre (et non « brouillon »).
# Deux familles : multi-teintes harmonieuses, et camaïeux (une teinte, du clair
# au foncé).
PALETTES = {
    # --- multi-couleurs qui se marient ---
    "candy":    [(247, 37, 133), (228, 0, 124), (157, 2, 180),
                 (114, 9, 183), (76, 201, 240)],
    "tropical": [(255, 99, 146), (255, 159, 67), (255, 214, 76),
                 (46, 196, 182), (91, 134, 229)],
    "sunset":   [(255, 221, 89), (255, 158, 44), (255, 94, 58),
                 (232, 49, 86), (176, 35, 90)],
    "ocean":    [(173, 232, 244), (72, 202, 228), (0, 180, 216),
                 (0, 119, 182), (2, 62, 138)],
    "forest":   [(183, 228, 179), (116, 198, 157), (64, 145, 108),
                 (45, 106, 79), (27, 67, 50)],
    "pride":    [(228, 3, 3), (255, 140, 0), (255, 237, 0),
                 (0, 128, 38), (0, 77, 255), (117, 7, 135)],
    # --- camaïeux (du clair au foncé d'une même teinte) ---
    "rose":     [(255, 209, 220), (255, 143, 177), (255, 77, 148),
                 (214, 40, 118), (155, 28, 82)],
    "grape":    [(224, 170, 255), (199, 125, 255), (157, 78, 221),
                 (123, 44, 191), (90, 24, 154)],
    "sky":      [(202, 240, 248), (144, 224, 239), (72, 202, 228),
                 (0, 150, 199), (3, 4, 94)],
    "mint":     [(208, 244, 222), (149, 213, 178), (82, 183, 136),
                 (45, 134, 89), (20, 83, 60)],
}
DEFAULT_PALETTE = "candy"


def stamp_color(palette, shade, rng):
    """Pioche une couleur de la palette (mélange local de plusieurs teintes) ;
    `shade` (0=ombre, 1=lumière) module la luminosité => volume."""
    base = rng.choice(palette)
    f = max(0.34, 0.60 + 0.46 * shade + rng.uniform(-0.06, 0.06))
    return (min(255, int(base[0] * f)), min(255, int(base[1] * f)),
            min(255, int(base[2] * f)), 255)


# ----------------------------------------------------------- carte de couverture
def _load_font(font_path, size):
    for p in (font_path, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if p and os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:  # noqa: BLE001
                pass
    return ImageFont.load_default()


def coverage_map(symbol, W, H, label, font_path, base):
    """Silhouette pleine (symbole + mot), bord légèrement adouci. ~1 dedans.
    Renvoie (couverture, géométrie du symbole) pour calculer l'ombrage."""
    sil = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(sil)
    label = (label or "").strip()
    sym_h = int(H * (0.74 if label else 0.92))
    side = int(min(W, sym_h) * 0.92)
    bx = (W - side) // 2
    by = int(H * 0.03)
    w = max(2, round(side * (0.30 if symbol in SOLID else 0.085)))
    SYMBOLS[symbol]((d), (bx, by, bx + side, by + side), 255, w)

    label_y0 = H
    if label:
        # lettres posées une à une avec interlettrage (sinon ça se soude)
        fsize = int(H * 0.21)
        track = 0.30  # espace entre lettres (plus large => V/E bien distincts)
        chars = list(label.upper())

        def layout(fs):
            fnt = _load_font(font_path, fs)
            widths, total = [], 0.0
            gap = fs * track
            for i, ch in enumerate(chars):
                l, t, r, b = d.textbbox((0, 0), ch, font=fnt)
                widths.append((ch, l, t, r - l))
                total += (r - l) + (gap if i < len(chars) - 1 else 0)
            return fnt, widths, total, gap

        font, widths, total, gap = layout(fsize)
        while total > W * 0.9 and fsize > 24:
            fsize = int(fsize * 0.92)
            font, widths, total, gap = layout(fsize)

        x = (W - total) / 2
        baseline = int(H * 0.80)
        label_y0 = baseline - int(fsize * 0.1)
        for ch, l, t, cw in widths:
            d.text((x - l, baseline - t), ch, fill=255, font=font)
            x += cw + gap

    cov = sil.filter(ImageFilter.GaussianBlur(base * 0.22))
    cov = np.asarray(cov, dtype=np.float32) / 255.0
    geo = (bx + side / 2.0, by + side / 2.0, side / 2.0 * 1.04, label_y0)
    return cov, geo


def shade_map(W, H, geo):
    """Ombrage volumétrique : dôme éclairé en haut-gauche pour le symbole,
    léger dégradé pour la zone du mot. 0 = ombre, 1 = pleine lumière."""
    cx, cy, R, label_y0 = geo
    ys, xs = np.mgrid[0:H, 0:W].astype(np.float32)
    nx = (xs - cx) / R
    ny = (ys - cy) / R
    nz = np.sqrt(np.clip(1.0 - nx * nx - ny * ny, 0.0, 1.0))
    lx, ly, lz = -0.45, -0.55, 0.70
    lam = np.clip(nx * lx + ny * ly + nz * lz, 0.0, 1.0)
    shade = 0.18 + 0.82 * lam
    grad = 0.80 - 0.30 * (xs / W)          # mot : éclairé à gauche
    shade = np.where(ys >= label_y0, grad, shade)
    return shade.astype(np.float32)


# ----------------------------------------------------------- tuiles
def make_tile(symbol, size, color):
    big = max(SS * 6, size * SS)
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = max(SS, round(big * 0.11))
    SYMBOLS[symbol](d, (w, w, big - w, big - w), color, w)
    return img.resize((size, size), Image.LANCZOS)


# ----------------------------------------------------------- composition
def build(symbol, W=1700, H=2000, colors="candy", label="",
          font_path="", base=34, seed=7):
    cov, geo = coverage_map(symbol, W, H, label, font_path, base)
    shade = shade_map(W, H, geo)
    rng = random.Random(seed)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    inside = 0.42
    palette = PALETTES.get(colors, PALETTES[DEFAULT_PALETTE])

    stamps = []   # (size, x, y, color, angle)

    # 1) couche de couverture : grille fine JITTERÉE (pas < taille => recouvre
    #    tout, aucun trou de fond), mais désordonnée donc pas « grille ».
    step = max(6, int(base * 0.46))
    for gy in range(0, H + step, step):
        for gx in range(0, W + step, step):
            x = gx + rng.randint(-step, step)
            y = gy + rng.randint(-step, step)
            if not (0 <= x < W and 0 <= y < H) or cov[y, x] < inside:
                continue
            s = float(shade[y, x])
            size = int(base * rng.uniform(0.9, 1.4) * (1.0 + 0.12 * (1 - s)))
            stamps.append((size, x, y, stamp_color(palette, s, rng),
                           rng.uniform(-16, 16)))

    # 2) couche organique par-dessus : gros ET petits, pour l'amoncellement
    for _ in range(int(len(stamps) * 0.6)):
        x, y = rng.randrange(W), rng.randrange(H)
        if cov[y, x] < inside:
            continue
        s = float(shade[y, x])
        size = int(base * rng.uniform(0.45, 1.95))
        stamps.append((size, x, y, stamp_color(palette, s, rng),
                       rng.uniform(-16, 16)))

    # du plus gros au plus petit => les petits se posent par-dessus (pile)
    stamps.sort(key=lambda a: -a[0])
    for size, x, y, color, ang in stamps:
        if size < 8:
            continue
        t = make_tile(symbol, size, color)
        if abs(ang) > 1:
            t = t.rotate(ang, expand=True, resample=Image.BICUBIC)
        out.alpha_composite(t, (x - t.width // 2, y - t.height // 2))
    return out, len(stamps)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="heart", choices=list(SYMBOLS))
    ap.add_argument("--label", default="", help="mot écrit dessous, en petits symboles")
    ap.add_argument("--colors", default="candy",
                    help="candy|tropical|sunset|ocean|forest|pride|rose|grape|sky|mint")
    ap.add_argument("--base", type=int, default=34, help="taille moyenne des symboles (px)")
    ap.add_argument("--font-path", default="")
    ap.add_argument("--out", default="produits/symbol_mosaics")
    ap.add_argument("--name", default="")
    ap.add_argument("--sheet", default="")
    args = ap.parse_args()

    img, n = build(args.symbol, colors=args.colors, label=args.label,
                   font_path=args.font_path, base=args.base)
    lab = f"_{args.label.lower()}" if args.label else ""
    name = args.name or f"{args.symbol}{lab}_{args.colors}_mosaic"
    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, f"{name}.png")
    img.save(out_path, dpi=(300, 300))
    print(f"{out_path}  ({img.width}x{img.height}, {n} petits {args.symbol})")

    if args.sheet:
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        bg = Image.new("RGB", img.size, (245, 245, 245))
        bg.paste(img, (0, 0), img)
        bg.save(args.sheet, quality=90)
        print("aperçu:", args.sheet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
