#!/usr/bin/env python3
"""
gen_speak_to_me.py — collection « [verbe]-moi en [langue] » (FR + EN).

Le gag : un verbe (souvent rude, parfois tendre) + une langue réputée pour
sonner agressive ou romantique. La typo de la langue fait le clin d'œil
(allemand en bloc froid, italien en serif chic, russe en capitales rouges…).

Fond transparent, 4500 px. Extensible : ajoute un verbe ou une langue et relance.

Usage :
    python scripts/gen_speak_to_me.py --out produits/speak_to_me
    python scripts/gen_speak_to_me.py --sheet /tmp/speak.png
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402
from typo_variants import VARIANTS, adapt  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

GRAY = (120, 120, 126, 255)
PLUM = (120, 30, 110, 255)
WARM = (200, 70, 28, 255)
COLD = (32, 78, 168, 255)
GREEN = (38, 122, 58, 255)
RED = (190, 46, 38, 255)
ORANGE = (210, 110, 18, 255)
BLUE = (30, 90, 170, 255)
GOLD = (185, 140, 10, 255)
REDDARK = (150, 28, 42, 255)

# langue -> (police, couleur, label FR, label EN)
LANG = {
    "german":     ("block",    COLD,    "EN ALLEMAND",    "IN GERMAN"),
    "portuguese": ("elegant",  GREEN,   "EN PORTUGAIS",   "IN PORTUGUESE"),
    "italian":    ("elegant",  WARM,    "EN ITALIEN",     "IN ITALIAN"),
    "spanish":    ("fatserif", REDDARK, "EN ESPAGNOL",    "IN SPANISH"),
    "russian":    ("impact",   RED,     "EN RUSSE",       "IN RUSSIAN"),
    "dutch":      ("block",    ORANGE,  "EN NÉERLANDAIS", "IN DUTCH"),
    "greek":      ("elegant",  BLUE,    "EN GREC",        "IN GREEK"),
    "polish":     ("block",    REDDARK, "EN POLONAIS",    "IN POLISH"),
    "finnish":    ("cond",     COLD,    "EN FINNOIS",     "IN FINNISH"),
    "berber":     ("fatserif", WARM,    "EN BERBÈRE",     "IN BERBER"),
    "quebecois":  ("comic",    BLUE,    "EN QUÉBÉCOIS",   "IN QUEBECOIS"),
    "hungarian":  ("block",    GREEN,   "EN HONGROIS",    "IN HUNGARIAN"),
}

# (id, langue(fr/en), verbe, langue_id, ton)  ton: harsh | tender
COMBOS = [
    # ---- FR ----
    ("fr_brutalise_portugais",  "fr", "brutalise-moi",   "portuguese", "harsh"),
    ("fr_insulte_allemand",     "fr", "insulte-moi",     "german",     "harsh"),
    ("fr_engueule_italien",     "fr", "engueule-moi",    "italian",    "harsh"),
    ("fr_menace_neerlandais",   "fr", "menace-moi",      "dutch",      "harsh"),
    ("fr_humilie_russe",        "fr", "humilie-moi",     "russian",    "harsh"),
    ("fr_gronde_espagnol",      "fr", "gronde-moi",      "spanish",    "harsh"),
    ("fr_sermonne_grec",        "fr", "sermonne-moi",    "greek",      "harsh"),
    ("fr_intimide_polonais",    "fr", "intimide-moi",    "polish",     "harsh"),
    ("fr_rabaisse_hongrois",    "fr", "rabaisse-moi",    "hungarian",  "harsh"),
    ("fr_insulte_berbere",      "fr", "insulte-moi",     "berber",     "harsh"),
    ("fr_vexe_quebecois",       "fr", "vexe-moi",        "quebecois",  "harsh"),
    ("fr_caline_italien",       "fr", "câline-moi",      "italian",    "tender"),
    ("fr_susurre_portugais",    "fr", "susurre-moi",     "portuguese", "tender"),
    ("fr_complimente_finnois",  "fr", "complimente-moi", "finnish",    "tender"),
    # ---- EN ----
    ("en_brutalize_portuguese", "en", "brutalize me",    "portuguese", "harsh"),
    ("en_insult_german",        "en", "insult me",       "german",     "harsh"),
    ("en_yell_italian",         "en", "yell at me",      "italian",    "harsh"),
    ("en_threaten_dutch",       "en", "threaten me",     "dutch",      "harsh"),
    ("en_humiliate_russian",    "en", "humiliate me",    "russian",    "harsh"),
    ("en_scold_spanish",        "en", "scold me",        "spanish",    "harsh"),
    ("en_lecture_greek",        "en", "lecture me",      "greek",      "harsh"),
    ("en_intimidate_polish",    "en", "intimidate me",   "polish",     "harsh"),
    ("en_belittle_hungarian",   "en", "belittle me",     "hungarian",  "harsh"),
    ("en_insult_berber",        "en", "insult me",       "berber",     "harsh"),
    ("en_whisper_portuguese",   "en", "whisper to me",   "portuguese", "tender"),
    ("en_compliment_finnish",   "en", "compliment me",   "finnish",    "tender"),
]


def measure(font, text):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box[1]


def fit_size(text, key, max_w, hi=1000, lo=20):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if measure(load_font(key, mid), text)[0] <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


def render(verb, lang_id, lang, tone, variant="dark", side=4500, margin_ratio=0.09):
    margin = int(side * margin_ratio)
    max_w = side - 2 * margin
    big_font_key, big_color, label_fr, label_en = lang
    big = label_fr if lang_id == "fr" else label_en
    big_color = adapt(big_color, variant)

    big_sz = fit_size(big, big_font_key, max_w)
    f_big = load_font(big_font_key, big_sz)

    verb_key = "script" if tone == "tender" else "hand"
    verb_color = adapt(PLUM if tone == "tender" else GRAY, variant)
    verb_sz = max(40, int(big_sz * 0.42))
    while verb_sz > 30 and measure(load_font(verb_key, verb_sz), verb)[0] > max_w:
        verb_sz -= 6
    f_verb = load_font(verb_key, verb_sz)

    vw, vh, voff = measure(f_verb, verb)
    bw, bh, boff = measure(f_big, big)
    gap = int(big_sz * 0.20)
    total_h = vh + gap + bh
    img = Image.new("RGBA", (side, total_h + 2 * margin), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    y = margin
    d.text(((side - vw) // 2, y - voff), verb, font=f_verb, fill=verb_color)
    y += vh + gap
    d.text(((side - bw) // 2, y - boff), big, font=f_big, fill=big_color)

    bbox = img.getbbox()
    if bbox is None:
        return img
    img = img.crop(bbox)
    pad = int(side * 0.07)
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(img, (pad, pad))
    if max(out.size) != side:
        r = side / max(out.size)
        out = out.resize((round(out.width * r), round(out.height * r)), Image.LANCZOS)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="produits/speak_to_me")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--lang", default="", help="fr | en")
    ap.add_argument("--variant", default="both", choices=["both", "dark", "light"])
    args = ap.parse_args()

    sel = set(args.only.split(",")) if args.only else None
    items = [c for c in COMBOS
             if (not sel or c[0] in sel)
             and (not args.lang or c[1] == args.lang)]

    if args.sheet:
        cols = 4
        rows = (len(items) + cols - 1) // cols
        cell = 560
        sheet = Image.new("RGB", (cols * cell, rows * cell), (243, 243, 245))
        dd = ImageDraw.Draw(sheet)
        try:
            lab = load_font("fjalla", 17)
        except Exception:
            lab = ImageFont.load_default()
        for i, (cid, lc, verb, lid, tone) in enumerate(items):
            im = render(verb, lc, LANG[lid], tone, side=1400)
            im.thumbnail((cell - 30, cell - 54))
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 15, r * cell + 15))
            dd.text((c * cell + 15, r * cell + cell - 30), f"{verb} · {lid}",
                    fill=(70, 70, 70), font=lab)
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=90)
        print(f"planche: {args.sheet} ({len(items)})")
        return

    variants = list(VARIANTS) if args.variant == "both" else [args.variant]
    os.makedirs(args.out, exist_ok=True)
    n = 0
    for cid, lc, verb, lid, tone in items:
        for v in variants:
            im = render(verb, lc, LANG[lid], tone, variant=v)
            im.save(os.path.join(args.out, f"{cid}__{v}.png"), dpi=(300, 300))
            n += 1
    print(f"{n} fichiers ({len(items)} × {len(variants)} variantes) → {args.out}")


if __name__ == "__main__":
    main()
