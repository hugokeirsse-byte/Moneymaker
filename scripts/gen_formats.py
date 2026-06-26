#!/usr/bin/env python3
"""
gen_formats.py — séries « formats officiels détournés » retenus.

Formats pilotés par data/formats.json (champ "format") :
  caution   : ruban jaune/noir « CAUTION : … »
  care      : étiquette de lavage (symboles) + texte
  card      : carton rouge / jaune (foot) incliné
  loading   : barre de chargement « … EN COURS »
  error     : fenêtre d'erreur 404
  rx        : ordonnance
  nutrition : étiquette « valeurs personnelles »

Variantes maillot : dark (clairs) / light (foncés). Les formats à couleur propre
(caution, carton) sont identiques ; les formats encre-sur-transparent (care,
loading, rx) basculent l'encre en clair pour les maillots foncés.
Fond transparent, 4500 px, 300 DPI.

Usage :
    python scripts/gen_formats.py --out produits/formats
    python scripts/gen_formats.py --sheet /tmp/formats.png
"""
import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402

ARIAL = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
ARIALR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
GOLD = (201, 162, 39, 255)


def af(sz, reg=False):
    return ImageFont.truetype(ARIALR if reg else ARIAL, int(sz))


def ct(d, cx, y, text, font, fill, anchor="ma"):
    d.text((cx, y), text, font=font, fill=fill, anchor=anchor)


def fitw(text, font_fn, max_w, hi, lo=16):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if font_fn(mid).getlength(text) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


def _ink(variant):
    return (20, 20, 22, 255) if variant == "dark" else (245, 245, 247, 255)


