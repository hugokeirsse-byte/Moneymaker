#!/usr/bin/env python3
"""
gen_symbol_mosaic.py — mosaïque TONALE : un grand symbole (et un mot dessous)
rendus par une nuée de petits symboles, dont la DENSITÉ crée les ombres et le
volume. Aucune IA, aucun coût : tout est dessiné avec Pillow.

Principe (pas une grille !) :
  1) on construit une carte de tons (silhouette pleine du symbole + mot dessous,
     floutée) : sombre = dense, clair = clairsemé ;
  2) on sème des milliers de petits symboles à des positions ALÉATOIRES, plus
     gros et plus serrés là où le ton est sombre, plus petits et espacés vers
     les bords qui s'estompent ;
  3) couleurs variées (teinte/valeur qui bougent d'un symbole à l'autre), les
     zones denses s'assombrissent => ombres ; les bords s'éclaircissent.

Le mot du bas (ex. « LOVE » sous le cœur) est lui aussi rempli des mêmes petits
symboles.

Symboles : peace, anarchy, heart, recycle, female, male, infinity, star.

Exemples :
    python scripts/gen_symbol_mosaic.py --symbol heart --label LOVE \
        --colors candy --font-path assets/fonts/Anton.ttf \
        --out produits/symbol_mosaics --sheet /tmp/heart.png
    python scripts/gen_symbol_mosaic.py --symbol peace --label PEACE \
        --colors rainbow --out produits/symbol_mosaics
"""
import argparse
import colorsys
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SS = 3  # suréchantillonnage des petites tuiles (anti-crénelage)


# ----------------------------------------------------------- dessin emblèmes
def draw_peace(d, box, color, w):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = (x1 - x0) / 2 - w
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=w)
    d.line([cx, cy - r, cx, cy + r], fill=color, width=w)
    dx = r * math.cos(math.radians(45))
    d.line([cx, cy, cx - dx, cy + dx], fill=color, width=w)
    d.line([cx, cy, cx + dx, cy + dx], fill=color, width=w)


def draw_anarchy(d, box, color, w):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = (x1 - x0) / 2 - w
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=w)
    top = (cx, cy - r * 0.78)
    bl = (cx - r * 0.62, cy + r * 0.72)
    br = (cx + r * 0.62, cy + r * 0.72)
    d.line([top, bl], fill=color, width=w)
    d.line([top, br], fill=color, width=w)
    d.line([cx - r * 1.15, cy + r * 0.18, cx + r * 1.15, cy + r * 0.18],
           fill=color, width=w)


