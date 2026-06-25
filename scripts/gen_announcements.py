#!/usr/bin/env python3
"""
gen_announcements.py — niche « annonces » evergreen (grossesse, bébé, famille).

Marché cadeau intemporel et fort vendeur : annonce de grossesse, faire-part,
« promu grand frère », futurs parents… Écriture Pacifico chaleureuse, mot
accentué, certaines avec une barre de chargement « bébé ».

Deux variantes maillot (encre sombre / claire), fond transparent, 4500 px.

Usage :
    python scripts/gen_announcements.py --out produits/announcements
    python scripts/gen_announcements.py --sheet /tmp/announce.png
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402
from typo_variants import VARIANTS, adapt  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

FONT = "script"  # Pacifico

PALETTES = {
    "dark":  {"ink": (30, 30, 34, 255), "soft": (120, 122, 128, 255),
              "accent": (210, 90, 110, 255), "bar": (120, 180, 200, 255)},
    "light": {"ink": (244, 244, 246, 255), "soft": (180, 182, 188, 255),
              "accent": (236, 120, 140, 255), "bar": (150, 205, 225, 255)},
}

# id, lang, lignes, {idx:"accent"|"soft"}, progress(None | (label, fraction))
ITEMS = [
    # --- EN ---
    ("eating_for_two", "en", ["Eating", "for Two"], {1: "accent"}, None),
    ("baby_loading", "en", ["Baby", "Loading…"], {1: "accent"}, ("loading", 0.75)),
    ("promoted_big_sister", "en", ["Promoted to", "Big Sister"], {1: "accent"}, None),
    ("promoted_big_brother", "en", ["Promoted to", "Big Brother"], {1: "accent"}, None),
    ("promoted_to_daddy", "en", ["Promoted", "to Daddy"], {1: "accent"}, None),
    ("promoted_to_mommy", "en", ["Promoted", "to Mommy"], {1: "accent"}, None),
    ("plus_one_coming", "en", ["Plus One", "Coming Soon"], {1: "accent"}, None),
    ("snack_dealer", "en", ["Official", "Snack Dealer"], {1: "accent"}, None),
    ("worth_the_wait", "en", ["Worth", "the Wait"], {1: "accent"}, None),
    ("made_with_love", "en", ["Made With Love", "Est. 2026"], {1: "soft"}, None),
    ("two_hearts_one_bump", "en", ["Two Hearts", "One Bump"], {1: "accent"}, None),
    ("hello_im_new", "en", ["Hello,", "I'm New Here"], {1: "accent"}, None),
    # --- FR ---
    ("on_mange_pour_deux", "fr", ["On Mange", "Pour Deux"], {1: "accent"}, None),
    ("bebe_en_chargement", "fr", ["Bébé", "en Chargement…"], {1: "accent"}, ("chargement", 0.75)),
    ("promu_grande_soeur", "fr", ["Promue", "Grande Sœur"], {1: "accent"}, None),
    ("promu_grand_frere", "fr", ["Promu", "Grand Frère"], {1: "accent"}, None),
    ("bientot_papa", "fr", ["Bientôt", "Papa"], {1: "accent"}, None),
    ("bientot_maman", "fr", ["Bientôt", "Maman"], {1: "accent"}, None),
    ("un_petit_plus", "fr", ["Un Petit Plus", "Arrive"], {1: "accent"}, None),
    ("fait_avec_amour", "fr", ["Fait Avec Amour", "2026"], {1: "soft"}, None),
    ("ca_pousse", "fr", ["Ça Pousse", "Là-Dedans"], {1: "accent"}, None),
    ("coucou_cest_moi", "fr", ["Coucou,", "C'est Bientôt Moi"], {1: "accent"}, None),
]


def measure(font, text):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box[1]


def fit_size(lines, max_w, hi=720, lo=20):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load_font(FONT, mid)
        if max(measure(f, t)[0] for t in lines) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


def render(lines, accents, progress, pal, side=4500, margin_ratio=0.12):
    margin = int(side * margin_ratio)
    max_w = side - 2 * margin
    sz = fit_size(lines, max_w)
    f = load_font(FONT, sz)
    gap = int(sz * 0.14)

    dims = [measure(f, t) for t in lines]
    bar_h = int(sz * 0.55) if progress else 0
    total_h = sum(d[1] for d in dims) + gap * (len(lines) - 1) + bar_h
    img = Image.new("RGBA", (side, total_h + 2 * margin), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)

    y = margin
    for i, (t, (w, h, off)) in enumerate(zip(lines, dims)):
        col = pal[accents[i]] if i in accents else pal["ink"]
        dr.text(((side - w) // 2, y - off), t, font=f, fill=col)
        y += h + gap

    if progress:
        label, frac = progress
        bw = int(max_w * 0.62)
        bx = (side - bw) // 2
        bh = int(sz * 0.26)
        rad = bh // 2
        dr.rounded_rectangle([bx, y, bx + bw, y + bh], radius=rad,
                             outline=pal["ink"], width=max(4, sz // 40))
        fillw = int(bw * frac)
        if fillw > bh:
            dr.rounded_rectangle([bx, y, bx + fillw, y + bh], radius=rad, fill=pal["bar"])
        pf = load_font("geo", int(sz * 0.22))
        pct = f"{int(frac * 100)}%"
        pw, ph, poff = measure(pf, pct)
        dr.text(((side - pw) // 2, y + bh + int(sz * 0.08) - poff), pct, font=pf, fill=pal["soft"])

    bbox = img.getbbox()
    img = img.crop(bbox)
    pad = int(side * 0.10)
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(img, (pad, pad))
    if max(out.size) != side:
        k = side / max(out.size)
        out = out.resize((round(out.width * k), round(out.height * k)), Image.LANCZOS)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="produits/announcements")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--lang", default="")
    ap.add_argument("--variant", default="both", choices=["both", "dark", "light"])
    args = ap.parse_args()

    sel = set(args.only.split(",")) if args.only else None
    items = [x for x in ITEMS if (not sel or x[0] in sel) and (not args.lang or x[1] == args.lang)]

    if args.sheet:
        cols = 4
        cell = 560
        rows = (len(items) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, rows * cell), (244, 244, 246))
        dd = ImageDraw.Draw(sheet)
        try:
            lab = load_font("geo", 16)
        except Exception:
            lab = ImageFont.load_default()
        for i, (pid, lg, lines, acc, prog) in enumerate(items):
            im = render(lines, acc, prog, PALETTES["dark"], side=1400)
            im.thumbnail((cell - 40, cell - 56))
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 20, r * cell + 20))
            dd.text((c * cell + 20, r * cell + cell - 30), pid[:28], fill=(70, 70, 70), font=lab)
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=90)
        print(f"planche: {args.sheet} ({len(items)})")
        return

    variants = list(VARIANTS) if args.variant == "both" else [args.variant]
    os.makedirs(args.out, exist_ok=True)
    n = 0
    for pid, lg, lines, acc, prog in items:
        for v in variants:
            im = render(lines, acc, prog, PALETTES[v])
            im.save(os.path.join(args.out, f"{pid}__{lg}__{v}.png"), dpi=(300, 300))
            n += 1
    print(f"{n} fichiers ({len(items)} × {len(variants)}) → {args.out}")


if __name__ == "__main__":
    main()
