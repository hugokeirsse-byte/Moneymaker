#!/usr/bin/env python3
"""
gen_trendy.py — mots « à la mode » & cynisme doux (zeitgeist EN).

Écriture : Pacifico (script rond) en casse Titre, mot accentué en rouge.
overrated/underrated/wonderrated (avec rature), overthinking, delulu, unhinged…

Deux variantes par design :
  __dark  : encre sombre (maillots clairs)
  __light : encre blanche (maillots foncés)
Fond transparent, 4500 px.

Usage :
    python scripts/gen_trendy.py --out produits/trendy
    python scripts/gen_trendy.py --sheet /tmp/trendy.png
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

FONT = "script"  # Pacifico

PALETTES = {
    "dark":  {"ink": (30, 30, 34, 255), "soft": (122, 124, 130, 255),
              "accent": (190, 60, 48, 255), "blue": (32, 90, 170, 255)},
    "light": {"ink": (244, 244, 246, 255), "soft": (180, 182, 188, 255),
              "accent": (232, 96, 84, 255), "blue": (96, 150, 224, 255)},
}

# id, lignes, {index: "accent"|"soft"|"blue"}, strike(index ou None)
PHRASES = [
    ("overrated", ["Overrated"], {0: "accent"}, 0),
    ("underrated", ["Underrated"], {0: "blue"}, None),
    ("rated_trio", ["Overrated", "Underrated", "Wonderrated"], {2: "accent"}, None),
    ("everything_overrated", ["Everything", "Is Overrated"], {1: "accent"}, None),
    ("let_me_overthink", ["Let Me", "Overthink", "This"], {1: "accent"}, None),
    ("professional_overthinker", ["Professional", "Overthinker"], {1: "accent"}, None),
    ("overthinking_since_birth", ["Overthinking", "Since Birth"], {1: "soft"}, None),
    ("delulu", ["Delulu"], {0: "accent"}, None),
    ("delulu_solulu", ["Delulu Is", "the Solulu"], {1: "accent"}, None),
    ("unhinged_but_polite", ["Unhinged", "but Polite"], {1: "soft"}, None),
    ("chronically_unimpressed", ["Chronically", "Unimpressed"], {1: "accent"}, None),
    ("mildly_disappointed", ["Mildly", "Disappointed"], {1: "soft"}, None),
    ("lowering_the_bar", ["Lowering the Bar", "Successfully"], {1: "accent"}, None),
    ("emotionally_overrated", ["Emotionally", "Overrated"], {1: "accent"}, None),
    ("iconic_allegedly", ["Iconic", "(Allegedly)"], {1: "soft"}, None),
    ("bare_minimum", ["Giving", "Bare Minimum", "Iconically"], {1: "accent"}, None),
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


def render(lines, accents, strike, pal, side=4500, margin_ratio=0.12):
    margin = int(side * margin_ratio)
    max_w = side - 2 * margin
    sz = fit_size(lines, max_w)
    f = load_font(FONT, sz)
    gap = int(sz * 0.14)

    dims = [measure(f, t) for t in lines]
    total_h = sum(dd[1] for dd in dims) + gap * (len(lines) - 1)
    img = Image.new("RGBA", (side, total_h + 2 * margin), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)

    y = margin
    for i, (t, (w, h, off)) in enumerate(zip(lines, dims)):
        col = pal[accents[i]] if i in accents else pal["ink"]
        x = (side - w) // 2
        dr.text((x, y - off), t, font=f, fill=col)
        if strike == i:
            ly = y + int(h * 0.52)
            dr.line([(x, ly), (x + w, ly)], fill=col, width=max(6, sz // 24))
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
    ap.add_argument("--out", default="produits/trendy")
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
        for i, (pid, lines, acc, strike) in enumerate(items):
            im = render(lines, acc, strike, PALETTES["dark"], side=1400)
            im.thumbnail((cell - 40, cell - 54))
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 20, r * cell + 20))
            dd.text((c * cell + 20, r * cell + cell - 30), pid[:28],
                    fill=(70, 70, 70), font=lab)
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=90)
        print(f"planche: {args.sheet} ({len(items)})")
        return

    variants = ["dark", "light"] if args.variant == "both" else [args.variant]
    os.makedirs(args.out, exist_ok=True)
    n = 0
    for pid, lines, acc, strike in items:
        for v in variants:
            im = render(lines, acc, strike, PALETTES[v])
            im.save(os.path.join(args.out, f"{pid}__{v}.png"), dpi=(300, 300))
            n += 1
    print(f"{n} fichiers ({len(items)} phrases × {len(variants)} variantes) → {args.out}")


if __name__ == "__main__":
    main()
