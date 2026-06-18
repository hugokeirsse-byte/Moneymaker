#!/usr/bin/env python3
"""
gen_wordcloud.py — designs « mots en forme » (format word_shape) à 0€.

Remplit une silhouette avec les mots-clés d'une niche, dans la police de la
collection, sur fond TRANSPARENT. Aucune IA payante : rendu local via la
bibliothèque open-source `wordcloud` (licence MIT).

Idée : « plein de mots qui forment un visuel ». Plus un mot est gros, plus il
est important — et on peut piloter cette taille par le VRAI volume de recherche
(rapport niche_jokes_ranked_*.json) pour que la demande réelle saute aux yeux.

Masques acceptés :
  - intégrés (aucune dépendance externe) : heart, star, hexagon, circle,
    diamond, arrow_up, australia ;
  - n'importe quel PNG silhouette via --mask chemin.png (les zones NON blanches
    sont remplies de mots ; idéal avec une icône CC0 d'openclipart / SVG Repo).

Couleurs : rainbow (arc-en-ciel réparti), black (tout noir), ou une palette
nommée (sunset, ocean, forest, candy). Fond toujours transparent.

Exemples (depuis la racine du repo) :
    python scripts/gen_wordcloud.py --words "nat 20,crit fail,loot,respawn" \
        --mask heart --colors rainbow --font-path assets/fonts/Kaushan_Script.ttf \
        --out produits/word_shapes --name rpg_coeur
    python scripts/gen_wordcloud.py --freq-file data/australia_slang.json \
        --mask australia --colors sunset --out produits/word_shapes
"""
import argparse
import colorsys
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

WHITE = 255  # wordcloud remplit là où le masque n'est PAS blanc


# ---------------------------------------------------------------- masques
def _poly_mask(size, points):
    """Masque (fond blanc, polygone noir) à partir de points normalisés 0..1."""
    img = Image.new("L", (size, size), WHITE)
    d = ImageDraw.Draw(img)
    d.polygon([(x * size, y * size) for x, y in points], fill=0)
    return np.array(img)


def builtin_mask(name, size=1600):
    n = name.lower()
    if n == "circle":
        img = Image.new("L", (size, size), WHITE)
        ImageDraw.Draw(img).ellipse([size * 0.04, size * 0.04,
                                     size * 0.96, size * 0.96], fill=0)
        return np.array(img)
    if n == "heart":
        img = Image.new("L", (size, size), WHITE)
        d = ImageDraw.Draw(img)
        pts = []
        for t in np.linspace(0, 2 * math.pi, 720):
            x = 16 * math.sin(t) ** 3
            y = (13 * math.cos(t) - 5 * math.cos(2 * t)
                 - 2 * math.cos(3 * t) - math.cos(4 * t))
            pts.append((0.5 + x / 38.0, 0.46 - y / 38.0))
        d.polygon([(px * size, py * size) for px, py in pts], fill=0)
        return np.array(img)
    if n in ("star", "star5"):
        pts, cx, cy = [], 0.5, 0.5
        for i in range(10):
            r = 0.47 if i % 2 == 0 else 0.20
            a = math.pi / 2 + i * math.pi / 5
            pts.append((cx + r * math.cos(a), cy - r * math.sin(a)))
        return _poly_mask(size, pts)
    if n in ("hexagon", "hex"):
        pts = [(0.5 + 0.46 * math.cos(math.pi / 6 + i * math.pi / 3),
                0.5 + 0.46 * math.sin(math.pi / 6 + i * math.pi / 3))
               for i in range(6)]
        return _poly_mask(size, pts)
    if n == "diamond":
        return _poly_mask(size, [(0.5, 0.03), (0.97, 0.5), (0.5, 0.97), (0.03, 0.5)])
    if n in ("arrow_up", "arrow"):
        return _poly_mask(size, [(0.5, 0.04), (0.95, 0.5), (0.7, 0.5),
                                 (0.7, 0.96), (0.3, 0.96), (0.3, 0.5), (0.05, 0.5)])
    if n == "australia":
        # Silhouette simplifiée de l'Australie (sens horaire depuis le NW Cape)
        raw = [
            (0.08, 0.31), (0.13, 0.20), (0.18, 0.13), (0.26, 0.09),
            (0.36, 0.08), (0.44, 0.10), (0.47, 0.09),
            (0.53, 0.11), (0.57, 0.08),
            (0.57, 0.17), (0.56, 0.27), (0.60, 0.32), (0.65, 0.27), (0.68, 0.18),
            (0.72, 0.10), (0.75, 0.07), (0.77, 0.12),
            (0.80, 0.20), (0.84, 0.31), (0.91, 0.43), (0.92, 0.50),
            (0.89, 0.57), (0.87, 0.63), (0.85, 0.68),
            (0.78, 0.66), (0.66, 0.65),
            (0.62, 0.60), (0.58, 0.65), (0.56, 0.68), (0.52, 0.65),
            (0.50, 0.68), (0.46, 0.72),
            (0.36, 0.74), (0.24, 0.72),
            (0.14, 0.66),
            (0.06, 0.55), (0.05, 0.44),
        ]
        # Étirer y pour remplir le carré (Australie est plus large que haute)
        pts = [(x, y * 1.20) for x, y in raw]
        return _poly_mask(size, pts)
    raise SystemExit(f"masque intégré inconnu : {name} "
                     "(heart, star, hexagon, circle, diamond, arrow_up, australia)")


