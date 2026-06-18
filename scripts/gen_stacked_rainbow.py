#!/usr/bin/env python3
"""
gen_stacked_rainbow.py — un même mot écrit N fois en empilement arc-en-ciel.

Chaque ligne = une couleur de l'arc-en-ciel (rouge → violet, ROYGBIV).
Les lignes se chevauchent légèrement pour un effet de « fondu d'écriture ».
Contour noir, fond transparent, haute résolution.

Exemple :
    python scripts/gen_stacked_rainbow.py --text COLORLESS \
        --font-path assets/fonts/Anton.ttf --out produits/hidden \
        --sheet /tmp/colorless_stack.png
"""
import argparse
import colorsys
import os
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


def rainbow_colors(n):
    """n couleurs réparties du rouge au violet (ROYGBIV)."""
    colors = []
    for i in range(n):
        hue = 0.83 * (i / max(n - 1, 1))
        r, g, b = colorsys.hsv_to_rgb(hue, 0.92, 0.97)
        colors.append((int(r * 255), int(g * 255), int(b * 255), 255))
    return colors


def render(text, layers, overlap, color_mode, font_path, W=2400, pad=120):
    text = text.upper().strip()

    fsize = 480
    tmp = Image.new("RGBA", (10, 10))
    td = ImageDraw.Draw(tmp)
    font = load_font(font_path, fsize)
    while fsize > 30:
        font = load_font(font_path, fsize)
        if td.textlength(text, font=font) <= W - 2 * pad:
            break
        fsize = int(fsize * 0.92)

    asc, desc = font.getmetrics()
    line_h = asc + desc
    sw = max(3, int(fsize * 0.05))
    step = int(line_h * (1.0 - overlap))
    H = pad + step * (layers - 1) + line_h + pad

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    if color_mode == "rainbow":
        colors = rainbow_colors(layers)
    else:
        try:
            base = ImageColor.getrgb(color_mode) + (255,)
        except ValueError:
            base = (230, 57, 70, 255)
        colors = [base] * layers

    tw = int(td.textlength(text, font=font))
    x = (W - tw) // 2

    # Dessiner de bas en haut pour que le rouge (couche 0, i=0) soit au-dessus
    for i in reversed(range(layers)):
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ld = ImageDraw.Draw(layer)
        y = pad + i * step
        ld.text((x, y), text, font=font, fill=colors[i],
                stroke_width=sw, stroke_fill=BLACK)
        img = Image.alpha_composite(img, layer)

    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True, help="mot/phrase (ex. COLORLESS)")
    ap.add_argument("--layers", type=int, default=7, help="nombre de répétitions (défaut 7)")
    ap.add_argument("--overlap", type=float, default=0.18,
                    help="chevauchement 0=aucun 0.5=mi-ligne (défaut 0.18)")
    ap.add_argument("--colors", default="rainbow", help="rainbow ou couleur hex")
    ap.add_argument("--font-path", default="")
    ap.add_argument("--out", default="produits/hidden")
    ap.add_argument("--name", default="")
    ap.add_argument("--sheet", default="")
    args = ap.parse_args()

    img = render(args.text, args.layers, args.overlap, args.colors, args.font_path)
    name = args.name or f"{args.text.lower()}_stack_{args.colors}"
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
