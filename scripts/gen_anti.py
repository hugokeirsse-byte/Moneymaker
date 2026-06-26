#!/usr/bin/env python3
"""
gen_anti.py — série « liste qui rétrécit à l'infini ».

Un mot d'accroche (ex. « ANTI ») puis une parenthèse ouvrante et une liste de
mots écrits de plus en plus petits, comme si ça continuait sans fin, terminée
par « … ) ». Idéal pour « ANTI(fasciste, capitaliste, ultra-riches, … ) ».

Écriture Pacifico, encre noire + mots rouges en alternance, fond transparent,
4500 px, 300 DPI, deux variantes maillot.

Usage :
    python scripts/gen_anti.py --out produits/anti
    python scripts/gen_anti.py --sheet /tmp/anti.png
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402
from typo_variants import VARIANTS, adapt  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

DATA_PATH = "data/anti.json"
FONT = "script"
INK = (28, 28, 32, 255)
RED = (190, 46, 38, 255)

SHRINK = 0.86      # facteur de réduction par ligne
MIN_RATIO = 0.07   # taille mini relative au head (≈ minuscule → effet « infini »)


def measure(f, t):
    b = f.getbbox(t)
    return b[2] - b[0], b[3] - b[1], b[1]


def render(entry, variant, idx=0, side=4500):
    ink = adapt(INK, variant)
    red = adapt(RED, variant)
    head = entry.get("head", "ANTI")
    words = list(entry["items"])
    # dernier mot : parenthèse fermante collée
    words[-1] = words[-1].rstrip(",") + " )"

    margin = int(side * 0.11)
    max_w = side - 2 * margin

    # head bien visible : « Head ( » calé à ~62 % de la largeur utile
    lo, hi = 20, int(side * 0.17)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load_font(FONT, mid)
        if measure(f, head + " (")[0] <= max_w * 0.62:
            lo = mid
        else:
            hi = mid - 1
    head_sz = lo
    min_sz = max(9, int(head_sz * MIN_RATIO))

    # ── empilage : on garnit chaque ligne de plusieurs mots, taille décroissante ──
    # grandes lignes = peu de mots (2-3) ; petites lignes = beaucoup de mots
    target_w = max_w
    sz = int(head_sz * 0.78)
    i = 0
    body = []  # (size, text)
    while i < len(words):
        f = load_font(FONT, sz)
        line = []
        w = 0.0
        while i < len(words):
            piece = (" " if line else "") + words[i]
            ww = f.getlength(piece)
            if line and w + ww > target_w:
                break
            line.append(words[i])
            w += ww
            i += 1
        body.append((sz, " ".join(line)))
        sz = max(min_sz, int(sz * SHRINK))

    img = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = side // 2

    fh = load_font(FONT, head_sz)
    rows = [(fh, head + " (", head_sz, False)]
    for s, t in body:
        rows.append((load_font(FONT, s), t, s, True))

    heights = [measure(f, t)[1] for f, t, _, _ in rows]
    gaps = [int(s * 0.20) for _, _, s, _ in rows]
    total_h = sum(heights) + sum(gaps[:-1])
    top = side // 2 - total_h // 2

    n_body = len(body)
    y = top
    block_w = 0
    item_k = 0
    for k, (f, t, s, is_item) in enumerate(rows):
        w, h, off = measure(f, t)
        block_w = max(block_w, w)
        if is_item:
            col = red if (item_k % 2 == 0) else ink
            frac = item_k / max(1, n_body - 1)
            alpha = int(255 - 95 * frac)
            col = col[:3] + (alpha,)
            item_k += 1
        else:
            col = ink
        d.text((cx - w / 2, y - off), t, font=f, fill=col)
        y += h + gaps[k]

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
    ap.add_argument("--out", default="produits/anti")
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
        for k, (i, e) in enumerate(items):
            im = render(e, "dark", idx=i, side=1300)
            im.thumbnail((cell - 40, cell - 60))
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(k, cols)
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
    for i, e in items:
        for v in variants:
            im = render(e, v, idx=i)
            im.save(os.path.join(args.out, f"{e['id']}__{v}.png"), dpi=(300, 300))
            n += 1
    print(f"{n} fichiers ({len(items)} × {len(variants)} variantes) → {args.out}")


if __name__ == "__main__":
    main()
