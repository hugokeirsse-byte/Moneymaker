#!/usr/bin/env python3
"""
gen_warning.py — série « avertissement sanitaire » façon paquet de cigarettes.

Cadre épais (noir ou rouge), texte en gros gras capitales façon mention légale
(« FUMER TUE » → « LE CAPITALISME TUE »). Format public non déposé : détournement
parodique sûr (pas de logo de marque, pas de photo-choc officielle).

Deux variantes maillot :
  dark  (maillots clairs) : cadre/texte en couleur sur fond blanc
  light (maillots foncés) : fond en couleur, cadre/texte en blanc
Fond transparent autour du cadre, 4500 px, 300 DPI.

Usage :
    python scripts/gen_warning.py --out produits/warning
    python scripts/gen_warning.py --sheet /tmp/warning.png
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

DATA_PATH = "data/warning.json"
FONT = "block"        # Archivo Black : grotesque lourd, look mention légale
FONT_SUB = "fjalla"   # condensé pour la sous-ligne
BLACK = (22, 22, 24, 255)
RED = (200, 28, 28, 255)
WHITE = (252, 252, 252, 255)


def wrap(font, text, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        trial = (cur + " " + w).strip()
        if cur and font.getlength(trial) > max_w:
            lines.append(cur)
            cur = w
        else:
            cur = trial
    if cur:
        lines.append(cur)
    return lines


def fit(text, max_w, max_lines, hi, lo=20):
    """Plus grande taille telle que le texte tienne en <= max_lines lignes."""
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load_font(FONT, mid)
        ls = wrap(f, text, max_w)
        if len(ls) <= max_lines and all(f.getlength(l) <= max_w for l in ls):
            lo = mid
        else:
            hi = mid - 1
    return lo


def render(entry, variant, side=4500):
    color = RED if entry.get("color") == "red" else BLACK
    text = entry["text"].upper()
    sub = entry.get("sub", "").upper()
    header = entry.get("header", "AVERTISSEMENT" if entry.get("lang") == "fr"
                        else "WARNING").upper()

    if variant == "dark":
        box_fill, fg = WHITE, color
    else:
        box_fill, fg = color, WHITE

    # géométrie du cadre
    bw = int(side * 0.020)                  # épaisseur bordure
    inner_w = int(side * 0.74)              # largeur utile du texte
    pad = int(side * 0.045)
    x0 = (side - inner_w) // 2 - pad
    x1 = side - x0

    main_sz = fit(text, inner_w, 3, hi=int(side * 0.16))
    fmain = load_font(FONT, main_sz)
    lines = wrap(fmain, text, inner_w)
    line_h = int(main_sz * 1.16)

    hdr_sz = int(side * 0.040)
    fhdr = load_font(FONT_SUB, hdr_sz)
    sub_sz = int(side * 0.034)
    fsub = load_font(FONT_SUB, sub_sz)

    # hauteurs des blocs
    hdr_bar_h = int(hdr_sz * 1.7)
    text_block = len(lines) * line_h
    sub_h = int(sub_sz * 1.5) if sub else 0
    inner_top_pad = int(side * 0.05)
    inner_bot_pad = int(side * 0.05)
    content_h = hdr_bar_h + inner_top_pad + text_block + sub_h + inner_bot_pad
    y0 = (side - content_h) // 2
    y1 = y0 + content_h

    img = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # boîte + bordure
    d.rectangle([x0, y0, x1, y1], fill=box_fill)
    for k in range(bw):
        d.rectangle([x0 + k, y0 + k, x1 - k, y1 - k], outline=fg)

    # bandeau d'en-tête (couleur pleine, texte inversé)
    bar = [x0 + bw, y0 + bw, x1 - bw, y0 + bw + hdr_bar_h]
    d.rectangle(bar, fill=fg)
    hb = fhdr.getbbox(header)
    d.text(((x0 + x1) / 2 - (hb[2] - hb[0]) / 2,
            (bar[1] + bar[3]) / 2 - (hb[3] + hb[1]) / 2),
           header, font=fhdr, fill=box_fill)

    # texte principal
    y = bar[3] + inner_top_pad
    for ln in lines:
        b = fmain.getbbox(ln)
        d.text(((x0 + x1) / 2 - (b[2] - b[0]) / 2 - b[0], y - b[1]),
               ln, font=fmain, fill=fg)
        y += line_h

    # sous-ligne
    if sub:
        b = fsub.getbbox(sub)
        d.text(((x0 + x1) / 2 - (b[2] - b[0]) / 2 - b[0], y + int(sub_sz * 0.2) - b[1]),
               sub, font=fsub, fill=fg)

    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="produits/warning")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--lang", default="")
    ap.add_argument("--data", default=DATA_PATH)
    ap.add_argument("--variant", default="both", choices=["both", "dark", "light"])
    args = ap.parse_args()

    data = json.load(open(args.data, encoding="utf-8"))
    entries = data["entries"]
    sel = set(args.only.split(",")) if args.only else None
    items = [e for e in entries
             if (not sel or e["id"] in sel) and (not args.lang or e.get("lang") == args.lang)]

    if args.sheet:
        cols = 4
        cell = 560
        rows = (len(items) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, rows * cell), (238, 238, 240))
        dd = ImageDraw.Draw(sheet)
        try:
            lab = load_font("fjalla", 15)
        except Exception:
            lab = ImageFont.load_default()
        for i, e in enumerate(items):
            v = "light" if (i % 4 == 3) else "dark"   # montre quelques inversés
            im = render(e, v, side=1300)
            im.thumbnail((cell - 40, cell - 60))
            bg = Image.new("RGB", im.size, (255, 255, 255) if v == "dark" else (32, 32, 36))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 20, r * cell + 20))
            dd.text((c * cell + 20, r * cell + cell - 26), f"{e['id'][:30]} [{v}]",
                    fill=(70, 70, 70), font=lab)
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=88)
        print(f"planche: {args.sheet} ({len(items)})")
        return

    variants = ["dark", "light"] if args.variant == "both" else [args.variant]
    os.makedirs(args.out, exist_ok=True)
    n = 0
    for e in items:
        for v in variants:
            im = render(e, v)
            im.save(os.path.join(args.out, f"{e['id']}__{v}.png"), dpi=(300, 300))
            n += 1
    print(f"{n} fichiers ({len(items)} × {len(variants)} variantes) → {args.out}")


if __name__ == "__main__":
    main()
