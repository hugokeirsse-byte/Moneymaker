#!/usr/bin/env python3
"""
gen_hidden_message.py — typographie « message caché » (trompe-l'œil de lecture).

Un mot/une phrase se lit normalement, mais certaines lettres — surlignées dans
une couleur d'accent (contour noir) — forment, lues seules, un SECOND message
(souvent une vanne). Ex. : « fri[ENDS]hip », « [BUTT]erfly », « [ANAL]ysis ».

Les lettres surlignées sont trouvées comme SOUS-SÉQUENCE de --text correspondant
à --hidden (1re occurrence, dans l'ordre). Le reste est en gris discret pour
reculer ; les lettres cachées ressortent et l'œil les relie tout seul.

0€, aucune IA : rendu Pillow, fond transparent, haute résolution.

Exemples :
    python scripts/gen_hidden_message.py --text BUTTERFLY --hidden BUTT \
        --font-path assets/fonts/Anton.ttf --out produits/hidden --sheet /tmp/b.png
    python scripts/gen_hidden_message.py --text FRIENDSHIP --hidden ENDS \
        --color "#e63946" --out produits/hidden
"""
import argparse
import os
import sys

from PIL import Image, ImageColor, ImageDraw, ImageFont

GREY = (150, 150, 150, 255)
BLACK = (15, 15, 15, 255)


def load_font(font_path, size):
    for p in (font_path, "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if p and os.path.isfile(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:  # noqa: BLE001
                pass
    return ImageFont.load_default()


def highlight_positions(text, hidden):
    """Indices de --text formant --hidden en sous-séquence (1re occurrence)."""
    h = "".join(hidden.split()).lower()
    if not h:
        return set()
    hl, j = set(), 0
    for i, ch in enumerate(text):
        if j < len(h) and ch.lower() == h[j]:
            hl.add(i)
            j += 1
    return hl if j == len(h) else set()


def render(text, hidden, accent, font_path, W=2200, pad=120):
    hl = highlight_positions(text, hidden)
    if not hl:
        print(f"⚠️  '{hidden}' n'est pas une sous-séquence de '{text}' — rien surligné",
              file=sys.stderr)

    # taille de police pour tenir dans la largeur
    fsize = 520
    tmp = Image.new("RGBA", (10, 10))
    td = ImageDraw.Draw(tmp)
    sw = 1
    total = 0
    font = load_font(font_path, fsize)
    while fsize > 40:
        font = load_font(font_path, fsize)
        sw = max(3, int(fsize * 0.05))
        widths = [td.textlength(c, font=font) for c in text]
        total = sum(widths) + sw * 2
        if total <= W - 2 * pad:
            break
        fsize = int(fsize * 0.92)
    asc, desc = font.getmetrics()
    H = asc + desc + 2 * pad + sw * 2

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = (W - (total - sw * 2)) / 2
    y = pad + sw
    for i, ch in enumerate(text):
        if i in hl:                       # lettre cachée : accent + contour noir, gras
            d.text((x, y), ch, font=font, fill=accent,
                   stroke_width=sw, stroke_fill=BLACK)
        else:                              # lettre de couverture : gris discret
            d.text((x, y), ch, font=font, fill=GREY)
        x += td.textlength(ch, font=font)
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--text", required=True, help="phrase visible (ex. BUTTERFLY)")
    ap.add_argument("--hidden", required=True, help="message caché (ex. BUTT)")
    ap.add_argument("--color", default="#e63946", help="couleur d'accent (hex ou nom)")
    ap.add_argument("--font-path", default="")
    ap.add_argument("--out", default="produits/hidden")
    ap.add_argument("--name", default="")
    ap.add_argument("--sheet", default="")
    args = ap.parse_args()

    try:
        accent = ImageColor.getrgb(args.color) + (255,)
    except ValueError:
        accent = (230, 57, 70, 255)

    img = render(args.text, args.hidden, accent, args.font_path)
    name = args.name or f"{args.text.lower()}_{args.hidden.lower()}_hidden"
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
