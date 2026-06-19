#!/usr/bin/env python3
"""
gen_trendy.py — mots « à la mode » & cynisme doux (zeitgeist EN).

Le vocabulaire qui tourne : overrated/underrated, overthinking, delulu, unhinged,
« lowering the bar ». Typo moderne épurée (grotesk géométrique) + un accent.
Fond transparent, 4500 px.

Usage :
    python scripts/gen_trendy.py --out produits/trendy
    python scripts/gen_trendy.py --sheet /tmp/trendy.png
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

INK = (28, 28, 32, 255)
SOFT = (122, 124, 130, 255)
ACCENT = (190, 60, 48, 255)
BLUE = (32, 90, 170, 255)

# id, lignes, police, {index_ligne: couleur}, strike(index ligne ou None)
PHRASES = [
    ("overrated", ["OVERRATED"], "block", {0: ACCENT}, 0),
    ("underrated", ["UNDERRATED"], "block", {0: BLUE}, None),
    ("rated_trio", ["OVERRATED", "UNDERRATED", "WONDERRATED"], "geo",
     {2: ACCENT}, None),
    ("everything_overrated", ["EVERYTHING", "IS OVERRATED"], "block", {1: ACCENT}, None),
    ("let_me_overthink", ["LET ME", "OVERTHINK", "THIS"], "geo", {1: ACCENT}, None),
    ("professional_overthinker", ["PROFESSIONAL", "OVERTHINKER"], "block", {1: ACCENT}, None),
    ("overthinking_since_birth", ["OVERTHINKING", "SINCE BIRTH"], "geo", {1: SOFT}, None),
    ("delulu", ["DELULU"], "block", {0: ACCENT}, None),
    ("delulu_solulu", ["DELULU IS", "THE SOLULU"], "geo", {1: ACCENT}, None),
    ("unhinged_but_polite", ["UNHINGED", "BUT POLITE"], "block", {1: SOFT}, None),
    ("chronically_unimpressed", ["CHRONICALLY", "UNIMPRESSED"], "geo", {1: ACCENT}, None),
    ("mildly_disappointed", ["MILDLY", "DISAPPOINTED"], "block", {1: SOFT}, None),
    ("lowering_the_bar", ["LOWERING THE BAR", "SUCCESSFULLY"], "geo", {1: ACCENT}, None),
    ("emotionally_overrated", ["EMOTIONALLY", "OVERRATED"], "block", {1: ACCENT}, None),
    ("iconic_allegedly", ["ICONIC", "(ALLEGEDLY)"], "geo", {1: SOFT}, None),
    ("bare_minimum", ["GIVING", "BARE MINIMUM", "ICONICALLY"], "geo", {1: ACCENT}, None),
]


def measure(font, text):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box[1]


def fit_size(lines, key, max_w, hi=760, lo=20):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load_font(key, mid)
        if max(measure(f, t)[0] for t in lines) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


def render(lines, key, accents, strike, side=4500, margin_ratio=0.12):
    margin = int(side * margin_ratio)
    max_w = side - 2 * margin
    sz = fit_size(lines, key, max_w)
    f = load_font(key, sz)
    gap = int(sz * 0.20)

    dims = [measure(f, t) for t in lines]
    total_h = sum(dd[1] for dd in dims) + gap * (len(lines) - 1)
    img = Image.new("RGBA", (side, total_h + 2 * margin), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)

    y = margin
    for i, (t, (w, h, off)) in enumerate(zip(lines, dims)):
        col = accents.get(i, INK)
        x = (side - w) // 2
        dr.text((x, y - off), t, font=f, fill=col)
        if strike == i:
            ly = y + h // 2
            dr.line([(x, ly), (x + w, ly)], fill=col, width=max(6, sz // 26))
        y += h + gap

    bbox = img.getbbox()
    if bbox is None:
        return img
    img = img.crop(bbox)
    pad = int(side * 0.10)
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(img, (pad, pad))
    if max(out.size) != side:
        r = side / max(out.size)
        out = out.resize((round(out.width * r), round(out.height * r)), Image.LANCZOS)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="produits/trendy")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    sel = set(args.only.split(",")) if args.only else None
    items = [p for p in PHRASES if not sel or p[0] in sel]

    if args.sheet:
        cols = 4
        rows = (len(items) + cols - 1) // cols
        cell = 560
        sheet = Image.new("RGB", (cols * cell, rows * cell), (244, 244, 246))
        dd = ImageDraw.Draw(sheet)
        try:
            lab = load_font("geo", 17)
        except Exception:
            lab = ImageFont.load_default()
        for i, (pid, lines, key, acc, strike) in enumerate(items):
            im = render(lines, key, acc, strike, side=1400)
            im.thumbnail((cell - 40, cell - 54))
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 20, r * cell + 20))
            dd.text((c * cell + 20, r * cell + cell - 30), pid[:28],
                    fill=(70, 70, 70), font=lab)
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=90)
        print(f"planche: {args.sheet} ({len(items)})")
        return

    os.makedirs(args.out, exist_ok=True)
    n = 0
    for pid, lines, key, acc, strike in items:
        im = render(lines, key, acc, strike)
        path = os.path.join(args.out, f"{pid}.png")
        im.save(path, dpi=(300, 300))
        print(f"  {path}")
        n += 1
    print(f"\n{n} fichiers → {args.out}")


if __name__ == "__main__":
    main()
