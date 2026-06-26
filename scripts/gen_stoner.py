#!/usr/bin/env python3
"""
gen_stoner.py — série « stoner / festival » (ambiguë, clin d'œil).

Phrases Pacifico. Deux modes :
  - normal : encre noire + mots rouges (markup *mot*) ;
  - "flag" : glyphes remplis d'un drapeau à bandes horizontales
    (ex. "rasta" = rouge/jaune/vert pour un « 420 » assumé mais soft).

Fond transparent, 4500 px, 300 DPI, deux variantes maillot.

Usage :
    python scripts/gen_stoner.py --out produits/stoner
    python scripts/gen_stoner.py --sheet /tmp/stoner.png
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402
from typo_variants import VARIANTS, adapt  # noqa: E402
from typo_ornaments import pick_style, apply_ornament  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

DATA_PATH = "data/stoner.json"
FONT = "script"
INK = (28, 28, 32, 255)
RED = (190, 46, 38, 255)

FLAGS = {
    "rasta": [(0, 158, 73), (254, 209, 0), (200, 16, 46)],   # vert / jaune / rouge
    "jamaica": [(0, 158, 73), (255, 209, 0), (20, 20, 20)],   # vert / or / noir
    "pride": [(228, 3, 3), (255, 140, 0), (255, 237, 0),
              (0, 128, 38), (0, 77, 255), (117, 7, 135)],
}


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


def flag_fill(mask, bbox, colors):
    """Renvoie un calque RGBA : bandes horizontales colorées sous l'alpha `mask`."""
    W, H = mask.size
    bands = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    x0, y0, x1, y1 = bbox
    span = max(1, y1 - y0)
    n = len(colors)
    db = ImageDraw.Draw(bands)
    for i, col in enumerate(colors):
        by0 = int(y0 + span * i / n)
        by1 = int(y0 + span * (i + 1) / n)
        db.rectangle([0, by0, W, by1], fill=col + (255,))
    bands.putalpha(mask)
    return bands


def render(entry, variant, idx=0, side=4500):
    flag = entry.get("flag")
    style = entry.get("ornament", None if flag else pick_style(idx))
    ink = adapt(INK, variant)
    red = adapt(RED, variant)
    token_lines = [parse_line(l) for l in entry["lines"]]

    margin = int(side * 0.12)
    max_w = side - 2 * margin
    sz = fit_size(token_lines, max_w, hi=int(side * 0.20 if flag else side * 0.16))
    f = load_font(FONT, sz)
    line_gap = int(sz * 0.14)

    asc = f.getbbox("ÀÇgjpqy")
    lh = asc[3] - asc[1]
    base_off = asc[1]
    n = len(token_lines)
    text_h = n * lh + line_gap * (n - 1)

    img = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    cx = side // 2
    top = side // 2 - text_h // 2
    widths = [line_w(f, tl) for tl in token_lines]
    block_w = max(widths)
    bbox = (cx - block_w // 2, top, cx + block_w // 2, top + text_h)

    if flag and flag in FLAGS:
        # 1) contour sombre dessiné SOUS le remplissage (sur son propre calque,
        #    sinon le remplissage transparent effacerait les glyphes colorés).
        sw = max(3, int(sz * 0.045))
        outline = Image.new("RGBA", (side, side), (0, 0, 0, 0))
        do = ImageDraw.Draw(outline)
        mask = Image.new("L", (side, side), 0)
        dm = ImageDraw.Draw(mask)
        y = top
        for tl, w in zip(token_lines, widths):
            x = cx - w / 2
            for seg, _ in tl:
                do.text((x, y - base_off), seg, font=f, fill=(22, 22, 24, 255),
                        stroke_width=sw, stroke_fill=(22, 22, 24, 255))
                dm.text((x, y - base_off), seg, font=f, fill=255)
                x += f.getlength(seg)
            y += lh + line_gap
        img.alpha_composite(outline)
        # 2) remplissage drapeau (bandes colorées) par-dessus le contour
        img.alpha_composite(flag_fill(mask, bbox, FLAGS[flag]))
    else:
        d = ImageDraw.Draw(img)
        y = top
        for tl, w in zip(token_lines, widths):
            x = cx - w / 2
            for seg, acc in tl:
                d.text((x, y - base_off), seg, font=f, fill=red if acc else ink)
                x += f.getlength(seg)
            y += lh + line_gap
        if style:
            qf = load_font(FONT, int(sz * 1.5))
            apply_ornament(d, style, bbox, ink, red, scale=side / 4500.0, quote_font=qf)

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
    ap.add_argument("--out", default="produits/stoner")
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
