#!/usr/bin/env python3
"""
gen_absurd_phrases.py — designs typographiques pour les phrases absurdes.

Chaque phrase reçoit un traitement visuel qui fait écho à son sujet :
- mots-clés grossis, stylisés ou colorés selon leur sens
- fond blanc, encre sombre ou colorée, 4500×4500 px
- transparent (RGBA) prêt pour impression POD

Usage :
    python scripts/gen_absurd_phrases.py --out produits/phrases_absurdes
    python scripts/gen_absurd_phrases.py --sheet /tmp/phrases_sheet.png
    python scripts/gen_absurd_phrases.py --only du_saucisson
"""
import argparse
import json
import math
import os
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONT_CANDIDATES = {
    "display": [
        "assets/fonts/Anton-Regular.ttf",
        "/usr/share/fonts/truetype/anton/Anton-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ],
    "mono": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    ],
    "serif": [
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
    ],
    "light": [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
}


def font_path(style):
    for p in FONT_CANDIDATES.get(style, FONT_CANDIDATES["display"]):
        if os.path.exists(p):
            return p
    return FONT_CANDIDATES["display"][-1]


def load(style, size):
    return ImageFont.truetype(font_path(style), size)


def measure(font, text):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box[1]


def fit_font_size(text, style, max_w, hi=900, lo=20):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        w, _, _ = measure(load(style, mid), text)
        if w <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


# ---------------------------------------------------------------------------
# Définition des phrases et de leur traitement visuel
# ---------------------------------------------------------------------------
# Chaque entrée :
#   id       : slug (nom du fichier)
#   lang     : fr / en
#   segments : liste de (texte, style, color, scale)
#              scale = multiplicateur de taille relative au token de référence
#              color = couleur RGBA (ou None = encre principale)
#   layout   : "stack" (une ligne par segment) | "flow" (mots sur 1-3 lignes auto)
# ---------------------------------------------------------------------------

DARK = (22, 22, 26, 255)
WARM = (210, 80, 30, 255)
COLD = (30, 80, 180, 255)
GOLD = (200, 155, 10, 255)
GRAY = (120, 120, 120, 255)
GREEN = (40, 130, 60, 255)
CREAM = (240, 230, 200, 255)

PHRASES = [
    # --- FR ---
    {
        "id": "du_saucisson_et_la_paix",
        "lang": "fr",
        "lines": [
            ("DU SAUCISSON", "display", DARK, 1.0),
            ("ET LA PAIX", "serif", GRAY, 0.65),
        ],
    },
    {
        "id": "insulte_moi_en_allemand",
        "lang": "fr",
        "lines": [
            ("INSULTE-MOI", "light", DARK, 0.55),
            ("EN ALLEMAND", "display", COLD, 1.0),
        ],
    },
    {
        "id": "insulte_moi_en_berbere",
        "lang": "fr",
        "lines": [
            ("INSULTE-MOI", "light", DARK, 0.55),
            ("EN BERBÈRE", "display", WARM, 1.0),
        ],
    },
    {
        "id": "plus_de_fromage_moins_de_problemes",
        "lang": "fr",
        "lines": [
            ("PLUS DE", "light", GRAY, 0.40),
            ("FROMAGE", "display", GOLD, 1.0),
            ("MOINS DE", "light", GRAY, 0.40),
            ("PROBLÈMES", "mono", DARK, 0.55),
        ],
    },
    {
        "id": "du_pate_et_de_lespoir",
        "lang": "fr",
        "lines": [
            ("DU PÂTÉ", "display", WARM, 1.0),
            ("ET DE L'ESPOIR", "serif", GRAY, 0.50),
        ],
    },
    {
        "id": "caline_moi_en_italien",
        "lang": "fr",
        "lines": [
            ("CÂLINE-MOI", "serif", DARK, 0.60),
            ("EN ITALIEN", "display", WARM, 1.0),
        ],
    },
    {
        "id": "moins_de_lundi_plus_de_raclette",
        "lang": "fr",
        "lines": [
            ("MOINS DE", "light", GRAY, 0.35),
            ("LUNDI", "mono", COLD, 0.70),
            ("PLUS DE", "light", GRAY, 0.35),
            ("RACLETTE", "display", GOLD, 1.0),
        ],
    },
    {
        "id": "parle_moi_en_klingon",
        "lang": "fr",
        "lines": [
            ("PARLE-MOI", "light", DARK, 0.50),
            ("EN KLINGON", "display", COLD, 1.0),
        ],
    },
    {
        "id": "du_vin_et_du_silence",
        "lang": "fr",
        "lines": [
            ("DU VIN", "display", WARM, 1.0),
            ("ET DU SILENCE", "light", GRAY, 0.42),
        ],
    },
    {
        "id": "chuchote_moi_du_gruyere",
        "lang": "fr",
        "lines": [
            ("CHUCHOTE-MOI", "light", GRAY, 0.45),
            ("DU GRUYÈRE", "display", GOLD, 1.0),
        ],
    },
    {
        "id": "du_jambon_et_de_la_tendresse",
        "lang": "fr",
        "lines": [
            ("DU JAMBON", "display", WARM, 1.0),
            ("ET DE LA TENDRESSE", "serif", GRAY, 0.42),
        ],
    },
    {
        "id": "menace_moi_en_portugais",
        "lang": "fr",
        "lines": [
            ("MENACE-MOI", "display", DARK, 0.75),
            ("EN PORTUGAIS", "display", GREEN, 1.0),
        ],
    },
    # --- EN ---
    {
        "id": "insult_me_in_german",
        "lang": "en",
        "lines": [
            ("INSULT ME", "light", DARK, 0.55),
            ("IN GERMAN", "display", COLD, 1.0),
        ],
    },
    {
        "id": "insult_me_in_berber",
        "lang": "en",
        "lines": [
            ("INSULT ME", "light", DARK, 0.55),
            ("IN BERBER", "display", WARM, 1.0),
        ],
    },
    {
        "id": "sausage_and_peace",
        "lang": "en",
        "lines": [
            ("SAUSAGE", "display", DARK, 1.0),
            ("AND PEACE", "serif", GRAY, 0.60),
        ],
    },
    {
        "id": "more_cheese_less_problems",
        "lang": "en",
        "lines": [
            ("MORE", "light", GRAY, 0.38),
            ("CHEESE", "display", GOLD, 1.0),
            ("LESS", "light", GRAY, 0.38),
            ("PROBLEMS", "mono", DARK, 0.55),
        ],
    },
    {
        "id": "whisper_to_me_in_klingon",
        "lang": "en",
        "lines": [
            ("WHISPER TO ME", "light", GRAY, 0.42),
            ("IN KLINGON", "display", COLD, 1.0),
        ],
    },
    {
        "id": "bread_and_revenge",
        "lang": "en",
        "lines": [
            ("BREAD", "display", GOLD, 1.0),
            ("AND REVENGE", "display", DARK, 0.55),
        ],
    },
    {
        "id": "less_monday_more_raclette",
        "lang": "en",
        "lines": [
            ("LESS MONDAY", "mono", COLD, 0.65),
            ("MORE RACLETTE", "display", GOLD, 1.0),
        ],
    },
    {
        "id": "threaten_me_in_portuguese",
        "lang": "en",
        "lines": [
            ("THREATEN ME", "display", DARK, 0.70),
            ("IN PORTUGUESE", "display", GREEN, 1.0),
        ],
    },
    {
        "id": "ham_and_tenderness",
        "lang": "en",
        "lines": [
            ("HAM", "display", WARM, 1.0),
            ("AND TENDERNESS", "serif", GRAY, 0.50),
        ],
    },
    {
        "id": "compliment_me_in_finnish",
        "lang": "en",
        "lines": [
            ("COMPLIMENT ME", "light", GRAY, 0.45),
            ("IN FINNISH", "display", COLD, 1.0),
        ],
    },
]


def render_phrase(ph, side=4500, margin_ratio=0.08):
    margin = int(side * margin_ratio)
    max_w = side - 2 * margin
    lines = ph["lines"]

    # Taille de référence : la ligne avec scale=1.0 remplit max_w
    ref_lines = [(txt, style) for txt, style, color, scale in lines if abs(scale - 1.0) < 0.01]
    if not ref_lines:
        ref_lines = [(lines[0][0], lines[0][1])]
    ref_txt, ref_style = ref_lines[0]
    ref_size = fit_font_size(ref_txt, ref_style, max_w)

    # Calcul des dimensions par ligne
    rendered = []
    for txt, style, color, scale in lines:
        sz = max(20, int(ref_size * scale))
        f = load(style, sz)
        w, h, off = measure(f, txt)
        rendered.append((txt, f, color, w, h, off))

    gap = int(ref_size * 0.12)
    total_h = sum(h for _, _, _, _, h, _ in rendered) + gap * (len(rendered) - 1)
    canvas_h = total_h + 2 * margin

    img = Image.new("RGBA", (side, canvas_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    y = margin
    for txt, f, color, w, h, off in rendered:
        x = (side - w) // 2
        d.text((x, y - off), txt, font=f, fill=color)
        y += h + gap

    # recadrage serré + marge homogène, côté long → side
    bbox = img.getbbox()
    if bbox is None:
        return img
    img = img.crop(bbox)
    pad = int(side * 0.06)
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(img, (pad, pad))
    if max(out.size) != side:
        r = side / max(out.size)
        out = out.resize((round(out.width * r), round(out.height * r)), Image.LANCZOS)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="produits/phrases_absurdes")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--only", default="", help="liste d'ids séparés par des virgules")
    ap.add_argument("--lang", default="", help="fr | en | '' (tous)")
    args = ap.parse_args()

    sel = set(args.only.split(",")) if args.only else None
    items = [p for p in PHRASES
             if (not sel or p["id"] in sel)
             and (not args.lang or p["lang"] == args.lang)]

    if args.sheet:
        cols = 3
        rows = (len(items) + cols - 1) // cols
        cell = 560
        sheet = Image.new("RGB", (cols * cell, rows * cell), (240, 240, 240))
        dd = ImageDraw.Draw(sheet)
        try:
            lab = ImageFont.truetype(font_path("light"), 20)
        except Exception:
            lab = ImageFont.load_default()
        for i, ph in enumerate(items):
            im = render_phrase(ph, side=1400)
            im.thumbnail((cell - 30, cell - 60))
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 15, r * cell + 15))
            dd.text((c * cell + 15, r * cell + cell - 38),
                    ph["id"][:30], fill=(60, 60, 60), font=lab)
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=90)
        print(f"planche: {args.sheet} ({len(items)} phrases)")
        return

    os.makedirs(args.out, exist_ok=True)
    n = 0
    for ph in items:
        im = render_phrase(ph)
        out_path = os.path.join(args.out, f"{ph['id']}__{ph['lang']}.png")
        im.save(out_path, dpi=(300, 300))
        print(f"  {out_path}  ({im.width}×{im.height})")
        n += 1
    print(f"\n{n} fichiers → {args.out}")


if __name__ == "__main__":
    main()
