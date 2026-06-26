#!/usr/bin/env python3
"""
gen_trending.py — 100 phrases POD ultra-optimisées / tendances.

Écriture Pacifico, encre noire + mots importants en rouge (markup *mot*),
et un embellissement choisi en ALTERNANCE parmi les cinq validés
(vague, double filet, étoiles, guillemets, cadre arrondi).

Fond transparent, 4500 px, 300 DPI, deux variantes maillot.

Usage :
    python scripts/gen_trending.py --out produits/trending
    python scripts/gen_trending.py --sheet /tmp/trending.png
    python scripts/gen_trending.py --only tr_but_first_coffee_en
    python scripts/gen_trending.py --lang fr
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402
from typo_variants import VARIANTS, adapt  # noqa: E402
from typo_ornaments import (STYLES, pick_style, apply_ornament,  # noqa: E402
                            sticker_layer)

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

DATA_PATH = "data/trending_100.json"
FONT = "script"
INK = (28, 28, 32, 255)
RED = (190, 46, 38, 255)


def parse_line(line):
    """'A *B* C' -> [('A ',False),('B',True),(' C',False)] (segments rouges)."""
    parts = line.split("*")
    return [(seg, i % 2 == 1) for i, seg in enumerate(parts) if seg != ""]


def line_width(font, tokens):
    return sum(font.getlength(t) for t, _ in tokens)


def fit_size(token_lines, max_w, hi=720, lo=20):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load_font(FONT, mid)
        if max(line_width(f, tl) for tl in token_lines) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


def render(entry, idx, variant, side=4500):
    style = entry.get("ornament", pick_style(idx))
    sticker = (style == "sticker")
    if sticker:
        # carte blanche : encre toujours sombre + rouge, quelle que soit la variante
        ink, accent = INK, RED
    else:
        ink = adapt(INK, variant)
        accent = adapt(RED, variant)
    token_lines = [parse_line(l) for l in entry["lines"]]

    margin = int(side * 0.16 if sticker else side * 0.13)
    max_w = side - 2 * margin
    sz = fit_size(token_lines, max_w, hi=int(side * 0.20))
    f = load_font(FONT, sz)
    qf = load_font(FONT, int(sz * 1.5))  # gros guillemets
    line_gap = int(sz * 0.14)

    # hauteurs de ligne via bbox d'un échantillon large
    asc = f.getbbox("ÀÇgjpqy")
    lh = asc[3] - asc[1]
    base_off = asc[1]
    n = len(token_lines)
    text_h = n * lh + line_gap * (n - 1)

    scale = side / 4500.0
    canvas = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(canvas)

    # bloc centré
    cy = side // 2
    top = cy - text_h // 2
    widths = [line_width(f, tl) for tl in token_lines]
    block_w = max(widths)
    cx = side // 2
    bbox = (cx - block_w // 2, top, cx + block_w // 2, top + text_h)

    if sticker:
        canvas.alpha_composite(sticker_layer((side, side), bbox, scale))

    y = top
    for tl, w in zip(token_lines, widths):
        x = cx - w / 2
        for seg, is_acc in tl:
            d.text((x, y - base_off), seg, font=f, fill=accent if is_acc else ink)
            x += f.getlength(seg)
        y += lh + line_gap

    if not sticker:
        apply_ornament(d, style, bbox, ink, accent, scale=scale, quote_font=qf)

    crop = canvas.getbbox()
    if crop is None:
        return canvas
    canvas = canvas.crop(crop)
    pad = int(side * 0.09)
    out = Image.new("RGBA", (canvas.width + 2 * pad, canvas.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(canvas, (pad, pad))
    if max(out.size) != side:
        k = side / max(out.size)
        out = out.resize((round(out.width * k), round(out.height * k)), Image.LANCZOS)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="produits/trending")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--lang", default="")
    ap.add_argument("--data", default=DATA_PATH)
    ap.add_argument("--variant", default="both", choices=["both", "dark", "light"])
    args = ap.parse_args()

    data = json.load(open(args.data, encoding="utf-8"))
    entries = data["entries"]
    sel = set(args.only.split(",")) if args.only else None
    items = [(i, e) for i, e in enumerate(entries)
             if (not sel or e["id"] in sel)
             and (not args.lang or e.get("lang") == args.lang)]

    if args.sheet:
        cols = 5
        cell = 560
        rows = (len(items) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, rows * cell), (246, 246, 248))
        dd = ImageDraw.Draw(sheet)
        try:
            lab = load_font("fjalla", 16)
        except Exception:
            lab = ImageFont.load_default()
        for k, (i, e) in enumerate(items):
            im = render(e, i, "dark", side=1300)
            im.thumbnail((cell - 40, cell - 64))
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(k, cols)
            sheet.paste(bg, (c * cell + 20, r * cell + 20))
            dd.text((c * cell + 20, r * cell + cell - 26),
                    f"{e['id'][:30]}  [{pick_style(i)}]", fill=(70, 70, 70), font=lab)
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=88)
        print(f"planche: {args.sheet} ({len(items)})")
        return

    variants = list(VARIANTS) if args.variant == "both" else [args.variant]
    os.makedirs(args.out, exist_ok=True)
    n = 0
    for i, e in items:
        for v in variants:
            im = render(e, i, v)
            im.save(os.path.join(args.out, f"{e['id']}__{v}.png"), dpi=(300, 300))
            n += 1
    print(f"{n} fichiers ({len(items)} phrases × {len(variants)} variantes) → {args.out}")


if __name__ == "__main__":
    main()
