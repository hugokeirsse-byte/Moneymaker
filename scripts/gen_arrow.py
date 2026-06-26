#!/usr/bin/env python3
"""
gen_arrow.py — série « flèche » qui désigne le voisin (façon « I'm with stupid »,
version plus drôle / actuelle / engagée).

Phrase Pacifico (mots-clés en rouge) + une grosse flèche pointant vers le côté
(gauche/droite) pour désigner la personne à côté de soi.

Fond transparent, 4500 px, 300 DPI, deux variantes maillot.

Usage :
    python scripts/gen_arrow.py --out produits/arrow
    python scripts/gen_arrow.py --sheet /tmp/arrow.png
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402
from typo_variants import VARIANTS, adapt  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

DATA_PATH = "data/arrow.json"
FONT = "script"
INK = (28, 28, 32, 255)
RED = (190, 46, 38, 255)


def parse_line(line):
    parts = line.split("*")
    return [(s, i % 2 == 1) for i, s in enumerate(parts) if s != ""]


def line_w(f, toks):
    return sum(f.getlength(t) for t, _ in toks)


def fit_size(token_lines, max_w, hi=620, lo=20):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load_font(FONT, mid)
        if max(line_w(f, tl) for tl in token_lines) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


def draw_arrow(d, cx, cy, width, thick, direction, color):
    """Grosse flèche horizontale pointant 'left' ou 'right', centrée en (cx, cy)."""
    half = width / 2
    head = width * 0.34         # longueur de la pointe
    hh = thick * 2.1            # demi-hauteur de la pointe
    s = 1 if direction == "right" else -1
    tip = cx + s * half
    base = cx - s * half
    shaft_end = tip - s * head
    # hampe
    d.line([(base, cy), (shaft_end, cy)], fill=color, width=int(thick))
    d.ellipse([base - thick / 2, cy - thick / 2, base + thick / 2, cy + thick / 2],
              fill=color)
    # pointe (triangle)
    d.polygon([(tip, cy), (shaft_end, cy - hh), (shaft_end, cy + hh)], fill=color)


def render(entry, variant, side=4500):
    ink = adapt(INK, variant)
    red = adapt(RED, variant)
    token_lines = [parse_line(l) for l in entry["lines"]]
    direction = entry.get("dir", "right")

    margin = int(side * 0.12)
    max_w = side - 2 * margin
    sz = fit_size(token_lines, max_w, hi=int(side * 0.16))
    f = load_font(FONT, sz)
    line_gap = int(sz * 0.13)

    asc = f.getbbox("ÀÇgjpqy")
    lh = asc[3] - asc[1]
    base_off = asc[1]
    n = len(token_lines)
    text_h = n * lh + line_gap * (n - 1)

    img = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = side // 2

    widths = [line_w(f, tl) for tl in token_lines]
    block_w = max(widths)
    arrow_w = int(min(block_w * 0.9, max_w * 0.7))
    arrow_thick = max(20, int(sz * 0.22))
    arrow_gap = int(sz * 0.45)
    total_h = text_h + arrow_gap + arrow_thick * 2

    top = side // 2 - total_h // 2
    y = top
    for tl, w in zip(token_lines, widths):
        x = cx - w / 2
        for seg, acc in tl:
            d.text((x, y - base_off), seg, font=f, fill=red if acc else ink)
            x += f.getlength(seg)
        y += lh + line_gap

    y += arrow_gap
    draw_arrow(d, cx, y + arrow_thick, arrow_w, arrow_thick, direction, ink)

    bb = img.getbbox()
    if bb is None:
        return img
    img = img.crop(bb)
    pad = int(side * 0.09)
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(img, (pad, pad))
    if max(out.size) != side:
        k = side / max(out.size)
        out = out.resize((round(out.width * k), round(out.height * k)), Image.LANCZOS)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="produits/arrow")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--lang", default="")
    ap.add_argument("--data", default=DATA_PATH)
    ap.add_argument("--variant", default="both", choices=["both", "dark", "light"])
    args = ap.parse_args()

    data = json.load(open(args.data, encoding="utf-8"))
    entries = data["entries"]
    sel = set(args.only.split(",")) if args.only else None
    items = [e for e in entries
             if (not sel or e["id"] in sel) and (not args.lang or e.get("lang") == args.lang)]

    if args.sheet:
        cols = 4
        cell = 600
        rows = (len(items) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, rows * cell), (246, 246, 248))
        dd = ImageDraw.Draw(sheet)
        try:
            lab = load_font("fjalla", 16)
        except Exception:
            lab = ImageFont.load_default()
        for i, e in enumerate(items):
            im = render(e, "dark", side=1300)
            im.thumbnail((cell - 40, cell - 60))
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 20, r * cell + 20))
            dd.text((c * cell + 20, r * cell + cell - 26), e["id"][:34],
                    fill=(70, 70, 70), font=lab)
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=88)
        print(f"planche: {args.sheet} ({len(items)})")
        return

    variants = list(VARIANTS) if args.variant == "both" else [args.variant]
    os.makedirs(args.out, exist_ok=True)
    n = 0
    for e in items:
        for v in variants:
            im = render(e, v)
            im.save(os.path.join(args.out, f"{e['id']}__{v}.png"), dpi=(300, 300))
            n += 1
    print(f"{n} fichiers ({len(items)} × {len(variants)} variantes) → {args.out}")


if __name__ == "__main__":
    main()
