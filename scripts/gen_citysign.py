#!/usr/bin/env python3
"""
gen_citysign.py — série « panneau d'agglomération » détourné.

Reproduit le panneau d'entrée de ville français (EB10) : rectangle BLANC, liseré
ROUGE, nom de commune en noir, police type routière (Liberation Sans). Mais le
« nom de ville » est une vanne ou un truc touchant (Burn-Out-les-Bains,
Procrastine-sur-Loire, Câlin-sur-Mer…), avec parfois une sous-ligne (pop., devise).

Format public non déposé. Fond transparent autour du panneau, 4500 px, 300 DPI.

Usage :
    python scripts/gen_citysign.py --out produits/citysign
    python scripts/gen_citysign.py --sheet /tmp/citysign.png
"""
import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont

ARIAL = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
ARIALR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
DATA_PATH = "data/citysign.json"
RED = (200, 28, 28, 255)
BLACK = (24, 24, 26, 255)
WHITE = (255, 255, 255, 255)


def af(sz, reg=False):
    return ImageFont.truetype(ARIALR if reg else ARIAL, int(sz))


def fit(text, max_w, hi, lo=16):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if af(mid).getlength(text) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


def render(entry, side=4500):
    name = entry["name"]
    sub = entry.get("sub", "")

    box_w = int(side * 0.90)
    pad_x = int(side * 0.06)
    inner_w = box_w - 2 * pad_x

    name_sz = fit(name, inner_w, hi=int(side * 0.16))
    fname = af(name_sz)
    nb = fname.getbbox(name)
    nh = nb[3] - nb[1]

    sub_sz = int(name_sz * 0.40)
    fsub = af(sub_sz, reg=True)
    sub_h = int(sub_sz * 1.5) if sub else 0

    top_pad = int(side * 0.07)
    bot_pad = int(side * 0.07)
    box_h = top_pad + nh + sub_h + bot_pad
    x0 = (side - box_w) // 2
    y0 = (side - box_h) // 2
    x1 = x0 + box_w
    y1 = y0 + box_h
    bw = max(6, int(box_w * 0.018))      # liseré rouge
    rad = int(side * 0.012)

    img = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([x0, y0, x1, y1], radius=rad, fill=WHITE)
    for k in range(bw):
        d.rounded_rectangle([x0 + k, y0 + k, x1 - k, y1 - k], radius=max(1, rad - k),
                            outline=RED)

    cx = (x0 + x1) / 2
    d.text((cx, y0 + top_pad - nb[1]), name, font=fname, fill=BLACK, anchor="ma")
    if sub:
        d.text((cx, y0 + top_pad + nh + int(sub_sz * 0.4)), sub, font=fsub,
               fill=BLACK, anchor="ma")
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="produits/citysign")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--data", default=DATA_PATH)
    args = ap.parse_args()

    data = json.load(open(args.data, encoding="utf-8"))
    entries = data["entries"]
    sel = set(args.only.split(",")) if args.only else None
    items = [e for e in entries if not sel or e["id"] in sel]

    if args.sheet:
        cols = 3
        cell = 640
        rows = (len(items) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, rows * cell), (238, 238, 240))
        dd = ImageDraw.Draw(sheet)
        lab = af(15, reg=True)
        for i, e in enumerate(items):
            im = render(e, side=1300)
            im.thumbnail((cell - 30, cell - 50))
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 15, r * cell + 15))
            dd.text((c * cell + 16, r * cell + cell - 24), e["id"][:34],
                    fill=(70, 70, 70), font=lab)
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=88)
        print(f"planche: {args.sheet} ({len(items)})")
        return

    os.makedirs(args.out, exist_ok=True)
    n = 0
    for e in items:
        render(e).save(os.path.join(args.out, f"{e['id']}.png"), dpi=(300, 300))
        n += 1
    print(f"{n} panneaux → {args.out}")


if __name__ == "__main__":
    main()
