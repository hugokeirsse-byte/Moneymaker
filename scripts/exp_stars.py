#!/usr/bin/env python3
"""
exp_stars.py — planche d'essai : un même modèle typo avec plusieurs traitements
d'étoiles (sparkles) pour choisir la déclinaison couleur.

Modes :
  noir_rouge   : étoiles rouges + quelques noires (actuel)
  rouge        : toutes rouges
  noir         : toutes noires
  multi_each   : chaque étoile d'une couleur différente (palette vive)
  multi_chaud  : idem, palette chaude (or/orange/rouge/rose)
  pastel       : idem, palette pastel
  dore         : toutes dorées
  multi_within : chaque étoile elle-même multicolore (branches arc-en-ciel)

Usage :
    python scripts/exp_stars.py --sheet /tmp/stars.png
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

# modèle d'essai (markup *mot* = rouge)
PHRASE = ["Reste", "*Sauvage*"]

VIVE = [(214, 40, 40), (0, 119, 182), (56, 176, 0), (255, 183, 3),
        (123, 44, 191), (251, 86, 7), (255, 0, 110), (2, 195, 154)]
CHAUD = [(214, 40, 40), (247, 127, 0), (252, 191, 73), (255, 0, 110),
         (233, 79, 55), (255, 158, 0)]
PASTEL = [(247, 154, 154), (160, 196, 255), (181, 234, 215), (255, 223, 168),
          (214, 188, 250), (255, 200, 221)]
DORE = (212, 160, 23)


def star_pts(cx, cy, r):
    pts = []
    for k in range(16):
        ang = math.pi / 8 * k - math.pi / 2
        rr = r if k % 2 == 0 else r * 0.40
        pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
    return pts


def draw_star(d, cx, cy, r, color):
    d.polygon(star_pts(cx, cy, r), fill=color)


def draw_star_multi(d, cx, cy, r, colors):
    """Étoile dont chaque branche a une couleur différente."""
    pts = star_pts(cx, cy, r)
    for k in range(8):
        outer = pts[2 * k]
        inprev = pts[(2 * k - 1) % 16]
        innext = pts[(2 * k + 1) % 16]
        d.polygon([(cx, cy), inprev, outer, innext], fill=colors[k % len(colors)])


def spots_for(x0, y0, x1, y1, scale):
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    big = int(95 * scale)
    mid = int(64 * scale)
    sm = int(46 * scale)
    xs = int(30 * scale)
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
        (cx - int(180 * scale), y0 - int(72 * scale), int(34 * scale)),
        (cx + int(180 * scale), y1 + int(72 * scale), int(34 * scale)),
        (x0 - int(o * 1.05), cy - int(o * 0.35), xs),
        (x1 + int(o * 1.05), cy + int(o * 0.45), xs),
    ]


def sparkle(d, bbox, scale, mode):
    spots = spots_for(*bbox, scale)
    for i, (x, y, r) in enumerate(spots):
        if mode == "noir_rouge":
            draw_star(d, x, y, r, RED if i < 10 else INK)
        elif mode == "rouge":
            draw_star(d, x, y, r, RED)
        elif mode == "noir":
            draw_star(d, x, y, r, INK)
        elif mode == "dore":
            draw_star(d, x, y, r, DORE)
        elif mode == "multi_each":
            draw_star(d, x, y, r, VIVE[i % len(VIVE)])
        elif mode == "multi_chaud":
            draw_star(d, x, y, r, CHAUD[i % len(CHAUD)])
        elif mode == "pastel":
            draw_star(d, x, y, r, PASTEL[i % len(PASTEL)])
        elif mode == "multi_within":
            draw_star_multi(d, x, y, r, VIVE)


def parse(line):
    parts = line.split("*")
    return [(s, i % 2 == 1) for i, s in enumerate(parts) if s != ""]


def render(mode, side=1300):
    tokens = [parse(l) for l in PHRASE]
    margin = int(side * 0.20)
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
    d = ImageDraw.Draw(img)
    cx = side // 2
    top = side // 2 - th // 2
    widths = [sum(f.getlength(t) for t, _ in tl) for tl in tokens]
    bw = max(widths)
    bbox = (cx - bw // 2, top, cx + bw // 2, top + th)
    sparkle(d, bbox, side / 4500.0, mode)
    y = top
    for tl, w in zip(tokens, widths):
        x = cx - w / 2
        for seg, acc in tl:
            d.text((x, y - off), seg, font=f, fill=RED if acc else INK)
            x += f.getlength(seg)
        y += lh + gap
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sheet", default="/tmp/stars.png")
    args = ap.parse_args()
    modes = ["noir_rouge", "rouge", "noir", "dore",
             "multi_each", "multi_chaud", "pastel", "multi_within"]
    cols = 4
    cell = 460
    rows = (len(modes) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * cell), (250, 250, 252))
    dd = ImageDraw.Draw(sheet)
    try:
        lab = load_font("fjalla", 22)
    except Exception:
        lab = ImageFont.load_default()
    for i, m in enumerate(modes):
        im = render(m)
        im.thumbnail((cell - 30, cell - 70))
        bg = Image.new("RGB", im.size, (255, 255, 255))
        bg.paste(im.convert("RGB"), mask=im.split()[-1])
        r, c = divmod(i, cols)
        sheet.paste(bg, (c * cell + 15, r * cell + 15))
        dd.text((c * cell + 18, r * cell + cell - 40), m, fill=(40, 40, 40), font=lab)
    os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
    sheet.save(args.sheet, quality=90)
    print(f"planche: {args.sheet} ({len(modes)} modes)")


if __name__ == "__main__":
    main()
