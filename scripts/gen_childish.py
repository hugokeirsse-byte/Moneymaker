#!/usr/bin/env python3
"""
gen_childish.py — comptines / vannes de cour de récré, en gros lettrage marqueur.

Designs au ton enfantin. La vedette : « T'as les boules, t'as les glandes,
t'as les gougouttes qui pendent ! » avec deux gouttes dessinées qui pendouillent.

Deux variantes maillot, fond transparent, 4500 px.

Usage :
    python scripts/gen_childish.py --out produits/childish
    python scripts/gen_childish.py --sheet /tmp/childish.png
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402
from typo_variants import VARIANTS, adapt  # noqa: E402

from PIL import Image, ImageDraw  # noqa: E402

INK = (32, 30, 30, 255)
DROP = (70, 150, 210, 255)   # goutte bleue

# id, lignes, drops(bool)
DESIGNS = [
    ("gougouttes_fr", ["T'AS LES BOULES", "T'AS LES GLANDES", "ET LES GOUGOUTTES",
                       "QUI PENDENT !"], True),
    ("dangly_drips_en", ["YOU'VE GOT THE GIGGLES", "THE WIGGLES", "AND TWO LIL' DRIPS",
                         "THAT DANGLE!"], True),
    ("celui_qui_dit_fr", ["CELUI QUI DIT", "C'EST CELUI", "QUI EST !"], False),
    ("first_one_to_laugh_en", ["FIRST ONE TO LAUGH", "IS A ROTTEN EGG"], False),
]


def measure(font, text):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box[1]


def fit_size(lines, key, max_w, hi=520, lo=20):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load_font(key, mid)
        if max(measure(f, t)[0] for t in lines) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


def draw_drop(d, cx, top, h, color):
    """Goutte qui pend : pointe en haut, bulbe en bas."""
    w = h * 0.62
    d.polygon([(cx, top), (cx - w * 0.28, top + h * 0.45),
               (cx + w * 0.28, top + h * 0.45)], fill=color)
    d.ellipse([cx - w / 2, top + h * 0.30, cx + w / 2, top + h], fill=color)
    # reflet
    d.ellipse([cx - w * 0.18, top + h * 0.50, cx - w * 0.02, top + h * 0.70],
              fill=(255, 255, 255, 180))


def render(lines, drops, variant, side=4500):
    ink = adapt(INK, variant)
    drop_col = adapt(DROP, variant)
    margin = int(side * 0.10)
    max_w = side - 2 * margin
    sz = fit_size(lines, "marker", max_w)
    f = load_font("marker", sz)
    gap = int(sz * 0.10)

    dims = [measure(f, t) for t in lines]
    text_h = sum(dd[1] for dd in dims) + gap * (len(lines) - 1)
    drop_h = int(sz * 1.1) if drops else 0
    img = Image.new("RGBA", (side, text_h + drop_h + 2 * margin), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    y = margin
    for t, (w, h, off) in zip(lines, dims):
        d.text(((side - w) // 2, y - off), t, font=f, fill=ink)
        y += h + gap

    if drops:
        y += int(sz * 0.1)
        for dx in (-int(sz * 0.55), int(sz * 0.55)):
            draw_drop(d, side // 2 + dx, y, drop_h, drop_col)

    bbox = img.getbbox()
    img = img.crop(bbox)
    pad = int(side * 0.08)
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(img, (pad, pad))
    if max(out.size) != side:
        k = side / max(out.size)
        out = out.resize((round(out.width * k), round(out.height * k)), Image.LANCZOS)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="produits/childish")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--variant", default="both", choices=["both", "dark", "light"])
    args = ap.parse_args()

    sel = set(args.only.split(",")) if args.only else None
    items = [x for x in DESIGNS if not sel or x[0] in sel]

    if args.sheet:
        cols = 2
        cell = 720
        rows = (len(items) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, rows * cell), (244, 244, 246))
        for i, (pid, lines, drops) in enumerate(items):
            im = render(lines, drops, "dark", side=1400)
            im.thumbnail((cell - 40, cell - 40))
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 20, r * cell + 20))
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=90)
        print(f"planche: {args.sheet}")
        return

    variants = list(VARIANTS) if args.variant == "both" else [args.variant]
    os.makedirs(args.out, exist_ok=True)
    n = 0
    for pid, lines, drops in items:
        for v in variants:
            im = render(lines, drops, v)
            im.save(os.path.join(args.out, f"{pid}__{v}.png"), dpi=(300, 300))
            n += 1
    print(f"{n} fichiers → {args.out}")


if __name__ == "__main__":
    main()
