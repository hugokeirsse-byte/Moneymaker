#!/usr/bin/env python3
"""
gen_warning.py — série « FUMER TUE » détournée (mention sanitaire paquet de clopes).

Reproduit le format exact : carré/rectangle BLANC, fin liseré NOIR, texte NOIR en
gras Helvetica/Arial (ici Liberation Sans Bold, métriquement identique à Arial)
centré, toujours avec le mot « TUE » / « KILLS ». Pas d'en-tête « AVERTISSEMENT ».
Format public non déposé → parodie sûre (ni logo de marque, ni photo officielle).

Variantes :
  dark  (maillots clairs) : carré blanc, liseré + texte noirs (l'authentique)
  light (maillots foncés) : carré noir, liseré + texte blancs (inversé, lisible)
Fond transparent autour du cadre, 4500 px, 300 DPI.

Usage :
    python scripts/gen_warning.py --out produits/warning
    python scripts/gen_warning.py --sheet /tmp/warning.png
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

ARIAL = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
ARIAL_R = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
DATA_PATH = "data/warning.json"
BLACK = (0, 0, 0, 255)
WHITE = (255, 255, 255, 255)


def hfont(sz, reg=False):
    return ImageFont.truetype(ARIAL_R if reg else ARIAL, int(sz))


def wrap(font, text, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if cur and font.getlength(trial) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def fit(text, max_w, max_lines, hi, lo=20):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = hfont(mid)
        ls = wrap(f, text, max_w)
        if len(ls) <= max_lines and all(f.getlength(l) <= max_w for l in ls):
            lo = mid
        else:
            hi = mid - 1
    return lo


def render(entry, variant, side=4500):
    text = entry["text"].upper()
    sub = entry.get("sub", "")

    if variant == "dark":
        box, fg = WHITE, BLACK
    else:
        box, fg = BLACK, WHITE

    box_w = int(side * 0.88)
    side_pad = int(side * 0.055)
    inner_w = box_w - 2 * side_pad

    main_sz = fit(text, inner_w, max_lines=2, hi=int(side * 0.15))
    fmain = hfont(main_sz)
    lines = wrap(fmain, text, inner_w)
    line_h = int(main_sz * 1.14)

    sub_sz = int(main_sz * 0.46)
    fsub = hfont(sub_sz)

    top_pad = int(side * 0.06)
    bot_pad = int(side * 0.06)
    sub_block = int(sub_sz * 1.7) if sub else 0
    text_h = len(lines) * line_h + sub_block
    box_h = top_pad + text_h + bot_pad

    x0 = (side - box_w) // 2
    y0 = (side - box_h) // 2
    x1 = x0 + box_w
    y1 = y0 + box_h
    bw = max(3, int(box_w * 0.012))   # fin liseré, comme sur le paquet

    img = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rectangle([x0, y0, x1, y1], fill=box)
    for k in range(bw):
        d.rectangle([x0 + k, y0 + k, x1 - k, y1 - k], outline=fg)

    cx = (x0 + x1) / 2
    y = y0 + top_pad
    for ln in lines:
        b = fmain.getbbox(ln)
        d.text((cx - (b[2] - b[0]) / 2 - b[0], y - b[1]), ln, font=fmain, fill=fg)
        y += line_h
    if sub:
        b = fsub.getbbox(sub)
        d.text((cx - (b[2] - b[0]) / 2 - b[0], y + int(sub_sz * 0.25) - b[1]),
               sub, font=fsub, fill=fg)

    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="produits/warning")
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
        cell = 560
        rows = (len(items) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, rows * cell), (228, 228, 230))
        dd = ImageDraw.Draw(sheet)
        lab = ImageFont.truetype(ARIAL_R, 15)
        for i, e in enumerate(items):
            v = "light" if (i % 4 == 3) else "dark"
            im = render(e, v, side=1300)
            im.thumbnail((cell - 40, cell - 60))
            bg = Image.new("RGB", im.size, (255, 255, 255) if v == "dark" else (34, 34, 38))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 20, r * cell + 20))
            dd.text((c * cell + 20, r * cell + cell - 26), f"{e['id'][:30]} [{v}]",
                    fill=(70, 70, 70), font=lab)
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=88)
        print(f"planche: {args.sheet} ({len(items)})")
        return

    variants = ["dark", "light"] if args.variant == "both" else [args.variant]
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
