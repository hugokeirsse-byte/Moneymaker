#!/usr/bin/env python3
"""
Composition FRONT seule avec un titre unique centré et INTÉGRÉ. Deux styles :
  - solid : titre net avec ombre douce + léger halo rouge (intégration discrète).
  - cloud : titre lumineux et brumeux, comme « dessiné dans les nuages » (bords
            vaporeux, halo diffus) — pour que les fils semblent en descendre.

Conçu pour la couverture « 404 » (concept marionnette) : le titre est placé
dans une bande vide (les nuages / au-dessus du personnage) sans couvrir la
figure.

Sortie : cover_front.jpg (1600x2560, RVB).

Usage :
  python compose_front_title.py --art art.png --title 404 --author "SHIRO KEGESU" \
      --center 0.16 --cap 0.135 --style cloud --out output/front
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

    if style == "cloud":
        # 404 « dessiné dans les nuages » : superposition de halos flous, pas de
        # bord dur, légère teinte froide — lumineux et vaporeux.
        white = (255, 255, 250, 255)
        # halo très large (lueur diffuse dans les nuages)
        wide = _stamp_layer(base.size, title, tf, tr, sx, top, white)
        wide = _reduce_alpha(wide.filter(ImageFilter.GaussianBlur(px(16))), 0.55)
        base = Image.alpha_composite(base.convert("RGBA"), wide).convert("RGB")
        # halo moyen
        mid = _stamp_layer(base.size, title, tf, tr, sx, top, white)
        mid = _reduce_alpha(mid.filter(ImageFilter.GaussianBlur(px(6))), 0.75)
        base = Image.alpha_composite(base.convert("RGBA"), mid).convert("RGB")
        # cœur adouci (légèrement flou, légèrement transparent -> fondu nuageux)
        core = _stamp_layer(base.size, title, tf, tr, sx, top, (255, 255, 252, 235))
        core = core.filter(ImageFilter.GaussianBlur(px(1.4)))
        base = Image.alpha_composite(base.convert("RGBA"), core).convert("RGB")
    else:
        # solid : ombre douce sombre + léger halo rouge + titre net.
        shadow = _stamp_layer(base.size, title, tf, tr, sx, top, (0, 0, 0, 205))
        shadow = shadow.filter(ImageFilter.GaussianBlur(px(6)))
        base = Image.alpha_composite(base.convert("RGBA"), shadow).convert("RGB")
        glow = _stamp_layer(base.size, title, tf, tr, sx, top, RED + (120,))
        glow = glow.filter(ImageFilter.GaussianBlur(px(4)))
        base = Image.alpha_composite(base.convert("RGBA"), glow).convert("RGB")
        d = ImageDraw.Draw(base)
        draw_tracked_center(d, cx, top, title, tf, (247, 240, 235), tr)

    # auteur en bas (net, dans les deux styles)
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
    ap.add_argument("--style", default="solid", choices=["solid", "cloud"])
    a = ap.parse_args()
    build(a.art, a.title, a.author, a.out, a.center, a.cap, a.style)


if __name__ == "__main__":
    main()
