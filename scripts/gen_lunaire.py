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

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

INK = (26, 26, 30, 255)
ACCENTS = [
    (190, 46, 38, 255), (32, 90, 168, 255), (40, 120, 70, 255),
    (170, 90, 20, 255), (110, 40, 120, 255), (24, 24, 28, 255),
]

# (id, ligne1, ligne2, police, rime?) — déadpan, deux mots, gros
PHRASES = [
    ("facteur_dompteur", "FACTEUR", "DOMPTEUR", "impact"),
    ("plombier_lunaire", "PLOMBIER", "LUNAIRE", "block"),
    ("notaire_sauvage", "NOTAIRE", "SAUVAGE", "tall"),
    ("boulanger_nucleaire", "BOULANGER", "NUCLÉAIRE", "impact"),
    ("comptable_feroce", "COMPTABLE", "FÉROCE", "block"),
    ("docteur_flatteur", "DOCTEUR", "FLATTEUR", "fjalla"),
    ("huissier_de_combat", "HUISSIER", "DE COMBAT", "impact"),
    ("pasteur_amateur", "PASTEUR", "AMATEUR", "tall"),
    ("charcutier_quantique", "CHARCUTIER", "QUANTIQUE", "block"),
    ("dentiste_viking", "DENTISTE", "VIKING", "impact"),
    ("pigeon_tactique", "PIGEON", "TACTIQUE", "fjalla"),
    ("retraite_balistique", "RETRAITÉ", "BALISTIQUE", "block"),
    ("plongeur_vengeur", "PLONGEUR", "VENGEUR", "impact"),
    ("fromager_mercenaire", "FROMAGER", "MERCENAIRE", "tall"),
    ("depute_aquatique", "DÉPUTÉ", "AQUATIQUE", "block"),
    ("tracteur_emotionnel", "TRACTEUR", "ÉMOTIONNEL", "fjalla"),
    ("eveque_bionique", "ÉVÊQUE", "BIONIQUE", "impact"),
    ("gendarme_melancolique", "GENDARME", "MÉLANCOLIQUE", "block"),
    ("facteur_intersideral", "FACTEUR", "INTERSIDÉRAL", "tall"),
    ("chanteur_menteur", "CHANTEUR", "MENTEUR", "impact"),
    ("boxeur_reveur", "BOXEUR", "RÊVEUR", "fjalla"),
    ("avocat_maritime", "AVOCAT", "MARITIME", "block"),
]


def measure(font, text):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box[1]


def fit_size(lines, key, max_w, hi=1100, lo=20):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load_font(key, mid)
        if max(measure(f, t)[0] for t in lines) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


def render(l1, l2, key, accent, side=4500, margin_ratio=0.10):
    margin = int(side * margin_ratio)
    max_w = side - 2 * margin
    sz = fit_size([l1, l2], key, max_w)
    f = load_font(key, sz)
    gap = int(sz * 0.06)

    d1 = measure(f, l1)
    d2 = measure(f, l2)
    total_h = d1[1] + gap + d2[1]
    img = Image.new("RGBA", (side, total_h + 2 * margin), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)

    y = margin
    dr.text(((side - d1[0]) // 2, y - d1[2]), l1, font=f, fill=INK)
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
        for i, (pid, l1, l2, key) in enumerate(items):
            im = render(l1, l2, key, ACCENTS[i % len(ACCENTS)], side=1400)
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

    os.makedirs(args.out, exist_ok=True)
    n = 0
    for i, (pid, l1, l2, key) in enumerate(items):
        im = render(l1, l2, key, ACCENTS[i % len(ACCENTS)])
        path = os.path.join(args.out, f"{pid}.png")
        im.save(path, dpi=(300, 300))
        print(f"  {path}")
        n += 1
    print(f"\n{n} fichiers → {args.out}")


if __name__ == "__main__":
    main()
