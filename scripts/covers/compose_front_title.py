#!/usr/bin/env python3
"""
Composition FRONT seule avec un titre unique centré et INTÉGRÉ. Styles :
  - solid : titre net, ombre douce + léger halo rouge (intégration discrète).
  - cloud : titre lumineux et brumeux, comme dessiné dans un nuage.
  - sky   : titre comme de la LUMIÈRE qui perce les nuages (trouées claires en
            forme de chiffres) — intégré au ciel mais resté lisible ; les fils
            semblent en descendre.

Sortie : cover_front.jpg (1600x2560, RVB).

Usage :
  python compose_front_title.py --art art.png --title 404 --author "SHIRO KEGESU" \
      --center 0.135 --cap 0.15 --style sky --out output/front
"""
from __future__ import annotations

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose_cover import (  # noqa: E402
    DPI, px, font, F_TITLE, INK_WHITE, RED, FACE_SAFETY_MM,
    fit_cover, add_grain, text_w,
)


def draw_tracked_center(d, cx, y, s, f, fill, tracking):
    total = text_w(d, s, f, tracking)
    x = cx - total / 2
    for ch in s:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + tracking


def _reduce_alpha(img, factor):
    r, g, b, a = img.split()
    a = a.point(lambda v: int(v * factor))
    return Image.merge("RGBA", (r, g, b, a))


def _stamp_layer(base_size, title, tf, tr, sx, top, fill):
    layer = Image.new("RGBA", base_size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    xx = sx
    for ch in title:
        d.text((xx, top), ch, font=tf, fill=fill)
        xx += d.textlength(ch, font=tf) + tr
    return layer


def build(art_path, title, author, out, center_frac, cap_frac, style):
    W, H = 1600, 2560
    base = fit_cover(Image.open(art_path).convert("RGB"), W, H)
    base = add_grain(base, 0.04)
    cx = W / 2
    cap = int(H * cap_frac)
    tf = font(F_TITLE, int(cap * 1.38))
    tr = int(cap * 0.05)
    asc, desc = tf.getmetrics()
    line_h = asc + desc
    top = int(H * center_frac - line_h / 2)
    probe = ImageDraw.Draw(base)
    total = text_w(probe, title, tf, tr)
    sx = cx - total / 2

    def layer(fill, blur, alpha=1.0):
        lyr = _stamp_layer(base.size, title, tf, tr, sx, top, fill)
        if blur:
            lyr = lyr.filter(ImageFilter.GaussianBlur(px(blur)))
        if alpha < 1.0:
            lyr = _reduce_alpha(lyr, alpha)
        return lyr

    def over(b, lyr):
        return Image.alpha_composite(b.convert("RGBA"), lyr).convert("RGB")

    if style == "sky":
        # 404 = lumière perçant les nuages : halos lumineux superposés + cœur
        # doux (lisible). Teinte légèrement chaude/pâle.
        warm = (255, 253, 246, 255)
        base = over(base, layer(warm, 18, 0.55))   # bloom large
        base = over(base, layer(warm, 7, 0.85))    # halo moyen
        base = over(base, layer((255, 255, 250, 255), 2.4))  # cœur doux
        base = over(base, layer((255, 255, 252, 255), 0.8, 0.55))  # net léger (lisibilité)
    elif style == "cloud":
        white = (255, 255, 250, 255)
        base = over(base, layer(white, 16, 0.55))
        base = over(base, layer(white, 6, 0.75))
        base = over(base, layer((255, 255, 252, 235), 1.4))
    else:  # solid
        base = over(base, layer((0, 0, 0, 205), 6))
        base = over(base, layer(RED + (120,), 4))
        d = ImageDraw.Draw(base)
        draw_tracked_center(d, cx, top, title, tf, (247, 240, 235), tr)

    # auteur en bas (net, dans tous les styles)
    d = ImageDraw.Draw(base)
    af = font(F_TITLE, int(H * 0.042 * 1.38))
    ay = H - px(FACE_SAFETY_MM) - int(H * 0.055)
    draw_tracked_center(d, cx, ay, author, af, INK_WHITE, int(H * 0.012))

    os.makedirs(out, exist_ok=True)
    path = os.path.join(out, "cover_front.jpg")
    base.convert("RGB").save(path, "JPEG", quality=92, dpi=(DPI, DPI))
    print("->", path)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", required=True)
    ap.add_argument("--title", default="404")
    ap.add_argument("--author", default="SHIRO KEGESU")
    ap.add_argument("--out", default="output/front")
    ap.add_argument("--center", type=float, default=0.30)
    ap.add_argument("--cap", type=float, default=0.135)
    ap.add_argument("--style", default="solid", choices=["solid", "cloud", "sky"])
    a = ap.parse_args()
    build(a.art, a.title, a.author, a.out, a.center, a.cap, a.style)


if __name__ == "__main__":
    main()
