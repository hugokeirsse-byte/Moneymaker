#!/usr/bin/env python3
"""
gen_strikethrough.py — série « correction » : mot(s) barré(s) puis remplacé(s).

Format meme : une phrase dont la fin est rayée et corrigée en dessous, en rouge
(ex. « Girls just want to have ~~fun~~ » → « equal rights »). Écriture Pacifico,
encre noire, rature + correction en rouge. Mot(s) clés rouges possibles.

Fond transparent, 4500 px, 300 DPI, deux variantes maillot.

Usage :
    python scripts/gen_strikethrough.py --out produits/corrige
    python scripts/gen_strikethrough.py --sheet /tmp/corrige.png
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402
from typo_variants import VARIANTS, adapt  # noqa: E402
from typo_ornaments import pick_style, apply_ornament, sticker_layer  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

DATA_PATH = "data/corrige.json"
FONT = "script"
INK = (28, 28, 32, 255)
RED = (190, 46, 38, 255)


def measure(f, t):
    b = f.getbbox(t)
    return b[2] - b[0], b[3] - b[1], b[1]


def fit_size(strings, max_w, hi=620, lo=20):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load_font(FONT, mid)
        if max(measure(f, s)[0] for s in strings if s) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


def render(entry, variant, idx=0, side=4500):
    style = entry.get("ornament", pick_style(idx))
    sticker = (style == "sticker")
    if sticker:
        ink, red = INK, RED          # carte blanche : encre sombre + rouge
    else:
        ink = adapt(INK, variant)
        red = adapt(RED, variant)
    kept = entry.get("kept", [])
    struck = entry["struck"]
    repl = entry["replacement"]

    margin = int(side * (0.17 if sticker else 0.12))
    max_w = side - 2 * margin
    all_lines = kept + [struck, repl]
    sz = fit_size(all_lines, max_w, hi=int(side * 0.17))
    f = load_font(FONT, sz)
    fr = load_font(FONT, int(sz * 1.06))   # correction un poil plus grande
    gap = int(sz * 0.16)

    img = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = side // 2

    # mesure hauteur totale
    dims_keep = [measure(f, t) for t in kept]
    dw_s, dh_s, off_s = measure(f, struck)
    dw_r, dh_r, off_r = measure(fr, repl)
    total_h = (sum(h for _, h, _ in dims_keep) + dh_s + dh_r
               + gap * (len(kept) + 1) + int(sz * 0.10))
    block_w = max([w for w, _, _ in dims_keep] + [dw_s, dw_r])
    top = side // 2 - total_h // 2
    bbox = (cx - block_w // 2, top, cx + block_w // 2, top + total_h)

    if sticker:
        img.alpha_composite(sticker_layer((side, side), bbox, side / 4500.0))

    y = top
    # lignes conservées (noir)
    for t, (w, h, off) in zip(kept, dims_keep):
        d.text((cx - w // 2, y - off), t, font=f, fill=ink)
        y += h + gap

    # ligne barrée (noir + rature rouge, trait épais)
    sx = cx - dw_s // 2
    d.text((sx, y - off_s), struck, font=f, fill=ink)
    line_y = y + dh_s // 2
    lw = max(9, int(sz * 0.075))
    ext = int(sz * 0.08)
    d.line([(sx - ext, line_y), (sx + dw_s + ext, line_y)], fill=red, width=lw)
    y += dh_s + gap + int(sz * 0.10)

    # correction (rouge, en dessous)
    d.text((cx - dw_r // 2, y - off_r), repl, font=fr, fill=red)

    if style and not sticker:
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
    ap.add_argument("--out", default="produits/corrige")
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
