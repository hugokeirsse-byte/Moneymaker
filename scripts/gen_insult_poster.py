#!/usr/bin/env python3
"""
gen_insult_poster.py — un seul mot en belle typographie, rien d'autre.

Le mot, centré, dans une police de caractère soignée (assets/fonts). Fond
transparent, 4500×4500. Plusieurs polices/couleurs au choix ou en rotation.

Usage :
    python scripts/gen_insult_poster.py --word GOURGANDINE --font fatserif
    python scripts/gen_insult_poster.py --batch data/insults_france.json --top 10
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402
from typo_variants import VARIANTS, adapt  # noqa: E402

from PIL import Image, ImageDraw  # noqa: E402

# Pacifico pour tous, alternance noir / rouge
STYLE_CYCLE = ["script"]
COLOR_CYCLE = [(24, 24, 28), (190, 46, 38)]


def measure(font, text):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box[1]


def fit_size(text, key, max_w, hi=1500, lo=20):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if measure(load_font(key, mid), text)[0] <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


def render_word(word, key="fatserif", color=(24, 24, 28), side=4500):
    margin = int(side * 0.10)
    max_w = side - 2 * margin
    sz = fit_size(word, key, max_w)
    f = load_font(key, sz)
    w, h, off = measure(f, word)
    img = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    col = color + (255,) if len(color) == 3 else color
    d.text(((side - w) // 2, (side - h) // 2 - off), word, font=f, fill=col)
    return img


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def slugify(word):
    return (word.lower().replace(" ", "_").replace("'", "")
            .replace("'", "").replace("œ", "oe"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--word", default="")
    ap.add_argument("--font", default="fatserif", help="clé de police (typo_fonts)")
    ap.add_argument("--color", default="")
    ap.add_argument("--out", default="produits/insult_posters")
    ap.add_argument("--batch", default="")
    ap.add_argument("--top", type=int, default=6)
    ap.add_argument("--variant", default="both", choices=["both", "dark", "light"])
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    variants = list(VARIANTS) if args.variant == "both" else [args.variant]

    if args.batch:
        data = json.load(open(args.batch, encoding="utf-8"))
        words = sorted(data.items(), key=lambda x: -x[1])[:args.top]
        for i, (word, _) in enumerate(words):
            key = STYLE_CYCLE[i % len(STYLE_CYCLE)]
            color = COLOR_CYCLE[i % len(COLOR_CYCLE)]
            for v in variants:
                im = render_word(word.upper(), key=key, color=adapt(color + (255,), v))
                im.save(os.path.join(args.out, f"{slugify(word)}_poster__{v}.png"),
                        dpi=(300, 300))
        print(f"{len(words)} posters × {len(variants)} variantes → {args.out}")
        return

    if not args.word:
        ap.error("--word ou --batch requis")
    base = hex_to_rgb(args.color) if args.color else (24, 24, 28)
    for v in variants:
        im = render_word(args.word.upper(), key=args.font, color=adapt(base + (255,), v))
        im.save(os.path.join(args.out, f"{slugify(args.word)}_poster__{v}.png"), dpi=(300, 300))
    print(f"{slugify(args.word)} × {len(variants)} → {args.out}")


if __name__ == "__main__":
    main()
