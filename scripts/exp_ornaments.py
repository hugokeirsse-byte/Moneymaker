#!/usr/bin/env python3
"""
exp_ornaments.py — planche d'essai : variantes de FORME et de COULEUR d'ornements
autour d'un même modèle typo, pour choisir la déclinaison.

Formes :
  spark4  : étoile à 4 branches (sparkle / scintillement) — la hero
  star5   : étoile classique à 5 branches
  star8   : étoile à 8 branches (l'actuelle)
  moon    : croissants de lune + petites étoiles à 4 branches

Couleurs :
  noir_or, or, noir_rouge, rouge, multi (vif)

Usage :
    python scripts/exp_ornaments.py --sheet /tmp/orn.png
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

FONT = "script"
INK = (28, 28, 32, 255)
RED = (190, 46, 38, 255)
GOLD = (201, 162, 39, 255)
GOLD_HI = (230, 196, 92, 255)

PHRASE = ["Reste", "*Sauvage*"]

VIVE = [(214, 40, 40), (0, 119, 182), (56, 176, 0), (255, 183, 3),
        (123, 44, 191), (251, 86, 7), (255, 0, 110), (2, 195, 154)]


def _poly_star(cx, cy, r, points, inner):
    pts = []
    n = points * 2
    for k in range(n):
        ang = math.pi / points * k - math.pi / 2
        rr = r if k % 2 == 0 else r * inner
        pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
    return pts


def draw_spark4(d, cx, cy, r, color):
    d.polygon(_poly_star(cx, cy, r, 4, 0.20), fill=color)


def draw_star5(d, cx, cy, r, color):
    d.polygon(_poly_star(cx, cy, r, 5, 0.42), fill=color)


def draw_star8(d, cx, cy, r, color):
    d.polygon(_poly_star(cx, cy, r, 8, 0.40), fill=color)


def draw_moon(img, cx, cy, r, color):
    layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    dl.ellipse([cx - r, cy - r, cx + r, cy + r], fill=color)
    off = r * 0.62
    dl.ellipse([cx - r + off, cy - r - r * 0.12,
                cx + r + off, cy + r - r * 0.12], fill=(0, 0, 0, 0))
    img.alpha_composite(layer)


def spots_for(x0, y0, x1, y1, scale):
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    big = int(105 * scale)
    mid = int(70 * scale)
    sm = int(50 * scale)
    xs = int(33 * scale)
    o = int(115 * scale)
    return [
        (x0 - o, y0 - int(o * 0.5), big),
        (x1 + o, y0 - int(o * 0.2), mid),
        (x0 - int(o * 0.5), y1 + int(o * 0.7), mid),
        (x1 + int(o * 0.8), y1 + int(o * 0.5), big),
        (cx, y0 - int(135 * scale), mid),
        (cx, y1 + int(135 * scale), sm),
        (x0 - int(o * 0.2), cy + int(o * 0.1), sm),
        (x1 + int(o * 0.4), cy - int(o * 0.2), sm),
        (cx - int(0.30 * (x1 - x0)), y0 - int(o * 0.75), sm),
        (cx + int(0.30 * (x1 - x0)), y1 + int(o * 0.75), sm),
        (x0 - int(o * 0.7), y1 - int(o * 0.4), sm),
        (x1 + int(o * 0.6), y0 + int(o * 0.4), sm),
        (cx - int(180 * scale), y0 - int(72 * scale), xs),
        (cx + int(180 * scale), y1 + int(72 * scale), xs),
        (x0 - int(o * 1.05), cy - int(o * 0.35), xs),
        (x1 + int(o * 1.05), cy + int(o * 0.45), xs),
    ]


def color_at(scheme, i, r, big):
    if scheme == "noir_or":
        return GOLD if i % 4 != 3 else INK
    if scheme == "or":
        return GOLD if r >= big * 0.7 else GOLD_HI
    if scheme == "noir_rouge":
        return RED if i < 10 else INK
    if scheme == "rouge":
        return RED
    if scheme == "multi":
        return VIVE[i % len(VIVE)]
    return RED


def ornament(img, bbox, scale, shape, scheme):
    spots = spots_for(*bbox, scale)
    big = max(r for _, _, r in spots)
    d = ImageDraw.Draw(img)
    for i, (x, y, r) in enumerate(spots):
        col = color_at(scheme, i, r, big)
        if shape == "moon":
            if r >= big * 0.66:
                draw_moon(img, x, y, r, col)
            else:
                draw_spark4(d, x, y, r, col)
        elif shape == "spark4":
            draw_spark4(d, x, y, r, col)
        elif shape == "star5":
            draw_star5(d, x, y, r, col)
        else:
            draw_star8(d, x, y, r, col)


def parse(line):
    parts = line.split("*")
    return [(s, i % 2 == 1) for i, s in enumerate(parts) if s != ""]


def render(shape, scheme, side=1300):
    tokens = [parse(l) for l in PHRASE]
    margin = int(side * 0.22)
    max_w = side - 2 * margin
    lo, hi = 20, int(side * 0.20)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load_font(FONT, mid)
        if max(sum(f.getlength(t) for t, _ in tl) for tl in tokens) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    sz = lo
    f = load_font(FONT, sz)
    asc = f.getbbox("ÀÇgjpqy")
    lh = asc[3] - asc[1]
    off = asc[1]
    gap = int(sz * 0.14)
    th = len(tokens) * lh + gap * (len(tokens) - 1)
    img = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    cx = side // 2
    top = side // 2 - th // 2
    widths = [sum(f.getlength(t) for t, _ in tl) for tl in tokens]
    bw = max(widths)
    bbox = (cx - bw // 2, top, cx + bw // 2, top + th)
    ornament(img, bbox, side / 4500.0, shape, scheme)
    d = ImageDraw.Draw(img)
    y = top
    for tl, w in zip(tokens, widths):
        x = cx - w / 2
        for seg, acc in tl:
            d.text((x, y - off), seg, font=f, fill=RED if acc else INK)
            x += f.getlength(seg)
        y += lh + gap
    return img


VARIANTS = [
    ("spark4", "noir_or"), ("spark4", "or"), ("spark4", "noir_rouge"),
    ("spark4", "multi"), ("spark4", "rouge"),
    ("star5", "noir_or"), ("star5", "or"), ("star5", "multi"),
    ("moon", "noir_or"), ("moon", "or"), ("moon", "multi"),
    ("star8", "noir_or"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default="/tmp/orn.png")
    args = ap.parse_args()
    cols = 4
    cell = 470
    rows = (len(VARIANTS) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * cell), (250, 250, 252))
    dd = ImageDraw.Draw(sheet)
    try:
        lab = load_font("fjalla", 22)
    except Exception:
        lab = ImageFont.load_default()
    for i, (shape, scheme) in enumerate(VARIANTS):
        im = render(shape, scheme)
        im.thumbnail((cell - 30, cell - 70))
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im.convert("RGB"), mask=im.split()[-1])
        r, c = divmod(i, cols)
        sheet.paste(bg, (c * cell + 15, r * cell + 15))
        dd.text((c * cell + 18, r * cell + cell - 42),
                f"{shape} · {scheme}", fill=(40, 40, 40), font=lab)
    os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
    sheet.save(args.sheet, quality=90)
    print(f"planche: {args.sheet} ({len(VARIANTS)} variantes)")


if __name__ == "__main__":
    main()
