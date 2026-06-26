#!/usr/bin/env python3
"""
gen_insult_collection.py — collection multi-langues : une insulte par pays.

Deux modes :
  --mode poster  : un fichier par insulte (mot seul en grande typo + pays)
  --mode grid    : planche contact de toutes les insultes

Usage :
    python scripts/gen_insult_collection.py --mode poster --out produits/insults_multilang
    python scripts/gen_insult_collection.py --mode grid   --out produits/insults_multilang
    python scripts/gen_insult_collection.py --country France --out produits/insults_multilang
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402
from typo_variants import VARIANTS, adapt  # noqa: E402

from PIL import Image, ImageDraw  # noqa: E402

DATA_PATH = "data/insults_multilang.json"

WORD_FONT = "script"    # Pacifico
LABEL_FONT = "script"   # Pacifico pour le libellé aussi


def measure(font, text):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box[1]


def hex_to_rgba(h, alpha=255):
    h = h.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return (r, g, b, alpha)


def fit_size(text, key, max_w, hi=1200, lo=20):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if measure(load_font(key, mid), text)[0] <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


def render_poster(entry, side=4500, variant="dark"):
    """Un mot, gros, centré. Pays + signification en petit en dessous."""
    margin = int(side * 0.08)
    max_w = side - 2 * margin

    color = adapt((201, 162, 39, 255), variant)    # rouge
    label_col = adapt((100, 100, 100, 255), variant)

    word = entry["word"].upper()
    sz = fit_size(word, WORD_FONT, max_w)
    f_word = load_font(WORD_FONT, sz)
    ww, wh, woff = measure(f_word, word)

    label = f"{entry['country']}  ·  \"{entry['meaning']}\""
    label_sz = max(30, sz // 8)
    f_label = load_font(LABEL_FONT, label_sz)
    lw, lh, loff = measure(f_label, label)

    gap = int(sz * 0.18)
    total_h = wh + gap + lh
    canvas_h = total_h + 2 * margin

    img = Image.new("RGBA", (side, canvas_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    y = margin
    d.text(((side - ww) // 2, y - woff), word, font=f_word, fill=color)
    y += wh + gap
    d.text(((side - lw) // 2, y - loff), label, font=f_label, fill=label_col)

    # crop + padding uniforme
    bbox = img.getbbox()
    if bbox is None:
        return img
    img = img.crop(bbox)
    pad = int(side * 0.06)
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(img, (pad, pad))
    if max(out.size) != side:
        r = side / max(out.size)
        out = out.resize((round(out.width * r), round(out.height * r)),
                         Image.LANCZOS)
    return out


def render_grid(entries, cols=5, cell=900):
    """Planche de toutes les insultes, fond blanc."""
    rows = (len(entries) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * cell, rows * cell), (250, 250, 250))

    for i, entry in enumerate(entries):
        word = entry["word"].upper()
        color = (201, 162, 39)   # rouge
        pad = int(cell * 0.08)
        max_w = cell - 2 * pad

        sz = fit_size(word, WORD_FONT, max_w)
        f_w = load_font(WORD_FONT, sz)
        ww, wh, woff = measure(f_w, word)

        f_l = load_font(LABEL_FONT, max(14, sz // 5))
        label = entry["country"]
        lw, lh, loff = measure(f_l, label)

        cell_img = Image.new("RGB", (cell, cell), (250, 250, 250))
        d = ImageDraw.Draw(cell_img)
        # bande de couleur en haut
        d.rectangle([0, 0, cell, cell // 10], fill=color)
        # mot
        y_word = cell // 10 + (cell * 3 // 4 - wh) // 2
        d.text(((cell - ww) // 2, y_word - woff), word, font=f_w, fill=color)
        # pays
        d.text(((cell - lw) // 2, cell - lh - pad // 2 - loff),
               label, font=f_l, fill=(120, 120, 120))

        r, c = divmod(i, cols)
        sheet.paste(cell_img, (c * cell, r * cell))

    return sheet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["poster", "grid"], default="poster")
    ap.add_argument("--out", default="produits/insults_multilang")
    ap.add_argument("--country", default="", help="filtre sur un pays")
    ap.add_argument("--data", default=DATA_PATH)
    ap.add_argument("--variant", default="both", choices=["both", "dark", "light"])
    args = ap.parse_args()

    data = json.load(open(args.data, encoding="utf-8"))
    entries = data["entries"]
    if args.country:
        entries = [e for e in entries
                   if args.country.lower() in e["country"].lower()]

    os.makedirs(args.out, exist_ok=True)

    if args.mode == "grid":
        sheet = render_grid(entries)
        path = os.path.join(args.out, "insults_grid.png")
        sheet.save(path, quality=92)
        print(f"grille: {path}  ({sheet.width}×{sheet.height})")
        return

    # mode poster : un fichier par insulte × variante maillot
    variants = list(VARIANTS) if args.variant == "both" else [args.variant]
    for entry in entries:
        slug = (entry["country"].lower().replace(" ", "_") + "_"
                + entry["word"].lower().replace(" ", "_").replace("'", ""))
        for v in variants:
            im = render_poster(entry, variant=v)
            im.save(os.path.join(args.out, f"{slug}_poster__{v}.png"), dpi=(300, 300))

    print(f"{len(entries)} × {len(variants)} variantes → {args.out}")


if __name__ == "__main__":
    main()
