#!/usr/bin/env python3
"""
gen_relatable.py — punchlines « relatable » déadpan (style qui domine Redbubble).

Écriture : Pacifico (script rond chaleureux) en casse Titre — le contraste
écriture mignonne / propos cynique fait mouche. Mot-clé accentué en rouge.

Deux variantes par design pour tous les maillots :
  __dark  : encre sombre (maillots clairs)
  __light : encre blanche (maillots foncés)
Fond transparent, 4500 px.

Usage :
    python scripts/gen_relatable.py --out produits/relatable
    python scripts/gen_relatable.py --sheet /tmp/relatable.png
    python scripts/gen_relatable.py --variant dark   # une seule variante
"""
import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

FONT = "script"  # Pacifico

# palettes par variante : ink (texte), soft (atténué), accent (mot en rouge)
PALETTES = {
    "dark":  {"ink": (30, 30, 34, 255), "soft": (120, 122, 128, 255),
              "accent": (190, 60, 48, 255)},
    "light": {"ink": (244, 244, 246, 255), "soft": (180, 182, 188, 255),
              "accent": (232, 96, 84, 255)},
}

# id, lignes, {index_ligne: "accent"|"soft"}
PHRASES = [
    ("professionally_tired", ["Professionally", "Tired"], {1: "accent"}),
    ("emotionally_unavailable_chores", ["Emotionally Unavailable", "for Chores"], {1: "soft"}),
    ("running_on_snacks_spite", ["Running on", "Snacks & Spite"], {1: "accent"}),
    ("socially_optional", ["Socially", "Optional"], {1: "accent"}),
    ("here_unfortunately", ["Here.", "Unfortunately."], {1: "soft"}),
    ("low_battery_high_standards", ["Low Battery", "High Standards"], {1: "accent"}),
    ("technically_functioning", ["Technically", "Functioning"], {1: "accent"}),
    ("out_of_office_mentally", ["Out of Office", "Mentally"], {1: "accent"}),
    ("doing_my_best_allegedly", ["Doing My Best", "(Allegedly)"], {1: "soft"}),
    ("emotional_support_overthinker", ["Emotional Support", "Overthinker"], {1: "accent"}),
    ("mildly_feral", ["Mildly", "Feral"], {1: "accent"}),
    ("my_hobby_not_perceived", ["My Hobby Is", "Not Being Perceived"], {1: "soft"}),
    ("introvert_loading", ["Introvert", "Loading…"], {1: "soft"}),
    ("not_now_not_ever", ["Not Now.", "Also Not Later."], {1: "soft"}),
    ("powered_by_caffeine_anxiety", ["Powered by", "Caffeine & Anxiety"], {1: "accent"}),
    ("im_not_arguing", ["I'm Not Arguing", "Just Explaining", "Why I'm Right"], {2: "accent"}),
]


def measure(font, text):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box[1]


def fit_size(lines, max_w, hi=760, lo=20):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load_font(FONT, mid)
        if max(measure(f, t)[0] for t in lines) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


def render(lines, accents, pal, side=4500, margin_ratio=0.12):
    margin = int(side * margin_ratio)
    max_w = side - 2 * margin
    sz = fit_size(lines, max_w)
    f = load_font(FONT, sz)
    gap = int(sz * 0.16)   # Pacifico a déjà de grandes contre-formes

    dims = [measure(f, t) for t in lines]
    total_h = sum(dd[1] for dd in dims) + gap * (len(lines) - 1)
    img = Image.new("RGBA", (side, total_h + 2 * margin), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)

    y = margin
    for i, (t, (w, h, off)) in enumerate(zip(lines, dims)):
        col = pal[accents[i]] if i in accents else pal["ink"]
        dr.text(((side - w) // 2, y - off), t, font=f, fill=col)
        y += h + gap

    bbox = img.getbbox()
    if bbox is None:
        return img
    img = img.crop(bbox)
    pad = int(side * 0.10)
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(img, (pad, pad))
    if max(out.size) != side:
        r = side / max(out.size)
        out = out.resize((round(out.width * r), round(out.height * r)), Image.LANCZOS)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="produits/relatable")
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
        sheet = Image.new("RGB", (cols * cell, rows * cell), (244, 244, 246))
        dd = ImageDraw.Draw(sheet)
        try:
            lab = load_font("fjalla", 17)
        except Exception:
            lab = ImageFont.load_default()
        for i, (pid, lines, acc) in enumerate(items):
            im = render(lines, acc, PALETTES["dark"], side=1400)
            im.thumbnail((cell - 40, cell - 56))
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 20, r * cell + 20))
            dd.text((c * cell + 20, r * cell + cell - 30), pid[:30],
                    fill=(70, 70, 70), font=lab)
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=90)
        print(f"planche: {args.sheet} ({len(items)})")
        return

    variants = ["dark", "light"] if args.variant == "both" else [args.variant]
    os.makedirs(args.out, exist_ok=True)
    n = 0
    for pid, lines, acc in items:
        for v in variants:
            im = render(lines, acc, PALETTES[v])
            im.save(os.path.join(args.out, f"{pid}__{v}.png"), dpi=(300, 300))
            n += 1
    print(f"{n} fichiers ({len(items)} phrases × {len(variants)} variantes) → {args.out}")


if __name__ == "__main__":
    main()
