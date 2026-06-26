#!/usr/bin/env python3
"""
gen_lunaire.py — phrases absurdes « sorties de nulle part », au premier degré.

Recette qui vend en POD sans se faire dépublier : un mot sérieux (métier, statut)
collé à un mot improbable, en grosse typo déadpan facon badge officiel. Certaines
riment. Fond transparent, 4500 px.

Usage :
    python scripts/gen_lunaire.py --out produits/lunaire
    python scripts/gen_lunaire.py --sheet /tmp/lunaire.png
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402
from typo_variants import INK_DARK, VARIANTS, adapt  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

INK = INK_DARK
RED = (201, 162, 39, 255)

# (id, ligne1, ligne2) — déadpan, deux mots, gros
PHRASES = [
    ("facteur_dompteur", "FACTEUR", "DOMPTEUR"),
    ("plombier_lunaire", "PLOMBIER", "LUNAIRE"),
    ("notaire_sauvage", "NOTAIRE", "SAUVAGE"),
    ("boulanger_nucleaire", "BOULANGER", "NUCLÉAIRE"),
    ("comptable_feroce", "COMPTABLE", "FÉROCE"),
    ("docteur_flatteur", "DOCTEUR", "FLATTEUR"),
    ("huissier_de_combat", "HUISSIER", "DE COMBAT"),
    ("pasteur_amateur", "PASTEUR", "AMATEUR"),
    ("charcutier_quantique", "CHARCUTIER", "QUANTIQUE"),
    ("dentiste_viking", "DENTISTE", "VIKING"),
    ("pigeon_tactique", "PIGEON", "TACTIQUE"),
    ("retraite_balistique", "RETRAITÉ", "BALISTIQUE"),
    ("plongeur_vengeur", "PLONGEUR", "VENGEUR"),
    ("fromager_mercenaire", "FROMAGER", "MERCENAIRE"),
    ("depute_aquatique", "DÉPUTÉ", "AQUATIQUE"),
    ("tracteur_emotionnel", "TRACTEUR", "ÉMOTIONNEL"),
    ("eveque_bionique", "ÉVÊQUE", "BIONIQUE"),
    ("gendarme_melancolique", "GENDARME", "MÉLANCOLIQUE"),
    ("facteur_intersideral", "FACTEUR", "INTERSIDÉRAL"),
    ("chanteur_menteur", "CHANTEUR", "MENTEUR"),
    ("boxeur_reveur", "BOXEUR", "RÊVEUR"),
    ("avocat_maritime", "AVOCAT", "MARITIME"),
]


def measure(font, text):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box[1]


def fit_size(lines, max_w, hi=1100, lo=20):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load_font("script", mid)
        if max(measure(f, t)[0] for t in lines) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


def render(l1, l2, variant="dark", side=4500, margin_ratio=0.10):
    ink = adapt(INK, variant)
    accent = adapt(RED, variant)
    margin = int(side * margin_ratio)
    max_w = side - 2 * margin
    sz = fit_size([l1, l2], max_w)
    f = load_font("script", sz)
    gap = int(sz * 0.06)

    d1 = measure(f, l1)
    d2 = measure(f, l2)
    total_h = d1[1] + gap + d2[1]
    img = Image.new("RGBA", (side, total_h + 2 * margin), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)

    y = margin
    dr.text(((side - d1[0]) // 2, y - d1[2]), l1, font=f, fill=ink)
    y += d1[1] + gap
    dr.text(((side - d2[0]) // 2, y - d2[2]), l2, font=f, fill=accent)

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
    ap.add_argument("--out", default="produits/lunaire")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--variant", default="both", choices=["both", "dark", "light"])
    args = ap.parse_args()

    sel = set(args.only.split(",")) if args.only else None
    items = [p for p in PHRASES if not sel or p[0] in sel]

    if args.sheet:
        cols = 4
        rows = (len(items) + cols - 1) // cols
        cell = 560
        sheet = Image.new("RGB", (cols * cell, rows * cell), (242, 242, 242))
        dd = ImageDraw.Draw(sheet)
        try:
            lab = load_font("fjalla", 18)
        except Exception:
            lab = ImageFont.load_default()
        for i, (pid, l1, l2) in enumerate(items):
            im = render(l1, l2, side=1400)
            im.thumbnail((cell - 30, cell - 56))
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 15, r * cell + 15))
            dd.text((c * cell + 15, r * cell + cell - 32), f"{l1} {l2}",
                    fill=(60, 60, 60), font=lab)
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=90)
        print(f"planche: {args.sheet} ({len(items)})")
        return

    variants = list(VARIANTS) if args.variant == "both" else [args.variant]
    os.makedirs(args.out, exist_ok=True)
    n = 0
    for i, (pid, l1, l2) in enumerate(items):
        for v in variants:
            im = render(l1, l2, variant=v)
            im.save(os.path.join(args.out, f"{pid}__{v}.png"), dpi=(300, 300))
            n += 1
    print(f"{n} fichiers ({len(items)} × {len(variants)} variantes) → {args.out}")


if __name__ == "__main__":
    main()
