#!/usr/bin/env python3
"""
gen_absurd_phrases.py — designs typographiques pour les phrases absurdes.

Chaque phrase reçoit un traitement où la TYPO fait un clin d'œil au sujet :
fromage/raclette en script coulant, langues « rigides » en bloc, mots tendres
en manuscrit. Polices réelles d'assets/fonts (Anton, Bebas, Playfair, Pacifico…).

Fond transparent, 4500 px de côté long, prêt pour POD.

Usage :
    python scripts/gen_absurd_phrases.py --out produits/phrases_absurdes
    python scripts/gen_absurd_phrases.py --sheet /tmp/phrases_sheet.png
    python scripts/gen_absurd_phrases.py --only du_saucisson_et_la_paix
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402
from typo_variants import VARIANTS, adapt  # noqa: E402
from typo_ornaments import apply_ornament  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402


def measure(font, text):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box[1]


def fit_font_size(text, key, max_w, hi=1000, lo=20):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        w, _, _ = measure(load_font(key, mid), text)
        if w <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


# --- palette — noir et rouge uniquement ----------------------------------
DARK = (24, 24, 28, 255)
RED  = (201, 162, 39, 255)
GRAY = (120, 120, 124, 255)
# anciens alias → remappés vers le duo noir/rouge
WARM = RED
COLD = DARK
GOLD = RED
GREEN = RED
PLUM = RED

# Chaque phrase : lignes (texte, font_key, couleur, scale).
# scale = taille relative à la ligne de référence (scale 1.0).
PHRASES = [
    # ---------------------------------------------------------------- FR
    {"id": "du_saucisson_et_la_paix", "lang": "fr", "lines": [
        ("DU SAUCISSON", "script", WARM, 1.0),
        ("et la paix", "script", DARK, 0.55)]},

    {"id": "insulte_moi_en_allemand", "lang": "fr", "lines": [
        ("insulte-moi", "script", GRAY, 0.55),
        ("EN ALLEMAND", "script", COLD, 1.0)]},

    {"id": "insulte_moi_en_berbere", "lang": "fr", "lines": [
        ("insulte-moi", "script", GRAY, 0.55),
        ("EN BERBÈRE", "script", WARM, 1.0)]},

    {"id": "plus_de_fromage_moins_de_problemes", "lang": "fr", "lines": [
        ("plus de", "script", GRAY, 0.42),
        ("FROMAGE", "script", GOLD, 1.0),
        ("moins de problèmes", "script", DARK, 0.34)]},

    {"id": "du_pate_et_de_lespoir", "lang": "fr", "lines": [
        ("DU PÂTÉ", "script", WARM, 1.0),
        ("et de l'espoir", "script", GRAY, 0.50)]},

    {"id": "caline_moi_en_italien", "lang": "fr", "lines": [
        ("câline-moi", "script", PLUM, 0.62),
        ("EN ITALIEN", "script", DARK, 1.0)]},

    {"id": "moins_de_lundi_plus_de_raclette", "lang": "fr", "lines": [
        ("MOINS DE LUNDI", "script", COLD, 0.52),
        ("plus de", "script", GRAY, 0.40),
        ("raclette", "script", GOLD, 1.0)]},

    {"id": "parle_moi_en_klingon", "lang": "fr", "lines": [
        ("parle-moi", "script", GRAY, 0.50),
        ("EN KLINGON", "script", COLD, 1.0)]},

    {"id": "du_vin_et_du_silence", "lang": "fr", "lines": [
        ("DU VIN", "script", WARM, 1.0),
        ("et du silence", "script", GRAY, 0.46)]},

    {"id": "chuchote_moi_du_gruyere", "lang": "fr", "lines": [
        ("chuchote-moi", "script", GRAY, 0.48),
        ("DU GRUYÈRE", "script", GOLD, 1.0)]},

    {"id": "du_jambon_et_de_la_tendresse", "lang": "fr", "lines": [
        ("DU JAMBON", "script", WARM, 1.0),
        ("et de la tendresse", "script", PLUM, 0.40)]},

    {"id": "menace_moi_en_portugais", "lang": "fr", "lines": [
        ("MENACE-MOI", "script", DARK, 0.66),
        ("EN PORTUGAIS", "script", GREEN, 1.0)]},

    # ---------------------------------------------------------------- EN
    {"id": "insult_me_in_german", "lang": "en", "lines": [
        ("insult me", "script", GRAY, 0.55),
        ("IN GERMAN", "script", COLD, 1.0)]},

    {"id": "insult_me_in_berber", "lang": "en", "lines": [
        ("insult me", "script", GRAY, 0.55),
        ("IN BERBER", "script", WARM, 1.0)]},

    {"id": "sausage_and_peace", "lang": "en", "lines": [
        ("SAUSAGE", "script", WARM, 1.0),
        ("and peace", "script", DARK, 0.55)]},

    {"id": "more_cheese_less_problems", "lang": "en", "lines": [
        ("more", "script", GRAY, 0.42),
        ("CHEESE", "script", GOLD, 1.0),
        ("less problems", "script", DARK, 0.34)]},

    {"id": "whisper_to_me_in_klingon", "lang": "en", "lines": [
        ("whisper to me", "script", GRAY, 0.46),
        ("IN KLINGON", "script", COLD, 1.0)]},

    {"id": "bread_and_revenge", "lang": "en", "lines": [
        ("BREAD", "script", GOLD, 1.0),
        ("and revenge", "script", DARK, 0.50)]},

    {"id": "less_monday_more_raclette", "lang": "en", "lines": [
        ("LESS MONDAY", "script", COLD, 0.52),
        ("more", "script", GRAY, 0.40),
        ("raclette", "script", GOLD, 1.0)]},

    {"id": "threaten_me_in_portuguese", "lang": "en", "lines": [
        ("THREATEN ME", "script", DARK, 0.62),
        ("IN PORTUGUESE", "script", GREEN, 1.0)]},

    {"id": "ham_and_tenderness", "lang": "en", "lines": [
        ("HAM", "script", WARM, 1.0),
        ("and tenderness", "script", PLUM, 0.42)]},

    {"id": "compliment_me_in_finnish", "lang": "en", "lines": [
        ("compliment me", "script", GRAY, 0.46),
        ("IN FINNISH", "script", COLD, 1.0)]},

    # --- localisé US/UK ---
    {"id": "bacon_and_hope", "lang": "en", "lines": [
        ("BACON", "script", WARM, 1.0),
        ("and hope", "script", GRAY, 0.50)]},
    {"id": "more_coffee_less_monday", "lang": "en", "lines": [
        ("more", "script", GRAY, 0.40),
        ("COFFEE", "script", (90, 60, 40, 255), 1.0),
        ("less monday", "script", COLD, 0.40)]},
    {"id": "donuts_and_destiny", "lang": "en", "lines": [
        ("DONUTS", "script", PLUM, 1.0),
        ("and destiny", "script", GRAY, 0.42)]},
    {"id": "tea_and_spite_uk", "lang": "en", "lines": [
        ("TEA", "script", (110, 70, 40, 255), 1.0),
        ("and spite", "script", GRAY, 0.55)]},
    {"id": "beans_on_toast_tolerance_uk", "lang": "en", "lines": [
        ("BEANS ON TOAST", "script", GOLD, 0.78),
        ("and tolerance", "script", GRAY, 0.40)]},

    # --- localisé DE (allemand) ---
    {"id": "mehr_bier_weniger_probleme", "lang": "de", "lines": [
        ("mehr", "script", GRAY, 0.40),
        ("BIER", "script", GOLD, 1.0),
        ("weniger probleme", "script", DARK, 0.42)]},
    {"id": "wurst_und_frieden", "lang": "de", "lines": [
        ("WURST", "script", WARM, 1.0),
        ("und frieden", "script", GRAY, 0.48)]},
    {"id": "brot_und_rache", "lang": "de", "lines": [
        ("BROT", "script", GOLD, 1.0),
        ("und rache", "script", DARK, 0.46)]},
    {"id": "kaese_und_hoffnung", "lang": "de", "lines": [
        ("KÄSE", "script", GOLD, 1.0),
        ("und hoffnung", "script", GRAY, 0.48)]},
    {"id": "beleidige_mich_bayerisch", "lang": "de", "lines": [
        ("beleidige mich", "script", GRAY, 0.45),
        ("AUF BAYERISCH", "script", COLD, 1.0)]},
]


def render_phrase(ph, variant="dark", side=4500, margin_ratio=0.08):
    margin = int(side * margin_ratio)
    max_w = side - 2 * margin
    lines = ph["lines"]

    ref = next((l for l in lines if abs(l[3] - 1.0) < 0.01), lines[0])
    ref_size = fit_font_size(ref[0], ref[1], max_w)

    rendered = []
    for txt, key, color, scale in lines:
        sz = max(24, int(ref_size * scale))
        # garde-fou : la ligne ne doit jamais déborder
        while sz > 24 and measure(load_font(key, sz), txt)[0] > max_w:
            sz -= 6
        f = load_font(key, sz)
        w, h, off = measure(f, txt)
        rendered.append((txt, f, adapt(color, variant), w, h, off))

    gap = int(ref_size * 0.14)
    total_h = sum(r[4] for r in rendered) + gap * (len(rendered) - 1)
    img = Image.new("RGBA", (side, total_h + 2 * margin), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    y = margin
    for txt, f, color, w, h, off in rendered:
        d.text(((side - w) // 2, y - off), txt, font=f, fill=color)
        y += h + gap

    # étoiles 4 branches or/noir autour du bloc
    block_w = max(r[3] for r in rendered)
    tb = ((side - block_w) // 2, margin, (side + block_w) // 2, margin + total_h)
    apply_ornament(d, "sparkles", tb, adapt(DARK, variant), adapt(RED, variant),
                   scale=side / 4500.0)

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
    ap.add_argument("--only", default="")
    ap.add_argument("--lang", default="")
    ap.add_argument("--variant", default="both", choices=["both", "dark", "light"])
    args = ap.parse_args()

    sel = set(args.only.split(",")) if args.only else None
    items = [p for p in PHRASES
             if (not sel or p["id"] in sel)
             and (not args.lang or p["lang"] == args.lang)]

    if args.sheet:
        cols = 3
        rows = (len(items) + cols - 1) // cols
        cell = 580
        sheet = Image.new("RGB", (cols * cell, rows * cell), (242, 242, 242))
        dd = ImageDraw.Draw(sheet)
        try:
            lab = load_font("fjalla", 22)
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
                    ph["id"][:32], fill=(60, 60, 60), font=lab)
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=90)
        print(f"planche: {args.sheet} ({len(items)} phrases)")
        return

    variants = list(VARIANTS) if args.variant == "both" else [args.variant]
    os.makedirs(args.out, exist_ok=True)
    n = 0
    for ph in items:
        for v in variants:
            im = render_phrase(ph, variant=v)
            im.save(os.path.join(args.out, f"{ph['id']}__{ph['lang']}__{v}.png"),
                    dpi=(300, 300))
            n += 1
    print(f"{n} fichiers ({len(items)} × {len(variants)} variantes) → {args.out}")


if __name__ == "__main__":
    main()
