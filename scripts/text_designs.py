#!/usr/bin/env python3
"""
text_designs.py — designs typographiques POD SANS génération d'image (0 €).

Rendu pur Pillow : une phrase forte + une typo propre, fond transparent, haute
résolution prête à l'upload (côté long ~4500 px, 300 DPI). Deux variantes par
phrase : encre sombre (t-shirts clairs) et encre blanche (t-shirts foncés).

Trois familles de produits :
  - mots « intraduisibles » devenus cultes dans une langue (TSUNDOKU, SOBREMESA,
    FIKA…) avec une définition en sous-titre — niche connue, zéro IA ;
  - phrases virales d'une langue vendues telles quelles ailleurs
    (« JE PEUX PAS J'AI PONEY »…) ;
  - humour universel (overthinker, paresse) et série « I ♥ … ».

Aucune marque déposée, aucune parole de chanson/film : uniquement des tournures
idiomatiques folkloriques, des mots de dictionnaire et de l'humour générique.

Usage :
    python scripts/text_designs.py --out produits/typographies
    python scripts/text_designs.py --sheet /tmp/sheet.png       # planche-contact
    python scripts/text_designs.py --only tsundoku,je_peux_pas   # sous-ensemble
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font as _roster_font  # noqa: E402

from PIL import Image, ImageDraw, ImageFont

# styles historiques -> clés du roster typo_fonts (vraies polices, fini DejaVu)
STYLE_MAP = {
    "display": "impact",       # Anton, punchy
    "serif": "elegant",        # Playfair, chic
    "serif_italic": "fatserif",  # Abril Fatface, display serif
    "sans": "block",           # Archivo Black
    "sans_light": "geo",       # Poppins, sous-titres propres
    "mono": "mono",            # Space Mono
}

# --- polices : on prend la 1re existante de chaque liste de candidats ----------
FONT_CANDIDATES = {
    "display": [  # sans condensé/punchy (idéal : Anton/Oswald, ajoutés en CI)
        "/usr/share/fonts/truetype/anton/Anton-Regular.ttf",
        "/usr/share/fonts/truetype/oswald/Oswald-Bold.ttf",
        "assets/fonts/Anton-Regular.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ],
    "sans": [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ],
    "sans_light": [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ],
    "serif": [
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerifBold.ttf",
    ],
    "serif_italic": [
        "/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSerifItalic.ttf",
    ],
    "mono": [
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationMono-Bold.ttf",
    ],
}


def font_path(style):
    for p in FONT_CANDIDATES.get(style, []):
        if os.path.exists(p):
            return p
    return FONT_CANDIDATES["sans"][1]  # DejaVu Bold : toujours présent


def load(style, size):
    return _roster_font(STYLE_MAP.get(style, "block"), size)


INK_DARK = (26, 26, 28)
INK_LIGHT = (245, 245, 245)
HEART_RED = (214, 40, 57)

# --- catalogue de phrases ------------------------------------------------------
# champs : id, lines (liste), sub (sous-titre/définition), style, accent (couleur
# d'un mot mis en valeur, optionnel), heart (place un ♥ là où le token "<3"
# apparaît dans les lignes), cat, fr (titre, description, mots_cles communs).
P = []


def add(**k):
    P.append(k)


# 1) Mots intraduisibles cultes -------------------------------------------------
add(id="tsundoku", lines=["TSUNDOKU"], sub="(jp) buying books and letting them pile up, unread",
    style="serif", cat="intraduisibles")
add(id="sobremesa", lines=["SOBREMESA"], sub="(es) the lazy table talk long after the meal is over",
    style="serif", cat="intraduisibles")
add(id="fika", lines=["FIKA"], sub="(sv) to slow down for coffee, cake and good company",
    style="serif", cat="intraduisibles")
add(id="gezellig", lines=["GEZELLIG"], sub="(nl) warm, cozy togetherness that feels like home",
    style="serif", cat="intraduisibles")
add(id="kummerspeck", lines=["KUMMERSPECK"], sub="(de) “grief bacon” : the weight gained from comfort eating",
    style="serif", cat="intraduisibles")
add(id="saudade", lines=["SAUDADE"], sub="(pt) a sweet, aching longing for what is gone",
    style="serif_italic", cat="intraduisibles")
add(id="hygge", lines=["HYGGE"], sub="(dk) the art of cozy contentment in small moments",
    style="serif", cat="intraduisibles")

# 2) Phrases FR virales (vendues à l'international) ------------------------------
add(id="je_peux_pas_poney", lines=["JE PEUX PAS", "J'AI PONEY"], style="display", cat="phrases_fr")
add(id="oh_puree", lines=["OH PURÉE"], sub="french for “oh dear…”", style="display", cat="phrases_fr")
add(id="apero_oclock", lines=["APÉRO", "O'CLOCK"], style="display", cat="phrases_fr")
add(id="cest_la_vie", lines=["C'EST", "LA VIE"], style="serif_italic", cat="phrases_fr")

# 3) Humour universel -----------------------------------------------------------
add(id="overthink", lines=["LET ME", "OVERTHINK", "THIS"], style="display", cat="humour")
add(id="hold_my_beer", lines=["HOLD", "MY BEER"], style="display", cat="humour")
add(id="pro_overthinker", lines=["PROFESSIONAL", "OVERTHINKER"], style="display", cat="humour")
add(id="cardio", lines=["RUNNING LATE", "IS MY CARDIO"], style="display", cat="humour")
add(id="nope_today", lines=["NOPE.", "NOT TODAY."], style="display", cat="humour")
add(id="introvert_dogs", lines=["INTROVERTED", "BUT WILLING TO", "DISCUSS DOGS"], style="sans", cat="humour")

# 4) Série « I ♥ … » ------------------------------------------------------------
add(id="i_love_naps", lines=["I <3", "NAPS"], heart=True, style="display", cat="i_love")
add(id="i_love_dog", lines=["I <3", "MY DOG"], heart=True, style="display", cat="i_love")
add(id="i_love_overthinking", lines=["I <3", "OVERTHINKING"], heart=True, style="display", cat="i_love")


def heart_polygon(cx, cy, s):
    """Cœur paramétrique propre et recolorable (pas de police emoji)."""
    pts = []
    for i in range(0, 361, 6):
        t = math.radians(i)
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s / 32, cy - y * s / 32))
    return pts


def measure(font, text):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box[1]


def fit_size(style, lines, max_w, hi=900, lo=40):
    """Plus grande taille de police où chaque ligne tient dans max_w."""
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load(style, mid)
        widths = []
        for ln in lines:
            txt = ln.replace("<3", "♥")
            widths.append(measure(f, txt)[0])
        if max(widths) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


def render(ph, ink, side=4500, margin_ratio=0.08):
    margin = int(side * margin_ratio)
    max_w = side - 2 * margin
    lines = ph["lines"]
    style = ph.get("style", "display")
    size = fit_size(style, lines, max_w)
    f = load(style, size)
    line_gap = int(size * 0.18)

    # hauteurs ligne par ligne
    dims = []
    for ln in lines:
        txt = ln.replace("<3", "♥")
        w, h, off = measure(f, txt)
        dims.append((txt, w, h, off))
    total_h = sum(d[2] for d in dims) + line_gap * (len(dims) - 1)

    sub = ph.get("sub")
    sub_font = None
    if sub:
        # le sous-titre ne doit jamais être plus large que le bloc titre ni que
        # la zone utile : on part de 16 % du titre puis on réduit pour tenir.
        widest = max(measure(f, d[0])[0] for d in dims)
        limit = min(widest, max_w)
        ss = max(int(size * 0.16), 60)
        while ss > 24 and measure(load("sans_light", ss), sub)[0] > limit:
            ss -= 4
        sub_font = load("sans_light", ss)
    sub_gap = int(size * 0.22) if sub else 0
    sub_h = measure(sub_font, sub)[1] if sub else 0

    canvas_h = total_h + sub_gap + sub_h + 2 * margin
    img = Image.new("RGBA", (side, canvas_h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    y = margin
    for (txt, w, h, off) in dims:
        x = (side - w) // 2
        if "♥" in txt and ph.get("heart"):
            # remplace ♥ par un cœur dessiné rouge, le reste en encre
            before, after = txt.split("♥", 1)
            wb = measure(f, before)[0]
            wa = measure(f, after)[0]
            hs = int(h * 0.92)
            total = wb + hs + wa
            x = (side - total) // 2
            d.text((x, y - off), before, font=f, fill=ink)
            d.polygon(heart_polygon(x + wb + hs / 2, y + h / 2, hs), fill=HEART_RED)
            d.text((x + wb + hs, y - off), after, font=f, fill=ink)
        else:
            d.text((x, y - off), txt, font=f, fill=ink)
        y += h + line_gap

    if sub:
        y += sub_gap - line_gap
        sw, sh, soff = measure(sub_font, sub)
        d.text(((side - sw) // 2, y - soff), sub, font=sub_font, fill=ink)

    # recadrage serré + marge homogène, côté long ramené à `side`
    bbox = img.getbbox()
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
    ap.add_argument("--out", default="")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    sel = set(args.only.split(",")) if args.only else None
    items = [p for p in P if not sel or p["id"] in sel]

    if args.sheet:
        cols = 3
        rows = (len(items) + cols - 1) // cols
        cell = 520
        sheet = Image.new("RGB", (cols * cell, rows * cell), (238, 238, 238))
        dd = ImageDraw.Draw(sheet)
        lab = load("sans", 22)
        for i, ph in enumerate(items):
            im = render(ph, INK_DARK, side=1400)
            im.thumbnail((cell - 30, cell - 70))
            bg = Image.new("RGB", im.size, (245, 245, 245)); bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 15, r * cell + 15))
            dd.text((c * cell + 15, r * cell + cell - 34), ph["id"], fill=(20, 20, 20), font=lab)
        sheet.save(args.sheet, quality=90)
        print("planche:", args.sheet, "(", len(items), "designs )")
        return

    if args.out:
        n = 0
        for ph in items:
            d = os.path.join(args.out, ph["cat"])
            os.makedirs(d, exist_ok=True)
            for var, ink in (("dark", INK_DARK), ("light", INK_LIGHT)):
                out = render(ph, ink)
                out.save(os.path.join(d, f"{ph['id']}__{var}.png"), dpi=(300, 300))
                n += 1
        print(f"{n} fichiers ({len(items)} phrases x 2 variantes) -> {args.out}")
        return

    print(f"{len(P)} phrases au catalogue. --sheet pour la planche, --out pour produire.")


if __name__ == "__main__":
    main()
