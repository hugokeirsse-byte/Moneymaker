#!/usr/bin/env python3
"""
gen_niches.py — punchlines de niches & sous-niches (gros marchés mal desservis).

Une phrase courte et drôle ciblant une communauté de passionnés (propriétaires
de Malinois, boulangers au levain, joueurs de disc golf, infirmières, soudeurs…).
Écriture Pacifico, encre noire + un mot accentué en rouge, et — au choix — un
ornement « vague » dessiné au-dessus et au-dessous (filet typographique propre).

Deux variantes maillot (encre sombre / claire), fond transparent, 4500 px.

Usage :
    python scripts/gen_niches.py --out produits/niches
    python scripts/gen_niches.py --sheet /tmp/niches.png
    python scripts/gen_niches.py --niche malinois        # une niche
    python scripts/gen_niches.py --lang en               # une langue
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402
from typo_variants import VARIANTS, adapt  # noqa: E402
from typo_ornaments import (STYLES, pick_style, apply_ornament,  # noqa: E402
                            sticker_layer, draw_word)

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

DATA_PATH = "data/niches_funny.json"
FONT = "script"  # Pacifico, comme tout le catalogue

# accent doré (lisible sur clair comme sur foncé → identique dans les deux palettes)
PALETTES = {
    "dark":  {"ink": (30, 30, 34, 255),   "accent": (201, 162, 39, 255)},
    "light": {"ink": (244, 244, 246, 255), "accent": (201, 162, 39, 255)},
}


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


def draw_swash(d, cx, y, width, color, base_thick):
    """Ornement « vague » symétrique, qui s'affine aux extrémités.

    Une onde douce (1,5 période) centrée en cx, d'amplitude maximale au milieu
    et nulle aux bouts ; épaisseur effilée + une petite goutte à chaque extrémité.
    """
    n = 140
    half = width / 2.0
    pts = []
    for i in range(n + 1):
        t = i / n                       # 0..1
        x = cx - half + t * width
        env = math.sin(math.pi * t)     # 0 aux bords, 1 au centre
        amp = base_thick * 2.4 * env
        yy = y + amp * math.sin(2 * math.pi * 1.5 * t)
        pts.append((x, yy))
    for i in range(n):
        t = (i + 0.5) / n
        env = math.sin(math.pi * t)
        w = max(1, base_thick * (0.28 + 0.72 * env))
        d.line([pts[i], pts[i + 1]], fill=color, width=int(round(w)))
    # petites gouttes aux extrémités
    r = base_thick * 0.9
    for px, py in (pts[0], pts[-1]):
        d.ellipse([px - r, py - r, px + r, py + r], fill=color)


def pick_for(entry, idx):
    """Style : nom explicite si fourni, False/None = aucun, sinon alternance/6."""
    o = entry.get("ornament", "auto")
    if o is False or o is None:
        return None
    if isinstance(o, str) and o in STYLES:
        return o
    return pick_style(idx)


def render(entry, pal, idx=0, side=4500, margin_ratio=0.13):
    lines = entry["lines"]
    accent_idx = entry.get("accent", len(lines) - 1)
    style = pick_for(entry, idx)
    sticker = (style == "sticker")
    if sticker:
        # carte blanche : encre toujours sombre + rouge
        pal = PALETTES["dark"]

    margin = int(side * (0.16 if sticker else margin_ratio))
    max_w = side - 2 * margin
    sz = fit_size(lines, max_w, hi=int(side * 0.20))
    f = load_font(FONT, sz)
    qf = load_font(FONT, int(sz * 1.5))
    gap = int(sz * 0.15)

    dims = [measure(f, t) for t in lines]
    text_w = max(dd[0] for dd in dims)
    text_h = sum(dd[1] for dd in dims) + gap * (len(lines) - 1)

    img = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)

    cx = side // 2
    top = side // 2 - text_h // 2
    bbox = (cx - text_w // 2, top, cx + text_w // 2, top + text_h)

    if sticker:
        img.alpha_composite(sticker_layer((side, side), bbox, side / 4500.0))

    sw = max(2, int(sz * 0.025))
    y = top
    for i, (t, (w, h, off)) in enumerate(zip(lines, dims)):
        draw_word(dr, ((side - w) // 2, y - off), t, f, i == accent_idx,
                  pal["ink"], pal["accent"], stroke=sw)
        y += h + gap

    if style and not sticker:
        apply_ornament(dr, style, bbox, pal["ink"], pal["accent"],
                       scale=side / 4500.0, quote_font=qf)

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
    ap.add_argument("--out", default="produits/niches")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--niche", default="")
    ap.add_argument("--lang", default="")
    ap.add_argument("--data", default=DATA_PATH)
    ap.add_argument("--variant", default="both", choices=["both", "dark", "light"])
    args = ap.parse_args()

    data = json.load(open(args.data, encoding="utf-8"))
    entries = data["entries"]
    sel = set(args.only.split(",")) if args.only else None
    items = [(i, e) for i, e in enumerate(entries)
             if (not sel or e["id"] in sel)
             and (not args.niche or e.get("niche") == args.niche)
             and (not args.lang or e.get("lang") == args.lang)]

    if args.sheet:
        cols = 5
        cell = 540
        rows = (len(items) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, rows * cell), (244, 244, 246))
        dd = ImageDraw.Draw(sheet)
        try:
            lab = load_font("fjalla", 15)
        except Exception:
            lab = ImageFont.load_default()
        for k, (i, e) in enumerate(items):
            im = render(e, PALETTES["dark"], idx=i, side=1300)
            im.thumbnail((cell - 40, cell - 60))
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(k, cols)
            sheet.paste(bg, (c * cell + 20, r * cell + 20))
            dd.text((c * cell + 20, r * cell + cell - 28), e["id"][:32],
                    fill=(70, 70, 70), font=lab)
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=88)
        print(f"planche: {args.sheet} ({len(items)})")
        return

    variants = list(VARIANTS) if args.variant == "both" else [args.variant]
    os.makedirs(args.out, exist_ok=True)
    n = 0
    for i, e in items:
        for v in variants:
            im = render(e, PALETTES[v], idx=i)
            im.save(os.path.join(args.out, f"{e['id']}__{v}.png"), dpi=(300, 300))
            n += 1
    print(f"{n} fichiers ({len(items)} phrases × {len(variants)} variantes) → {args.out}")


if __name__ == "__main__":
    main()