def _heart_pts(box):
    x0, y0, x1, y1 = box
    sx, sy = (x1 - x0), (y1 - y0)
    pts = []
    for t in [i / 120 * 2 * math.pi for i in range(121)]:
        hx = 16 * math.sin(t) ** 3
        hy = (13 * math.cos(t) - 5 * math.cos(2 * t)
              - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((x0 + sx * (0.5 + hx / 36.0), y0 + sy * (0.46 - hy / 36.0)))
    return pts


def draw_heart(d, box, color, w):
    d.polygon(_heart_pts(box), fill=color)


def draw_recycle(d, box, color, w):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    r = (x1 - x0) / 2 - w
    for k in range(3):
        a = math.radians(90 + k * 120)
        a2 = math.radians(90 + k * 120 + 80)
        p1 = (cx + r * math.cos(a), cy - r * math.sin(a))
        p2 = (cx + r * math.cos(a2), cy - r * math.sin(a2))
        d.line([p1, p2], fill=color, width=w)
        d.line([p2, (cx + r * 0.45 * math.cos(a2), cy - r * 0.45 * math.sin(a2))],
               fill=color, width=w)


def draw_venus(d, box, color, w):
    x0, y0, x1, y1 = box
    cx = (x0 + x1) / 2
    r = (x1 - x0) / 2 - w
    top = y0 + w
    d.ellipse([cx - r * 0.6, top, cx + r * 0.6, top + r * 1.2], outline=color, width=w)
    cy = top + r * 1.2
    d.line([cx, cy, cx, y1 - w], fill=color, width=w)
    d.line([cx - r * 0.4, (cy + y1) / 2, cx + r * 0.4, (cy + y1) / 2], fill=color, width=w)


def draw_mars(d, box, color, w):
    x0, y0, x1, y1 = box
    r = (x1 - x0) / 2.6
    d.ellipse([x0 + w, y1 - 2 * r - w, x0 + 2 * r + w, y1 - w], outline=color, width=w)
    arrow_o = (x0 + 2 * r, y1 - 2 * r)
    tip = (x1 - w, y0 + w)
    d.line([arrow_o, tip], fill=color, width=w)
    d.line([tip[0] - r * 0.9, tip[1], tip[0], tip[1]], fill=color, width=w)
    d.line([tip[0], tip[1], tip[0], tip[1] + r * 0.9], fill=color, width=w)


def draw_infinity(d, box, color, w):
    x0, y0, x1, y1 = box
    cy = (y0 + y1) / 2
    r = (y1 - y0) / 2 - w
    d.ellipse([x0 + w, cy - r, x0 + w + 2 * r, cy + r], outline=color, width=w)
    d.ellipse([x1 - w - 2 * r, cy - r, x1 - w, cy + r], outline=color, width=w)


def draw_star(d, box, color, w):
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    R = (x1 - x0) / 2 - w
    pts = []
    for i in range(10):
        rad = R if i % 2 == 0 else R * 0.42
        a = math.pi / 2 + i * math.pi / 5
        pts.append((cx + rad * math.cos(a), cy - rad * math.sin(a)))
    d.polygon(pts, fill=color)


SYMBOLS = {
    "peace": draw_peace, "anarchy": draw_anarchy, "heart": draw_heart,
    "recycle": draw_recycle, "female": draw_venus, "male": draw_mars,
    "infinity": draw_infinity, "star": draw_star,
}
# fraction du trait quand on dessine la SILHOUETTE pleine (carte de tons)
SOLID = {"heart", "star"}


# ----------------------------------------------------------- couleurs
PALETTES = {
    "sunset": [(255, 94, 58), (255, 149, 5), (255, 191, 0), (214, 40, 100)],
    "ocean":  [(0, 119, 182), (0, 180, 216), (72, 202, 228), (2, 62, 138)],
    "forest": [(45, 106, 79), (82, 183, 136), (27, 67, 50), (149, 213, 178)],
    "candy":  [(247, 37, 133), (228, 0, 124), (114, 9, 183), (76, 201, 240)],
    "pride":  [(228, 3, 3), (255, 140, 0), (255, 237, 0), (0, 128, 38),
               (0, 77, 255), (117, 7, 135)],
}


def stamp_color(mode, frac, tone, rng):
    """Couleur d'un petit symbole. Plus le ton est sombre (dense), plus la
    valeur baisse => les amas forment des ombres. Teinte/valeur jitterées."""
    if mode == "black":
        g = int(18 + (1 - tone) * 90) + rng.randint(-10, 10)
        g = max(0, min(70, g))
        return (g, g, g, 255)
    if mode in PALETTES:
        base = rng.choice(PALETTES[mode])
        f = 0.6 + 0.4 * tone + rng.uniform(-0.08, 0.08)
        return (int(base[0] * f), int(base[1] * f), int(base[2] * f), 255)
    # rainbow : teinte par position horizontale + bruit, valeur ~ ton
    hue = (0.83 * frac + rng.uniform(-0.04, 0.04)) % 1.0
    val = max(0.45, min(1.0, 0.97 - 0.4 * tone + rng.uniform(-0.05, 0.05)))
    r, g, b = colorsys.hsv_to_rgb(hue, 0.9, val)
    return (int(r * 255), int(g * 255), int(b * 255), 255)


# ----------------------------------------------------------- carte de tons
def _load_font(font_path, size):
    for p in (font_path, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if p and os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:  # noqa: BLE001
                pass
    return ImageFont.load_default()


def tone_map(symbol, W, H, label, font_path, base):
    """Silhouette pleine (symbole en haut + mot en bas), floutée -> tons."""
    sil = Image.new("L", (W, H), 0)
    d = ImageDraw.Draw(sil)
    label = (label or "").strip()
    sym_h = int(H * (0.74 if label else 0.92))
    side = int(min(W, sym_h) * 0.92)
    bx = (W - side) // 2
    by = int(H * 0.03)
    w = max(2, round(side * (0.30 if symbol in SOLID else 0.085)))
    SYMBOLS[symbol]((d), (bx, by, bx + side, by + side), 255, w)

    if label:
        # lettres posées une à une avec interlettrage (sinon le flou les soude)
        fsize = int(H * 0.21)
        track = 0.22  # espace entre lettres, en fraction de fsize
        chars = list(label.upper())

        def layout(fs):
            fnt = _load_font(font_path, fs)
            widths, total = [], 0.0
            gap = fs * track
            for i, ch in enumerate(chars):
                l, t, r, b = d.textbbox((0, 0), ch, font=fnt)
                widths.append((ch, l, t, r - l))
                total += (r - l) + (gap if i < len(chars) - 1 else 0)
            return fnt, widths, total, gap

        font, widths, total, gap = layout(fsize)
        while total > W * 0.9 and fsize > 24:
            fsize = int(fsize * 0.92)
            font, widths, total, gap = layout(fsize)

        x = (W - total) / 2
        baseline = int(H * 0.80)
        for ch, l, t, cw in widths:
            d.text((x - l, baseline - t), ch, fill=255, font=font)
            x += cw + gap

    tone = sil.filter(ImageFilter.GaussianBlur(base * 0.42))
    return np.asarray(tone, dtype=np.float32) / 255.0


# ----------------------------------------------------------- tuiles
def make_tile(symbol, size, color):
    big = max(SS * 6, size * SS)
    img = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = max(SS, round(big * 0.11))
    SYMBOLS[symbol](d, (w, w, big - w, big - w), color, w)
    return img.resize((size, size), Image.LANCZOS)


# ----------------------------------------------------------- composition
def build(symbol, W=1700, H=2000, colors="rainbow", label="",
          font_path="", base=34, seed=7):
    tone = tone_map(symbol, W, H, label, font_path, base)
    rng = random.Random(seed)
    out = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    cell = max(6, base // 2)
    occ = {}

    def too_close(x, y, size):
        cx, cy = x // cell, y // cell
        for ax in range(cx - 2, cx + 3):
            for ay in range(cy - 2, cy + 3):
                for (ox, oy, os_) in occ.get((ax, ay), ()):
                    if (ox - x) ** 2 + (oy - y) ** 2 < ((size + os_) * 0.30) ** 2:
                        return True
        return False

    attempts = int(W * H / (base * base) * 9)
    placed = 0
    for _ in range(attempts):
        x = rng.randrange(W)
        y = rng.randrange(H)
        tv = float(tone[y, x])
        if tv < 0.05 or rng.random() > tv ** 0.75:
            continue
        size = int(base * (0.42 + 1.05 * tv) * rng.uniform(0.82, 1.18))
        if size < 9:
            continue
        if too_close(x, y, size):
            continue
        color = stamp_color(colors, x / W, tv, rng)
        t = make_tile(symbol, size, color)
        if rng.random() < 0.85:
            t = t.rotate(rng.uniform(-14, 14), expand=True, resample=Image.BICUBIC)
        out.alpha_composite(t, (x - t.width // 2, y - t.height // 2))
        occ.setdefault((x // cell, y // cell), []).append((x, y, size))
        placed += 1
    return out, placed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbol", default="heart", choices=list(SYMBOLS))
    ap.add_argument("--label", default="", help="mot écrit dessous, en petits symboles")
    ap.add_argument("--colors", default="rainbow")
    ap.add_argument("--base", type=int, default=34, help="taille moyenne des symboles (px)")
    ap.add_argument("--font-path", default="")
    ap.add_argument("--out", default="produits/symbol_mosaics")
    ap.add_argument("--name", default="")
    ap.add_argument("--sheet", default="")
    args = ap.parse_args()

    img, n = build(args.symbol, colors=args.colors, label=args.label,
                   font_path=args.font_path, base=args.base)
    lab = f"_{args.label.lower()}" if args.label else ""
    name = args.name or f"{args.symbol}{lab}_{args.colors}_mosaic"
    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, f"{name}.png")
    img.save(out_path, dpi=(300, 300))
    print(f"{out_path}  ({img.width}x{img.height}, {n} petits {args.symbol})")

    if args.sheet:
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        bg = Image.new("RGB", img.size, (245, 245, 245))
        bg.paste(img, (0, 0), img)
        bg.save(args.sheet, quality=90)
        print("aperçu:", args.sheet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
