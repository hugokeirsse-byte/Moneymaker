#!/usr/bin/env python3
"""
gen_symbol_mosaic.py — un GRAND symbole composé de PLEIN de petits identiques.

Ex. : un grand signe peace formé de centaines de petits peace ; un grand symbole
anarchie fait de petits symboles anarchie. Aucune IA, aucun coût : tout est
dessiné vectoriellement avec Pillow, donc 0 dépendance externe et 0 souci de
licence (formes géométriques universelles, non déposables).

Principe : la GRANDE forme (silhouette épaisse de l'emblème) sert de masque ;
on y estampille des petites copies du MÊME emblème sur une grille, uniquement
là où le masque est plein. Couleurs : rainbow (arc-en-ciel), black, ou palette.
Fond transparent, haute résolution.

Symboles intégrés : peace, anarchy, heart, recycle, female (vénus), male (mars).

Exemples (depuis la racine du repo) :
    python scripts/gen_symbol_mosaic.py --symbol peace --colors rainbow \
        --out produits/symbol_mosaics --sheet /tmp/peace.png
    python scripts/gen_symbol_mosaic.py --symbol anarchy --colors black \
        --tile 70 --out produits/symbol_mosaics
"""
import argparse
import colorsys
import math
import os
import sys

from PIL import Image, ImageDraw

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
    # barre transversale du A qui déborde du cercle (signe anarchiste)
    d.line([cx - r * 1.15, cy + r * 0.18, cx + r * 1.15, cy + r * 0.18],
           fill=color, width=w)


def draw_heart(d, box, color, w):
    x0, y0, x1, y1 = box
    sx, sy = (x1 - x0), (y1 - y0)
    pts = []
    for t in [i / 100 * 2 * math.pi for i in range(101)]:
        hx = 16 * math.sin(t) ** 3
        hy = (13 * math.cos(t) - 5 * math.cos(2 * t)
              - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((x0 + sx * (0.5 + hx / 36.0), y0 + sy * (0.46 - hy / 36.0)))
    d.polygon(pts, fill=color)


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
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = (x1 - x0) / 2.6
    d.ellipse([x0 + w, y1 - 2 * r - w, x0 + 2 * r + w, y1 - w], outline=color, width=w)
    arrow_o = (x0 + 2 * r, y1 - 2 * r)
    tip = (x1 - w, y0 + w)
    d.line([arrow_o, tip], fill=color, width=w)
    d.line([tip[0] - r * 0.9, tip[1], tip[0], tip[1]], fill=color, width=w)
    d.line([tip[0], tip[1], tip[0], tip[1] + r * 0.9], fill=color, width=w)


SYMBOLS = {
    "peace": draw_peace, "anarchy": draw_anarchy, "heart": draw_heart,
    "recycle": draw_recycle, "female": draw_venus, "male": draw_mars,
}


# ----------------------------------------------------------- couleurs
PALETTES = {
    "sunset": [(255, 94, 58), (255, 149, 5), (255, 191, 0), (214, 40, 100)],
    "ocean":  [(0, 119, 182), (0, 180, 216), (72, 202, 228), (2, 62, 138)],
    "forest": [(45, 106, 79), (82, 183, 136), (27, 67, 50), (149, 213, 178)],
    "candy":  [(247, 37, 133), (114, 9, 183), (58, 12, 163), (76, 201, 240)],
}


def color_for(mode, frac, idx):
    if mode == "black":
        return (20, 20, 20, 255)
    if mode in PALETTES:
        pal = PALETTES[mode]
        return pal[idx % len(pal)] + (255,)
    hue = 0.83 * frac  # rainbow horizontal, rouge -> violet
    r, g, b = colorsys.hsv_to_rgb(hue, 0.88, 0.97)
    return (int(r * 255), int(g * 255), int(b * 255), 255)


# ----------------------------------------------------------- composition
def make_tile(symbol, tile, color):
    """Petit emblème net (rendu à SSx puis réduit)."""
    big = tile * SS
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = max(SS, round(big * 0.10))
    SYMBOLS[symbol](d, (w, w, big - w, big - w), color, w)
    return img.resize((tile, tile), Image.LANCZOS)


def build(symbol, canvas=1700, tile=48, colors="rainbow", jitter=0.12,
          stroke_frac=0.06):
    # masque : grande silhouette du même emblème. Trait assez fin pour que la
    # STRUCTURE de l'emblème reste lisible (les vides entre branches), assez
    # large pour accueillir une ou deux tuiles.
    mbig = canvas * 2
    mask_img = Image.new("L", (mbig, mbig), 0)
    md = ImageDraw.Draw(mask_img)
    pad = int(mbig * 0.06)
    SYMBOLS[symbol](md, (pad, pad, mbig - pad, mbig - pad), 255,
                    max(2, round(mbig * stroke_frac)))
    mask = mask_img.resize((canvas, canvas), Image.LANCZOS).load()

    out = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    step = int(tile * 0.92)
    idx = 0
    import random
    random.seed(7)
    for gy in range(step // 2, canvas, step):
        for gx in range(step // 2, canvas, step):
            if mask[min(gx, canvas - 1), min(gy, canvas - 1)] < 110:
                continue
            color = color_for(colors, gx / canvas, idx)
            t = make_tile(symbol, tile, color)
            jx = int((random.random() - 0.5) * tile * jitter)
            jy = int((random.random() - 0.5) * tile * jitter)
            out.alpha_composite(t, (gx - tile // 2 + jx, gy - tile // 2 + jy))
            idx += 1
    return out, idx


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="peace", choices=list(SYMBOLS))
    ap.add_argument("--colors", default="rainbow")
    ap.add_argument("--tile", type=int, default=48, help="taille des petits symboles (px)")
    ap.add_argument("--stroke", type=float, default=0.06,
                    help="épaisseur du grand emblème (fraction); plus petit = plus lisible")
    ap.add_argument("--out", default="produits/symbol_mosaics")
    ap.add_argument("--name", default="")
    ap.add_argument("--sheet", default="")
    args = ap.parse_args()

    img, n = build(args.symbol, tile=args.tile, colors=args.colors,
                   stroke_frac=args.stroke)
    name = args.name or f"{args.symbol}_{args.colors}_mosaic"
    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, f"{name}.png")
    img.save(out_path, dpi=(300, 300))
    print(f"{out_path}  ({img.width}x{img.height}, {n} petits {args.symbol})")

    if args.sheet:
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        bg = Image.new("RGB", img.size, (240, 240, 240))
        bg.paste(img, (0, 0), img)
        bg.save(args.sheet, quality=90)
        print("aperçu:", args.sheet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