# ── caution ────────────────────────────────────────────────────────────────
def f_caution(e, variant, side):
    im = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    H = int(side * 0.46); y0 = (side - H) // 2
    yellow = (250, 204, 21, 255); black = (20, 20, 22, 255)
    d.rectangle([0, y0, side, y0 + H], fill=yellow)
    sw = int(side * 0.07)
    for band in (y0, y0 + H - int(H * 0.15)):
        for x in range(-side, side, sw * 2):
            d.polygon([(x, band), (x + sw, band), (x + sw - 40, band + int(H * 0.15)),
                       (x - 40, band + int(H * 0.15))], fill=black)
    head = e.get("head", "CAUTION").upper()
    text = e["text"].upper()
    ct(d, side // 2, y0 + int(H * 0.26), head, af(side * 0.085), black)
    fs = fitw(text, af, int(side * 0.82), int(side * 0.06))
    ct(d, side // 2, y0 + int(H * 0.52), text, af(fs), black)
    return im


# ── care (étiquette de lavage) ──────────────────────────────────────────────
def f_care(e, variant, side):
    im = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fg = _ink(variant)
    W = int(side * 0.8); H = int(side * 0.4); x0 = (side - W) // 2; y0 = (side - H) // 2
    d.rectangle([x0, y0, x0 + W, y0 + H], outline=fg, width=int(side * 0.006))
    n = 4; cw = W / n; sy = y0 + int(H * 0.24); s = int(side * 0.07)
    cxs = [x0 + cw * (i + 0.5) for i in range(n)]
    lw = max(3, int(side * 0.006))
    d.polygon([(cxs[0]-s, sy-s*0.4), (cxs[0]+s, sy-s*0.4), (cxs[0]+s*0.7, sy+s),
               (cxs[0]-s*0.7, sy+s)], outline=fg, width=lw)
    d.arc([cxs[0]-s*0.6, sy-s*0.1, cxs[0]+s*0.6, sy+s*0.5], 0, 180, fill=fg, width=lw)
    d.polygon([(cxs[1], sy-s), (cxs[1]-s, sy+s), (cxs[1]+s, sy+s)], outline=fg, width=lw)
    d.rectangle([cxs[2]-s, sy-s, cxs[2]+s, sy+s], outline=fg, width=lw)
    d.ellipse([cxs[2]-s*0.3, sy-s*0.3, cxs[2]+s*0.3, sy+s*0.3], outline=fg, width=lw)
    d.polygon([(cxs[3]-s, sy+s*0.5), (cxs[3]+s, sy+s*0.5), (cxs[3]+s*0.6, sy-s*0.3),
               (cxs[3]-s*0.3, sy-s*0.3)], outline=fg, width=lw)
    ct(d, side // 2, y0 + int(H * 0.66), e["text"].upper(),
       af(fitw(e["text"].upper(), af, int(W * 0.92), int(side * 0.05))), fg)
    if e.get("sub"):
        ct(d, side // 2, y0 + int(H * 0.83), e["sub"], af(side * 0.030, reg=True), fg)
    return im


# ── card (carton foot) ──────────────────────────────────────────────────────
def f_card(e, variant, side):
    im = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    layer = Image.new("RGBA", (side, side), (0, 0, 0, 0)); dl = ImageDraw.Draw(layer)
    col = (240, 200, 25, 255) if e.get("color") == "yellow" else (206, 26, 32, 255)
    W = int(side * 0.46); H = int(side * 0.64); x0 = (side - W) // 2; y0 = (side - H) // 2
    dl.rounded_rectangle([x0, y0, x0 + W, y0 + H], radius=24, fill=col)
    fg = (20, 20, 22, 255) if e.get("color") == "yellow" else (255, 255, 255, 255)
    t1 = e.get("title", "RED CARD").upper(); t2 = e["text"].upper()
    ct(dl, side // 2, y0 + int(H * 0.26), t1, af(side * 0.058), fg)
    fs = fitw(t2, af, int(W * 0.84), int(side * 0.052))
    ct(dl, side // 2, y0 + int(H * 0.50), t2, af(fs), fg)
    layer = layer.rotate(8, resample=Image.BICUBIC, center=(side // 2, side // 2))
    im.alpha_composite(layer)
    return im


# ── loading ─────────────────────────────────────────────────────────────────
def f_loading(e, variant, side):
    im = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    fg = _ink(variant)
    label = e["text"].upper()
    ct(d, side // 2, int(side * 0.33), label,
       load_font("geo", fitw(label, lambda s: load_font("geo", s), int(side * 0.8),
                             int(side * 0.06))), fg)
    W = int(side * 0.66); H = int(side * 0.075); x0 = (side - W) // 2; y0 = int(side * 0.48)
    d.rounded_rectangle([x0, y0, x0 + W, y0 + H], radius=H // 2, outline=fg,
                        width=int(side * 0.006))
    pct = int(e.get("pct", 47))
    fillw = max(H, int(W * pct / 100))
    d.rounded_rectangle([x0 + 6, y0 + 6, x0 + fillw, y0 + H - 6], radius=H // 2, fill=GOLD)
    ct(d, side // 2, y0 + H + int(side * 0.03), f"{pct} %  —  {e.get('sub','')}",
       load_font("geo", side * 0.033), fg)
    return im


# ── error 404 ───────────────────────────────────────────────────────────────
def f_error(e, variant, side):
    im = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    W = int(side * 0.82); H = int(side * 0.56); x0 = (side - W) // 2; y0 = (side - H) // 2
    d.rounded_rectangle([x0, y0, x0 + W, y0 + H], radius=16, fill=(24, 26, 32, 255))
    bar = int(H * 0.14)
    d.rounded_rectangle([x0, y0, x0 + W, y0 + bar * 2], radius=16, fill=(40, 44, 52, 255))
    d.rectangle([x0, y0 + bar, x0 + W, y0 + bar * 2], fill=(40, 44, 52, 255))
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse([x0 + 24 + i * 42, y0 + bar * 0.5, x0 + 52 + i * 42, y0 + bar * 0.5 + 28],
                  fill=c + (255,))
    ct(d, side // 2, y0 + int(H * 0.26), e.get("code", "404"),
       load_font("code", side * 0.155), (236, 238, 244, 255))
    txt = e["text"].upper().replace(" ", "_")
    ct(d, side // 2, y0 + int(H * 0.64), txt,
       load_font("mono", fitw(txt, lambda s: load_font("mono", s), int(W * 0.86),
                              int(side * 0.05))), (120, 220, 150, 255))
    return im


# ── rx (ordonnance) ─────────────────────────────────────────────────────────
def f_rx(e, variant, side):
    im = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    W = int(side * 0.68); H = int(side * 0.74); x0 = (side - W) // 2; y0 = (side - H) // 2
    paper = (255, 255, 255, 255) if variant == "dark" else (242, 242, 244, 255)
    edge = (30, 30, 34, 255)
    d.rectangle([x0, y0, x0 + W, y0 + H], fill=paper, outline=edge, width=int(side * 0.005))
    ct(d, side // 2, y0 + int(H * 0.04), e.get("head", "ORDONNANCE").upper(),
       af(side * 0.05), edge)
    d.text((x0 + 26, y0 + int(H * 0.17)), "℞", font=af(side * 0.1), fill=edge)
    fh = load_font("hand", int(side * 0.05))
    items = e["items"]
    yy = y0 + int(H * 0.30)
    for it in items:
        d.text((x0 + int(W * 0.24), yy), "• " + it, font=fh, fill=(20, 30, 90, 255))
        yy += int(H * 0.72 / max(4, len(items)))
    d.line([x0 + int(W * 0.45), y0 + int(H * 0.9), x0 + W - 26, y0 + int(H * 0.9)],
           fill=edge, width=2)
    d.text((x0 + int(W * 0.5), y0 + int(H * 0.91)), e.get("doctor", "Dr. Bon Sens"),
           font=load_font("hand", int(side * 0.038)), fill=edge)
    return im


# ── nutrition (valeurs personnelles) ───────────────────────────────────────
def f_nutrition(e, variant, side):
    im = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    W = int(side * 0.6); H = int(side * 0.74); x0 = (side - W) // 2; y0 = (side - H) // 2
    paper = (255, 255, 255, 255) if variant == "dark" else (242, 242, 244, 255)
    ink = (0, 0, 0, 255)
    d.rectangle([x0, y0, x0 + W, y0 + H], fill=paper, outline=ink, width=int(side * 0.006))
    ct(d, side // 2, y0 + int(H * 0.035), e.get("title", "VALEURS PERSONNELLES").upper(),
       af(side * 0.05), ink)
    d.line([x0 + 20, y0 + int(H * 0.18), x0 + W - 20, y0 + int(H * 0.18)], fill=ink,
           width=int(side * 0.012))
    rows = e["rows"]
    fy = af(side * 0.038); fr = af(side * 0.038, reg=True)
    yy = y0 + int(H * 0.23); step = int(H * 0.72 / max(5, len(rows)))
    for name, val in rows:
        d.text((x0 + 28, yy), name, font=fr, fill=ink)
        d.text((x0 + W - 28, yy), val, font=fy, fill=ink, anchor="ra")
        d.line([x0 + 20, yy + step - 8, x0 + W - 20, yy + step - 8], fill=ink, width=2)
        yy += step
    return im


DISPATCH = {"caution": f_caution, "care": f_care, "card": f_card, "loading": f_loading,
            "error": f_error, "rx": f_rx, "nutrition": f_nutrition}


def render(entry, variant, side=4500):
    return DISPATCH[entry["format"]](entry, variant, side)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="produits/formats")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--format", default="")
    ap.add_argument("--data", default="data/formats.json")
    ap.add_argument("--variant", default="both", choices=["both", "dark", "light"])
    args = ap.parse_args()

    data = json.load(open(args.data, encoding="utf-8"))
    entries = data["entries"]
    sel = set(args.only.split(",")) if args.only else None
    items = [e for e in entries
             if (not sel or e["id"] in sel) and (not args.format or e["format"] == args.format)]

    if args.sheet:
        cols = 4
        cell = 560
        rows = (len(items) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, rows * cell), (235, 235, 238))
        dd = ImageDraw.Draw(sheet)
        lab = af(15, reg=True)
        for i, e in enumerate(items):
            v = "light" if (i % 5 == 4) else "dark"
            im = render(e, v, side=1200)
            im.thumbnail((cell - 36, cell - 56))
            bgc = (255, 255, 255) if v == "dark" else (34, 34, 38)
            bg = Image.new("RGB", im.size, bgc)
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 18, r * cell + 18))
            dd.text((c * cell + 18, r * cell + cell - 28), f"{e['id'][:30]} [{v}]",
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
            render(e, v).save(os.path.join(args.out, f"{e['id']}__{v}.png"), dpi=(300, 300))
            n += 1
    print(f"{n} fichiers ({len(items)} × {len(variants)} variantes) → {args.out}")


if __name__ == "__main__":
    main()
