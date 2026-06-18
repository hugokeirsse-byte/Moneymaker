#!/usr/bin/env python3
"""
gen_decomposition.py — effet « le mot se consume ».

Le mot est répété en empilement ; chaque ligne perd une lettre depuis le début.
Aligné à droite : DEPRESSION → EPRESSION → PRESSION → ... → N.
Idéal pour des mots émotionnels (DEPRESSION, ANXIETY, BURNOUT...).
Rendu Pillow, fond transparent, haute résolution.

Exemple :
    python scripts/gen_decomposition.py --text DEPRESSION \
        --font-path assets/fonts/Anton.ttf --out produits/hidden \
        --sheet /tmp/dep.png
"""
import argparse
import os
import random
import sys

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


def render(text, color, font_path, W=1800, seed=42):
    rng = random.Random(seed)
    text = text.upper().strip()
    n = len(text)
    pad = 80
    fsize = 260
    tmp = Image.new("RGBA", (10, 10))
    td = ImageDraw.Draw(tmp)
    while fsize > 24:
        font = load_font(font_path, fsize)
        if td.textlength(text, font=font) <= W - 2 * pad:
            break
        fsize = int(fsize * 0.92)
    font = load_font(font_path, fsize)
    asc, desc = font.getmetrics()
    line_h = asc + desc
    gap = int(line_h * 0.06)
    sw = max(2, int(fsize * 0.035))
    H = n * (line_h + gap) + 2 * pad
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i in range(n):
        fragment = text[i:]
        w = int(td.textlength(fragment, font=font))
        # Légère variation X pour effet organique
        x = W - pad - w + rng.randint(-18, 6)
        y = pad + i * (line_h + gap)
        d.text((x, y), fragment, font=font, fill=color,
               stroke_width=sw, stroke_fill=BLACK)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True, help="mot à décomposer (ex. DEPRESSION)")
    ap.add_argument("--color", default="#0f0f0f", help="couleur du texte (hex)")
    ap.add_argument("--font-path", default="")
    ap.add_argument("--out", default="produits/hidden")
    ap.add_argument("--name", default="")
    ap.add_argument("--sheet", default="")
    args = ap.parse_args()
    try:
        color = ImageColor.getrgb(args.color) + (255,)
    except ValueError:
        color = (15, 15, 15, 255)
    img = render(args.text, color, args.font_path)
    name = args.name or f"{args.text.lower()}_decomposition"
    os.makedirs(args.out, exist_ok=True)
    out_path = os.path.join(args.out, f"{name}.png")
    img.save(out_path, dpi=(300, 300))
    print(f"{out_path}  ({img.width}x{img.height})")
    if args.sheet:
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        bg = Image.new("RGB", img.size, (245, 245, 245))
        bg.paste(img, (0, 0), img)
        bg.save(args.sheet, quality=90)
        print("aperçu:", args.sheet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
