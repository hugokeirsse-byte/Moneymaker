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
    diamond, arrow_up ;
  - n'importe quel PNG silhouette via --mask chemin.png (les zones NON blanches
    sont remplies de mots ; idéal avec une icône CC0 d'openclipart / SVG Repo).

Couleurs : rainbow (arc-en-ciel réparti), black (tout noir), ou une palette
nommée (sunset, ocean, forest, candy). Fond toujours transparent.

Exemples (depuis la racine du repo) :
    python scripts/gen_wordcloud.py --words "nat 20,crit fail,loot,respawn" \
        --mask heart --colors rainbow --font-path assets/fonts/Kaushan_Script.ttf \
        --out produits/word_shapes --name rpg_coeur
    python scripts/gen_wordcloud.py --from-report reports/niche_jokes_ranked_X.json \
        --niche chess --mask star --colors ocean --out produits/word_shapes
"""
import argparse
import colorsys
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageColor, ImageDraw

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
        # Silhouette simplifiée de l'Australie (horaire depuis le NW Cape)
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


def country_data(name, size=2000, margin=0.06, keep_frac=0.07):
    """Silhouette RÉELLE d'un pays via GeoJSON haute résolution (georgique/world-geojson).

    name : slug du pays en minuscules (ireland, usa, new_zealand, italy, jamaica,
    france, germany, mexico, canada...). Projette lon/lat (equirectangulaire,
    corrigée par cos(lat)) et garde les polygones principaux (>= keep_frac de
    l'aire max) pour écarter les îlots lointains.

    Retourne (mask_np, polys) — polys = polygones projetés en coords image (pour
    tracer un contour).
    """
    import urllib.request
    slug = name.strip().lower().replace(" ", "_")
    url = ("https://raw.githubusercontent.com/georgique/world-geojson/"
           f"develop/countries/{slug}.json")
    req = urllib.request.Request(url, headers={"User-Agent": "Moneymaker/1.0"})
    data = json.load(urllib.request.urlopen(req, timeout=40))
    geom = data["features"][0]["geometry"]
    if geom["type"] == "Polygon":
        rings = [geom["coordinates"][0]]
    else:  # MultiPolygon
        rings = [poly[0] for poly in geom["coordinates"]]

    def ring_area(r):
        a = 0.0
        for i in range(len(r)):
            x1, y1 = r[i]
            x2, y2 = r[(i + 1) % len(r)]
            a += x1 * y2 - x2 * y1
        return abs(a) / 2.0

    areas = [ring_area(r) for r in rings]
    amax = max(areas) if areas else 0
    keep = [r for r, a in zip(rings, areas) if a >= keep_frac * amax]

    pts_all = [pt for r in keep for pt in r]
    lats = [p[1] for p in pts_all]
    lat0 = math.radians(sum(lats) / len(lats))
    kx = math.cos(lat0)  # compression horizontale réaliste

    xs = [p[0] * kx for p in pts_all]
    ys = [-p[1] for p in pts_all]  # nord en haut
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    span = max(maxx - minx, maxy - miny) or 1.0
    inner = size * (1 - 2 * margin)
    offx = (size - inner * (maxx - minx) / span) / 2
    offy = (size - inner * (maxy - miny) / span) / 2

    def proj(lon, lat):
        x = (lon * kx - minx) / span * inner + offx
        y = (-lat - miny) / span * inner + offy
        return (x, y)

    polys = [[proj(lon, lat) for lon, lat in r] for r in keep]
    img = Image.new("L", (size, size), WHITE)
    d = ImageDraw.Draw(img)
    for r in polys:
        d.polygon(r, fill=0)
    return np.array(img), polys


def country_mask(name, size=2000, **kw):
    return country_data(name, size=size, **kw)[0]


def country_contour(polys, size, width=12, color=(255, 255, 255, 255)):
    """Trace le contour blanc du pays (fond transparent) pour bien le détourer."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for r in polys:
        ring = [(int(x), int(y)) for x, y in r]
        d.line(ring + [ring[0]], fill=color, width=width, joint="curve")
        # arrondir les sommets (joint="curve" ne couvre pas les bouts)
        rad = width // 2
        for x, y in ring:
            d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=color)
    return img


def load_mask(spec):
    if spec.lower().startswith("country:"):
        return country_mask(spec.split(":", 1)[1])
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


