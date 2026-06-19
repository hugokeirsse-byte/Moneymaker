#!/usr/bin/env python3
"""
gen_insult_poster.py — un seul mot en grande typographie, rien d'autre.

Rendu minimal : le mot seul, centré, en beauté. Fond blanc transparent.
Deux variantes : encre sombre (foncée) et encre colorée.

Usage :
    python scripts/gen_insult_poster.py --word GOURGANDINE --out produits/insult_posters
    python scripts/gen_insult_poster.py --word FAQUIN --color "#c05010"
    python scripts/gen_insult_poster.py --batch data/insults_france.json --top 10
"""
import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = [
    "assets/fonts/Anton-Regular.ttf",
    "/usr/share/fonts/truetype/anton/Anton-Regular.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
]

SERIF_CANDIDATES = [
    "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
]

COLOR_PRESETS = [
    (22, 22, 26),
    (195, 60, 20),
    (20, 70, 160),
    (180, 130, 0),
    (40, 120, 55),
    (140, 20, 140),
]


def best_font(serif=False):
    candidates = SERIF_CANDIDATES if serif else FONT_CANDIDATES
    for p in candidates:
        if os.path.exists(p):
            return p
    return FONT_CANDIDATES[-1]


def measure(font, text):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box[1]


def render_word(word, color=(22, 22, 26), side=4500, serif=False):
    margin = int(side * 0.10)
    max_w = side - 2 * margin

    fp = best_font(serif=serif)
    # Taille maximale pour tenir dans la largeur
    lo, hi = 20, 1400
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = ImageFont.truetype(fp, mid)
        w, _, _ = measure(f, word)
        if w <= max_w:
            lo = mid
        else:
            hi = mid - 1

    f = ImageFont.truetype(fp, lo)
    w, h, off = measure(f, word)

    # Canvas carré 4500×4500
    img = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = (side - w) // 2
    y = (side - h) // 2
    d.text((x, y - off), word, font=f, fill=color + (255,) if len(color) == 3 else color)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--word", default="", help="mot à afficher")
    ap.add_argument("--color", default="", help="couleur hex (ex. #c05010)")
    ap.add_argument("--serif", action="store_true")
    ap.add_argument("--out", default="produits/insult_posters")
    ap.add_argument("--batch", default="", help="fichier JSON {mot: poids}")
    ap.add_argument("--top", type=int, default=5, help="nb de mots en batch")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)

    def hex_to_rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    if args.batch:
        data = json.load(open(args.batch, encoding="utf-8"))
        words = sorted(data.items(), key=lambda x: -x[1])[:args.top]
        for i, (word, _) in enumerate(words):
            color = COLOR_PRESETS[i % len(COLOR_PRESETS)]
            im = render_word(word.upper(), color=color, serif=args.serif)
            slug = word.lower().replace(" ", "_").replace("'", "").replace("'", "")
            path = os.path.join(args.out, f"{slug}_poster.png")
            im.save(path, dpi=(300, 300))
            print(f"  {path}")
        print(f"\n{len(words)} posters → {args.out}")
        return

    if not args.word:
        ap.error("--word ou --batch requis")

    color = hex_to_rgb(args.color) if args.color else (22, 22, 26)
    im = render_word(args.word.upper(), color=color, serif=args.serif)
    slug = args.word.lower().replace(" ", "_").replace("'", "")
    path = os.path.join(args.out, f"{slug}_poster.png")
    im.save(path, dpi=(300, 300))
    print(path)


if __name__ == "__main__":
    main()
