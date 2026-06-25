#!/usr/bin/env python3
"""
gen_geek_phrases.py — séries « fan/geek » au traitement typographique malin.

Clin d'œil codeur : police mono, espaces remplacés par des underscores, prompt
« > » et curseur bloc « ▮ ». Idéal pour les niches de fans (langues fictives,
binaire…). Fond transparent, 4500 px, prêt POD.

Usage :
    python scripts/gen_geek_phrases.py --out produits/geek_phrases
    python scripts/gen_geek_phrases.py --sheet /tmp/geek_sheet.png
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402
from typo_variants import VARIANTS, adapt  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

INK = (28, 30, 34, 255)
GRAY = (130, 132, 138, 255)
RED = (190, 46, 38, 255)
TERM = RED
CYAN = RED
AMBER = RED
MAGENTA = RED

# prompt : ligne grise « > verbe_moi », puis grande ligne « EN_LANGUE▮ »
PHRASES = [
    {"id": "insulte_moi_en_klingon", "lang": "fr",
     "small": "> insulte_moi", "big": "EN_KLINGON", "accent": TERM},
    {"id": "susurre_moi_en_elfique", "lang": "fr",
     "small": "> susurre_moi", "big": "EN_ELFIQUE", "accent": CYAN},
    {"id": "menace_moi_en_dothraki", "lang": "fr",
     "small": "> menace_moi", "big": "EN_DOTHRAKI", "accent": AMBER},
    {"id": "chuchote_moi_en_fourchelangue", "lang": "fr",
     "small": "> chuchote_moi", "big": "EN_FOURCHELANGUE", "accent": TERM},
    {"id": "complimente_moi_en_valyrien", "lang": "fr",
     "small": "> complimente_moi", "big": "EN_VALYRIEN", "accent": MAGENTA},
    {"id": "parle_moi_en_binaire", "lang": "fr",
     "small": "> parle_moi", "big": "EN_BINAIRE", "accent": TERM,
     "footer": "01001100 01001111 01010110 01000101"},

    {"id": "insult_me_in_klingon", "lang": "en",
     "small": "> insult_me", "big": "IN_KLINGON", "accent": TERM},
    {"id": "whisper_to_me_in_elvish", "lang": "en",
     "small": "> whisper_to_me", "big": "IN_ELVISH", "accent": CYAN},
    {"id": "threaten_me_in_dothraki", "lang": "en",
     "small": "> threaten_me", "big": "IN_DOTHRAKI", "accent": AMBER},
    {"id": "compliment_me_in_valyrian", "lang": "en",
     "small": "> compliment_me", "big": "IN_VALYRIAN", "accent": MAGENTA},
    {"id": "talk_to_me_in_binary", "lang": "en",
     "small": "> talk_to_me", "big": "IN_BINARY", "accent": TERM,
     "footer": "01001100 01001111 01010110 01000101"},

    # ---- DE (allemand) ----
    {"id": "beleidige_mich_klingonisch", "lang": "de",
     "small": "> beleidige_mich", "big": "AUF_KLINGONISCH", "accent": TERM},
    {"id": "fluester_mir_elbisch", "lang": "de",
     "small": "> fluester_mir", "big": "AUF_ELBISCH", "accent": CYAN},
    {"id": "rede_mit_mir_binaer", "lang": "de",
     "small": "> rede_mit_mir", "big": "AUF_BINÄR", "accent": TERM,
     "footer": "01001100 01001001 01000101 01000010 01000101"},

    # ---- ES (espagnol) ----
    {"id": "insultame_en_klingon", "lang": "es",
     "small": "> insultame", "big": "EN_KLINGON", "accent": TERM},
    {"id": "susurrame_en_elfico", "lang": "es",
     "small": "> susurrame", "big": "EN_ELFICO", "accent": CYAN},
    {"id": "hablame_en_binario", "lang": "es",
     "small": "> hablame", "big": "EN_BINARIO", "accent": TERM,
     "footer": "01000001 01001101 01001111 01010010"},

    # ---- IT (italien) ----
    {"id": "insultami_in_klingon", "lang": "it",
     "small": "> insultami", "big": "IN_KLINGON", "accent": TERM},
    {"id": "sussurrami_in_elfico", "lang": "it",
     "small": "> sussurrami", "big": "IN_ELFICO", "accent": CYAN},
    {"id": "parlami_in_binario", "lang": "it",
     "small": "> parlami", "big": "IN_BINARIO", "accent": TERM,
     "footer": "01000001 01001101 01001111 01010010 01000101"},
]


def measure(font, text):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box[1]


def fit_size(text, key, max_w, hi=900, lo=20):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if measure(load_font(key, mid), text)[0] <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


def render(ph, variant="dark", side=4500, margin_ratio=0.09):
    ink = adapt(INK, variant)
    gray = adapt(GRAY, variant)
    accent = adapt(ph["accent"], variant)
    margin = int(side * margin_ratio)
    max_w = side - 2 * margin

    big = ph["big"]
    # curseur = bloc plein dessiné (largeur ~0.55 d'un glyphe), pas un caractère
    big_sz = fit_size(big + "WW", "script", max_w)
    f_big = load_font("script", big_sz)

    small_sz = max(28, int(big_sz * 0.30))
    f_small = load_font("script", small_sz)

    foot = ph.get("footer")
    foot_sz = max(24, int(big_sz * 0.16)) if foot else 0
    f_foot = load_font("script", foot_sz) if foot else None

    sw, sh, soff = measure(f_small, ph["small"])
    bw, bh, boff = measure(f_big, big)
    cur_w = int(measure(f_big, "M")[0] * 0.62)
    cur_gap = int(cur_w * 0.45)
    fw = fh = foff = 0
    if foot:
        fw, fh, foff = measure(f_foot, foot)

    gap1 = int(big_sz * 0.22)
    gap2 = int(big_sz * 0.20)
    total_h = sh + gap1 + bh + (gap2 + fh if foot else 0)
    img = Image.new("RGBA", (side, total_h + 2 * margin), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    y = margin
    d.text(((side - sw) // 2, y - soff), ph["small"], font=f_small, fill=gray)
    y += sh + gap1
    # grand : mot en encre + curseur bloc plein coloré (rectangle dessiné)
    bbw = measure(f_big, big)[0]
    x0 = (side - (bbw + cur_gap + cur_w)) // 2
    d.text((x0, y - boff), big, font=f_big, fill=ink)
    cx = x0 + bbw + cur_gap
    d.rectangle([cx, y, cx + cur_w, y + bh], fill=accent)
    y += bh + (gap2 if foot else 0)
    if foot:
        d.text(((side - fw) // 2, y - foff), foot, font=f_foot, fill=accent)

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
    ap.add_argument("--out", default="produits/geek_phrases")
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
        cell = 620
        sheet = Image.new("RGB", (cols * cell, rows * cell), (244, 244, 246))
        dd = ImageDraw.Draw(sheet)
        try:
            lab = load_font("mono", 20)
        except Exception:
            lab = ImageFont.load_default()
        for i, ph in enumerate(items):
            im = render(ph, side=1500)
            im.thumbnail((cell - 30, cell - 60))
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 15, r * cell + 15))
            dd.text((c * cell + 15, r * cell + cell - 36),
                    ph["id"][:34], fill=(60, 60, 60), font=lab)
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=90)
        print(f"planche: {args.sheet} ({len(items)})")
        return

    variants = list(VARIANTS) if args.variant == "both" else [args.variant]
    os.makedirs(args.out, exist_ok=True)
    n = 0
    for ph in items:
        for v in variants:
            im = render(ph, variant=v)
            im.save(os.path.join(args.out, f"{ph['id']}__{ph['lang']}__{v}.png"),
                    dpi=(300, 300))
            n += 1
    print(f"{n} fichiers ({len(items)} × {len(variants)} variantes) → {args.out}")


if __name__ == "__main__":
    main()