# ------------------------------------------------------------- drapeaux
# type "vbands" : bandes verticales (couleur selon position X)
# type "hbands" : bandes horizontales (couleur selon position Y)
# type "palette": drapeau complexe -> couleurs cyclées (non positionnel)
FLAGS = {
    # bande « blanche » des drapeaux -> gris clair (205) pour rester visible
    # sous un liseré blanc de sticker
    "ireland":     {"type": "vbands", "colors": [(22, 155, 98), (205, 205, 205), (255, 136, 62)]},
    "italy":       {"type": "vbands", "colors": [(0, 140, 69), (205, 205, 205), (205, 33, 42)]},
    "france":      {"type": "vbands", "colors": [(0, 85, 164), (205, 205, 205), (239, 65, 53)]},
    "mexico":      {"type": "vbands", "colors": [(0, 104, 71), (205, 205, 205), (206, 17, 38)]},
    "canada":      {"type": "vbands", "colors": [(213, 43, 30), (205, 205, 205), (213, 43, 30)]},
    "germany":     {"type": "hbands", "colors": [(30, 30, 30), (221, 0, 0), (255, 206, 0)]},
    "usa":         {"type": "palette", "colors": [(178, 34, 52), (205, 205, 205), (60, 59, 110)]},
    "new_zealand": {"type": "palette", "colors": [(0, 36, 125), (204, 20, 43), (205, 205, 205)]},
    "jamaica":     {"type": "palette", "colors": [(0, 155, 58), (254, 209, 0), (30, 30, 30)]},
    "australia":   {"type": "palette", "colors": [(0, 36, 125), (204, 20, 43), (205, 205, 205)]},
}


def make_flag_color_func(slug, width, height):
    """Colore les mots selon les couleurs du drapeau (positionnel si bandes)."""
    spec = FLAGS.get(slug)
    if not spec:
        return None
    cols, typ, n = spec["colors"], spec["type"], len(spec["colors"])
    if typ == "palette":
        state = {"i": 0}

        def cf(*a, **k):
            c = cols[state["i"] % n]
            state["i"] += 1
            return c
        return cf

    def cf(word, font_size=0, position=(0, 0), orientation=None, **k):
        y, x = position[0], position[1]   # wordcloud : position = (ligne, colonne)
        frac = (x / max(width, 1)) if typ == "vbands" else (y / max(height, 1))
        return cols[min(n - 1, max(0, int(frac * n)))]
    return cf


def add_word_outline(img, width=3, color=(255, 255, 255)):
    """Ajoute un liseré (sticker) autour de TOUS les mots. Blanc par défaut =
    look autocollant ; chaque mot ressort sur n'importe quel fond."""
    from PIL import ImageFilter
    alpha = img.split()[3]
    dil = alpha
    for _ in range(max(1, width)):
        dil = dil.filter(ImageFilter.MaxFilter(3))
    base = Image.new("RGBA", img.size, color + (0,))
    base.putalpha(dil)
    return Image.alpha_composite(base, img)


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


def make_cloud(freq, mask, font_path, color_func):
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
        color_func=color_func,
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
    ap.add_argument("--colors", default="rainbow",
                    help="rainbow | black | sunset/ocean/forest/candy | flag")
    ap.add_argument("--font-path", default="")
    ap.add_argument("--out", default="produits/word_shapes")
    ap.add_argument("--name", default="")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--contour", type=int, default=0,
                    help="épaisseur du contour blanc du pays (0 = aucun)")
    ap.add_argument("--word-outline", type=int, default=0,
                    help="liseré sticker autour des mots (0 = aucun)")
    ap.add_argument("--outline-color", default="#ffffff", help="couleur du liseré des mots")
    ap.add_argument("--contour-color", default="#ffffff", help="couleur du contour du pays")
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

    # masque + polygones (pays = silhouette réelle + contour possible)
    polys, csize, slug = None, 2000, ""
    if args.mask.lower().startswith("country:"):
        slug = args.mask.split(":", 1)[1].strip().lower().replace(" ", "_")
        mask, polys = country_data(slug, size=csize)
    else:
        mask = load_mask(args.mask)
    h, w = mask.shape[:2]

    # couleurs : flag (drapeau positionnel) | bw (noir & blanc) | palette/rainbow
    if args.colors == "flag":
        color_func = make_flag_color_func(slug, w, h)
        if color_func is None:
            print(f"[drapeau] inconnu pour '{slug}' — rainbow", file=sys.stderr)
            color_func = make_color_func("rainbow", list(freq.keys()))
    elif args.colors == "bw":
        def color_func(*a, **k):
            return (28, 28, 28)
    else:
        color_func = make_color_func(args.colors, list(freq.keys()))

    img = make_cloud(freq, mask, font, color_func)

    if args.word_outline > 0:
        img = add_word_outline(img, width=args.word_outline,
                               color=ImageColor.getrgb(args.outline_color))
    if args.contour > 0 and polys:
        contour = country_contour(polys, csize, width=args.contour,
                                  color=ImageColor.getrgb(args.contour_color) + (255,))
        img = Image.alpha_composite(contour, img)

    name = args.name or f"{(args.niche or 'mots').replace(' ', '_')}_{args.mask}_{args.colors}"
    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, f"{name}.png")
    img.save(out_path, dpi=(300, 300))
    print(f"{out_path}  ({img.width}x{img.height}, {len(freq)} mots)")

    if args.sheet:
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        # fond gris moyen si sticker/contour (voir blanc ET noir), clair sinon
        tone = (128, 130, 134) if (args.contour > 0 or args.colors in ("flag", "bw")) else (235, 235, 235)
        bg = Image.new("RGB", img.size, tone)
        bg.paste(img, (0, 0), img)
        bg.save(args.sheet, quality=90)
        print("aperçu:", args.sheet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
