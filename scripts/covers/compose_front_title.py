#!/usr/bin/env python3
"""
Composition FRONT seule avec un titre unique centré et INTÉGRÉ (ombre douce +
léger halo derrière, pour ne pas faire « sticker plaqué »). Conçu pour la
couverture « 404 » (concept marionnette) : le titre est placé dans une bande
vide (au-dessus du personnage, sous la croix) et ne couvre ni l'un ni l'autre.

Sortie : cover_front.jpg (1600x2560, RVB).

Usage :
  python compose_front_title.py --art art.png --title 404 --author "SHIRO KEGESU" \
      --center 0.30 --cap 0.135 --out output/front
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


def build(art_path, title, author, out, center_frac, cap_frac):
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

    # positions des glyphes (centré)
    probe = ImageDraw.Draw(base)
    total = text_w(probe, title, tf, tr)
    sx = cx - total / 2

    def stamp(layer_draw, fill):
        xx = sx
        for ch in title:
            layer_draw.text((xx, top), ch, font=tf, fill=fill)
            xx += layer_draw.textlength(ch, font=tf) + tr

    # 1) ombre douce sombre (intégration « lettre derrière »)
    shadow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    stamp(ImageDraw.Draw(shadow), (0, 0, 0, 205))
    shadow = shadow.filter(ImageFilter.GaussianBlur(px(6)))
    base = Image.alpha_composite(base.convert("RGBA"), shadow).convert("RGB")

    # 2) léger halo rouge (accent, intégration lumineuse)
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    stamp(ImageDraw.Draw(glow), RED + (120,))
    glow = glow.filter(ImageFilter.GaussianBlur(px(4)))
    base = Image.alpha_composite(base.convert("RGBA"), glow).convert("RGB")

    # 3) titre net par-dessus (blanc chaud)
    d = ImageDraw.Draw(base)
    draw_tracked_center(d, cx, top, title, tf, (247, 240, 235), tr)

    # auteur en bas
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
    a = ap.parse_args()
    build(a.art, a.title, a.author, a.out, a.center, a.cap)


if __name__ == "__main__":
    main()
