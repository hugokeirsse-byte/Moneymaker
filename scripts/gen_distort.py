#!/usr/bin/env python3
"""
gen_distort.py — effet « le mot se déforme » (mental-health / glitch aesthetic).

Le mot est répété N fois, empilé. Ligne après ligne, les lettres se DÉFORMENT
de plus en plus (rotation, cisaillement, étirement, ondulation, dérive) — elles
ne disparaissent jamais. La 1re ligne est nette, la dernière presque illisible.
Idéal pour DEPRESSION, ANXIETY, BURNOUT, OVERWHELMED...

Rendu Pillow + numpy, fond TRANSPARENT, haute résolution. Reproductible (seed).

Exemple :
    python scripts/gen_distort.py --text DEPRESSION --lines 8 \
        --font-path assets/fonts/Anton.ttf --out produits/hidden --sheet /tmp/d.png
"""
import argparse
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageFont

BLACK = (15, 15, 15, 255)


def load_font(font_path, size):
    for p in (font_path, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if p and os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def render_glyph(ch, font, color, sw, pad=40):
    """Une lettre sur sa propre tuile RGBA (avec marge pour la rotation)."""
    tmp = Image.new("RGBA", (10, 10))
    w = int(ImageDraw.Draw(tmp).textlength(ch, font=font))
    asc, desc = font.getmetrics()
    h = asc + desc
    tile = Image.new("RGBA", (w + 2 * pad, h + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(tile)
    d.text((pad, pad), ch, font=font, fill=color, stroke_width=sw, stroke_fill=BLACK)
    return tile, w


def distort_tile(tile, strength, rng):
    """Rotation + cisaillement + étirement vertical, proportionnels à strength."""
    if strength <= 0.001:
        return tile
    # cisaillement horizontal + étirement vertical via transformation affine
    shear = rng.uniform(-0.30, 0.30) * strength
    scale_y = 1.0 + rng.uniform(-0.18, 0.42) * strength
    scale_x = 1.0 + rng.uniform(-0.14, 0.14) * strength
    w, h = tile.size
    nh = max(1, int(h * scale_y))
    nw = max(1, int(w * scale_x))
    t = tile.resize((nw, nh), Image.BICUBIC)
    # cisaillement : x' = x + shear*y
    a, b, c = scale_x_unused = 1, shear, -shear * nh / 2
    t = t.transform((int(nw + abs(shear) * nh), nh), Image.AFFINE,
                    (1, shear, c, 0, 1, 0), resample=Image.BICUBIC)
    # rotation
    ang = rng.uniform(-18, 18) * strength
    t = t.rotate(ang, expand=True, resample=Image.BICUBIC)
    return t


def wave_warp(img, strength, rng):
    """Ondulation liquide (déplacement sinusoïdal) sur toute la ligne."""
    if strength <= 0.02:
        return img
    arr = np.array(img)
    h, w = arr.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    dx = np.zeros((h, w), np.float32)
    dy = np.zeros((h, w), np.float32)
    for _ in range(2):
        amp = strength * rng.uniform(3, 7)
        fx = rng.uniform(1.5, 4.0) / max(w, 1) * 2 * math.pi
        fy = rng.uniform(1.5, 4.0) / max(h, 1) * 2 * math.pi
        ph = rng.uniform(0, 2 * math.pi)
        dx += amp * np.sin(fy * yy + ph)
        dy += amp * np.sin(fx * xx + ph)
    sx = np.clip(xx + dx, 0, w - 1).astype(np.int32)
    sy = np.clip(yy + dy, 0, h - 1).astype(np.int32)
    return Image.fromarray(arr[sy, sx])


def render_line(text, font, color, sw, strength, rng, W):
    """Une ligne du mot, lettres déformées, centrée, largeur W."""
    asc, desc = font.getmetrics()
    base_h = asc + desc
    line_h = int(base_h * 2.2)  # marge verticale pour débordements
    canvas = Image.new("RGBA", (W, line_h), (0, 0, 0, 0))
    # positionnement séquentiel avec jitter
    tiles = []
    total_w = 0
    for ch in text:
        if ch == " ":
            tiles.append(("space", int(base_h * 0.4)))
            total_w += int(base_h * 0.4)
            continue
        glyph, gw = render_glyph(ch, font, color, sw)
        glyph = distort_tile(glyph, strength, rng)
        tiles.append((glyph, gw))
        total_w += gw
    spacing = int(base_h * 0.02)
    total_w += spacing * (len(tiles) - 1)
    x = (W - total_w) // 2
    cy = line_h // 2
    for item, gw in tiles:
        if item == "space":
            x += gw + spacing
            continue
        glyph = item
        jx = int(rng.uniform(-0.05, 0.03) * base_h * strength)
        jy = int(rng.uniform(-0.16, 0.16) * base_h * strength)
        # placer la tuile centrée verticalement sur la ligne de base
        gy = cy - glyph.height // 2 + jy
        gx = x + jx - (glyph.width - gw) // 2
        canvas.alpha_composite(glyph, (max(0, gx), max(0, gy)))
        x += gw + spacing
    canvas = wave_warp(canvas, strength, rng)
    return canvas


def render(text, lines, color, font_path, max_strength, W=2000, seed=7):
    text = text.upper().strip()
    rng = random.Random(seed)
    pad = 80
    fsize = 300
    tmp = Image.new("RGBA", (10, 10))
    td = ImageDraw.Draw(tmp)
    while fsize > 24:
        f = load_font(font_path, fsize)
        if td.textlength(text, font=f) <= W - 2 * pad - 200:
            break
        fsize = int(fsize * 0.92)
    font = load_font(font_path, fsize)
    sw = max(2, int(fsize * 0.04))
    asc, desc = font.getmetrics()
    line_h = int((asc + desc) * 2.2)
    step = int((asc + desc) * 1.02)  # chevauchement vertical léger
    H = pad * 2 + step * (lines - 1) + line_h
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    for i in range(lines):
        s = (i / max(lines - 1, 1)) * max_strength
        line = render_line(text, font, color, sw, s, rng, W)
        y = pad + i * step - (line_h - step) // 2
        img.alpha_composite(line, (0, y))
    # rogner les marges transparentes
    bbox = img.getbbox()
    if bbox:
        img = img.crop((0, max(0, bbox[1] - pad // 2), W, min(H, bbox[3] + pad // 2)))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True, help="mot à déformer (ex. DEPRESSION)")
    ap.add_argument("--lines", type=int, default=8, help="nombre de lignes empilées")
    ap.add_argument("--strength", type=float, default=1.0,
                    help="intensité max de déformation (défaut 1.0)")
    ap.add_argument("--color", default="#0f0f0f", help="couleur du texte (hex)")
    ap.add_argument("--font-path", default="")
    ap.add_argument("--out", default="produits/hidden")
    ap.add_argument("--name", default="")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()
    try:
        color = ImageColor.getrgb(args.color) + (255,)
    except ValueError:
        color = (15, 15, 15, 255)
    img = render(args.text, args.lines, color, args.font_path, args.strength, seed=args.seed)
    name = args.name or f"{args.text.lower()}_distort"
    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, f"{name}.png")
    img.save(out_path, dpi=(300, 300))
    print(f"{out_path}  ({img.width}x{img.height})")
    if args.sheet:
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        bg = Image.new("RGB", img.size, (245, 245, 245))
        bg.paste(img, (0, 0), img)
        bg.save(args.sheet, quality=92)
        print("aperçu:", args.sheet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
