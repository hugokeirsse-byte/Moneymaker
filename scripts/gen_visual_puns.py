#!/usr/bin/env python3
"""
gen_visual_puns.py — blagues visuelles minimalistes « forme mal étiquetée ».

Une belle forme géométrique + dessous un mot qui désigne une AUTRE forme.
Déadpan, ultra propre. Ex. un rond avec écrit « CARRÉ ».

Deux variantes maillot (encre sombre / claire), fond transparent, 4500 px.

Usage :
    python scripts/gen_visual_puns.py --out produits/visual_puns
    python scripts/gen_visual_puns.py --sheet /tmp/puns.png
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402
from typo_variants import VARIANTS, adapt  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

INK = (28, 28, 32, 255)

# id, forme, label FR, label EN
PUNS = [
    ("rond_carre", "circle", "CARRÉ", "SQUARE"),
    ("carre_rond", "square", "ROND", "CIRCLE"),
    ("triangle_cercle", "triangle", "CERCLE", "CIRCLE"),
    ("coeur_cube", "heart", "CUBE", "CUBE"),
    ("etoile_ligne", "star", "LIGNE", "LINE"),
]


def draw_shape(d, shape, cx, cy, r, fill):
    if shape == "circle":
        d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=fill)
    elif shape == "square":
        d.rectangle([cx - r, cy - r, cx + r, cy + r], fill=fill)
    elif shape == "triangle":
        h = r * 1.732
        d.polygon([(cx, cy - r), (cx - r * 0.95, cy + h / 2),
                   (cx + r * 0.95, cy + h / 2)], fill=fill)
    elif shape == "heart":
        pts = []
        for i in range(0, 361, 4):
            t = math.radians(i)
            x = 16 * math.sin(t) ** 3
            y = (13 * math.cos(t) - 5 * math.cos(2 * t)
                 - 2 * math.cos(3 * t) - math.cos(4 * t))
            pts.append((cx + x * r / 16, cy - y * r / 15))
        d.polygon(pts, fill=fill)
    elif shape == "star":
        pts = []
        for i in range(10):
            rr = r if i % 2 == 0 else r * 0.42
            a = math.pi / 2 + i * math.pi / 5
            pts.append((cx + rr * math.cos(a), cy - rr * math.sin(a)))
        d.polygon(pts, fill=fill)


def measure(font, text):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box[1]


def render(shape, label, variant, side=4500):
    ink = adapt(INK, variant)
    margin = int(side * 0.16)
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)

    r = int(side * 0.26)
    cx = side // 2
    cy = int(side * 0.40)
    draw_shape(d, shape, cx, cy, r, ink)

    # label dessous, gros et propre
    max_w = side - 2 * margin
    lo, hi = 40, 900
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if measure(load_font("script", mid), label)[0] <= max_w:
            lo = mid
        else:
            hi = mid - 1
    f = load_font("script", lo)
    lw, lh, loff = measure(f, label)
    d.text(((side - lw) // 2, int(side * 0.74) - loff), label, font=f, fill=ink)

    bbox = canvas.getbbox()
    canvas = canvas.crop(bbox)
    pad = int(side * 0.08)
    out = Image.new("RGBA", (canvas.width + 2 * pad, canvas.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(canvas, (pad, pad))
    if max(out.size) != side:
        k = side / max(out.size)
        out = out.resize((round(out.width * k), round(out.height * k)), Image.LANCZOS)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="produits/visual_puns")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--variant", default="both", choices=["both", "dark", "light"])
    args = ap.parse_args()

    sel = set(args.only.split(",")) if args.only else None
    items = [p for p in PUNS if not sel or p[0] in sel]

    if args.sheet:
        cols = 5
        cell = 460
        sheet = Image.new("RGB", (cols * cell, ((len(items) * 2 + cols - 1) // cols) * cell),
                          (244, 244, 246))
        i = 0
        for pid, shape, fr, en in items:
            for lab in (fr, en):
                im = render(shape, lab, "dark", side=1200)
                im.thumbnail((cell - 40, cell - 40))
                bg = Image.new("RGB", im.size, (255, 255, 255))
                bg.paste(im.convert("RGB"), mask=im.split()[-1])
                r, c = divmod(i, cols)
                sheet.paste(bg, (c * cell + 20, r * cell + 20))
                i += 1
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=90)
        print(f"planche: {args.sheet}")
        return

    variants = list(VARIANTS) if args.variant == "both" else [args.variant]
    os.makedirs(args.out, exist_ok=True)
    n = 0
    for pid, shape, fr, en in items:
        for lab, lg in ((fr, "fr"), (en, "en")):
            for v in variants:
                im = render(shape, lab, v)
                im.save(os.path.join(args.out, f"{pid}__{lg}__{v}.png"), dpi=(300, 300))
                n += 1
    print(f"{n} fichiers → {args.out}")


if __name__ == "__main__":
    main()