def load_mask(spec):
    if os.path.isfile(spec):
        im = Image.open(spec).convert("L")
        side = max(im.size)
        canvas = Image.new("L", (side, side), WHITE)
        canvas.paste(im, ((side - im.width) // 2, (side - im.height) // 2))
        arr = np.array(canvas)
        # binarise : sombre = forme à remplir
        return np.where(arr < 128, 0, WHITE).astype(np.uint8)
    return builtin_mask(spec)


# ---------------------------------------------------------------- couleurs
PALETTES = {
    "sunset": [(255, 94, 58), (255, 149, 5), (255, 191, 0), (214, 40, 100)],
    "ocean":  [(0, 119, 182), (0, 180, 216), (72, 202, 228), (2, 62, 138)],
    "forest": [(45, 106, 79), (82, 183, 136), (27, 67, 50), (149, 213, 178)],
    "candy":  [(247, 37, 133), (114, 9, 183), (58, 12, 163), (76, 201, 240)],
}


def make_color_func(mode, words):
    if mode == "black":
        def cf(*a, **k):
            return (20, 20, 20)
        return cf
    if mode in PALETTES:
        pal = PALETTES[mode]
        state = {"i": 0}

        def cf(*a, **k):
            c = pal[state["i"] % len(pal)]
            state["i"] += 1
            return c
        return cf
    # rainbow : teinte répartie sur l'ensemble des mots (rouge -> violet)
    order = {w: i for i, w in enumerate(words)}
    total = max(len(words) - 1, 1)

    def cf(word, *a, **k):
        hue = 0.83 * (order.get(word, 0) / total)
        r, g, b = colorsys.hsv_to_rgb(hue, 0.88, 0.97)
        return (int(r * 255), int(g * 255), int(b * 255))
    return cf


# ---------------------------------------------------------------- données
def words_from_report(path, niche_substr):
    d = json.load(open(path, encoding="utf-8"))
    freq = {}
    for j in d.get("ranked", []):
        if niche_substr.lower() not in j.get("niche", "").lower():
            continue
        weight = float(j.get("real_volume", 0)) or 1.0
        for kw in (j.get("keywords") or [j.get("text", "")]):
            kw = kw.strip()
            if kw:
                freq[kw] = max(freq.get(kw, 0), weight)
    return freq


def make_cloud(freq, mask, font_path, color_mode, scale=1600):
    from wordcloud import WordCloud
    words = list(freq.keys())
    wc = WordCloud(
        font_path=font_path,
        mask=mask,
        mode="RGBA",
        background_color=None,     # fond transparent
        max_words=len(words) + 5,
        relative_scaling=0.5,
        prefer_horizontal=0.92,
        margin=2,
        color_func=make_color_func(color_mode, words),
    )
    wc.generate_from_frequencies(freq)
    return wc.to_image()  # RGBA


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--words", default="", help="liste séparée par des virgules")
    ap.add_argument("--from-report", default="", help="reports/niche_jokes_ranked_*.json")
    ap.add_argument("--freq-file", default="", help="JSON {mot: poids} (ex. data/australia_slang.json)")
    ap.add_argument("--niche", default="", help="filtre de niche (sous-chaîne)")
    ap.add_argument("--mask", default="heart")
    ap.add_argument("--colors", default="rainbow")
    ap.add_argument("--font-path", default="")
    ap.add_argument("--out", default="produits/word_shapes")
    ap.add_argument("--name", default="")
    ap.add_argument("--sheet", default="")
    args = ap.parse_args()

    if args.freq_file:
        raw = json.load(open(args.freq_file, encoding="utf-8"))
        freq = {str(k): float(v) for k, v in raw.items() if str(k).strip()}
    elif args.from_report:
        freq = words_from_report(args.from_report, args.niche)
    else:
        freq = {w.strip(): 1.0 for w in args.words.split(",") if w.strip()}
    if not freq:
        print("ERREUR: aucun mot (utilise --words ou --from-report/--niche)", file=sys.stderr)
        return 1

    font = args.font_path or None
    if font and not os.path.isfile(font):
        print(f"[police] introuvable : {font} — police par défaut", file=sys.stderr)
        font = None

    mask = load_mask(args.mask)
    img = make_cloud(freq, mask, font, args.colors)

    name = args.name or f"{(args.niche or 'mots').replace(' ', '_')}_{args.mask}_{args.colors}"
    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, f"{name}.png")
    img.save(out_path, dpi=(300, 300))
    print(f"{out_path}  ({img.width}x{img.height}, {len(freq)} mots)")

    if args.sheet:
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        bg = Image.new("RGB", img.size, (235, 235, 235))
        bg.paste(img, (0, 0), img)
        bg.save(args.sheet, quality=90)
        print("aperçu:", args.sheet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
