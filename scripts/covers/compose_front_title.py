#!/usr/bin/env python3
"""
Composition FRONT : titre posé (optionnel), accroche 3 lignes (optionnel),
et/ou « 404 » brodé dans le dos (optionnel).

- --title 404 --style solid|cloud|sky  (NONE ou espace = pas de titre)
- --tagline "L1|L2|L3"  (lignes séparées par des barres verticales)
- --emb-text 404  (broderie dans le dos)

Sortie : cover_front.jpg (1600x2560, RVB).
"""
from __future__ import annotations

import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose_cover import (  # noqa: E402
    DPI, px, font, F_TITLE, F_ITAL, INK_WHITE, RED, FACE_SAFETY_MM,
    fit_cover, add_grain, text_w,
)


def _active(v):
    return bool(v and v.strip() and v.strip().upper() != "NONE")


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


def draw_embroidery(base, text, cx_f, cy_f, h_f):
    W, H = base.size
    cap = int(H * h_f)
    f = font(F_ITAL, int(cap * 1.5))
    d0 = ImageDraw.Draw(base)
    tw = d0.textlength(text, font=f)
    x = W * cx_f - tw / 2
    y = H * cy_f - cap / 2
    layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
    dl = ImageDraw.Draw(layer)
    dl.text((x + px(0.5), y + px(0.6)), text, font=f, fill=(18, 24, 34, 160))
    dl.text((x - px(0.4), y - px(0.4)), text, font=f, fill=(240, 236, 222, 120))
    dl.text((x, y), text, font=f, fill=(223, 217, 199, 235))
    layer = layer.filter(ImageFilter.GaussianBlur(px(0.4)))
    return Image.alpha_composite(base.convert("RGBA"), layer).convert("RGB")


def draw_tagline(base, lines, cy_f, h_f):
    """Accroche : petites capitales, tracking large, blanc cassé 85 %, ombre douce."""
    W, H = base.size
    cx = W / 2
    cap = int(H * h_f)
    f = font(F_TITLE, int(cap * 1.38))
    tr = int(cap * 0.34)
    lh = int(cap * 1.75)
    total_h = lh * len(lines)
    y0 = int(H * cy_f - total_h / 2)

    def stamp(fill):
        lyr = Image.new("RGBA", base.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(lyr)
        y = y0
        for ln in lines:
            s = ln.upper()
            tw = text_w(d, s, f, tr)
            x = cx - tw / 2
            for ch in s:
                d.text((x, y), ch, font=f, fill=fill)
                x += d.textlength(ch, font=f) + tr
            y += lh
        return lyr

    shadow = stamp((0, 0, 0, 150)).filter(ImageFilter.GaussianBlur(px(3)))
    base = Image.alpha_composite(base.convert("RGBA"), shadow).convert("RGB")
    white = stamp(INK_WHITE + (217,))
    base = Image.alpha_composite(base.convert("RGBA"), white).convert("RGB")
    return base


def build(art_path, title, author, out, center_frac, cap_frac, style,
          emb_text, emb_cx, emb_cy, emb_h, tagline, tag_cy, tag_h):
    W, H = 1600, 2560
    base = fit_cover(Image.open(art_path).convert("RGB"), W, H)
    base = add_grain(base, 0.04)
    cx = W / 2

    if _active(emb_text):
        base = draw_embroidery(base, emb_text.strip(), emb_cx, emb_cy, emb_h)

    if _active(title):
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
            warm = (255, 253, 246, 255)
            base = over(base, layer(warm, 18, 0.55))
            base = over(base, layer(warm, 7, 0.85))
            base = over(base, layer((255, 255, 250, 255), 2.4))
            base = over(base, layer((255, 255, 252, 255), 0.8, 0.55))
        elif style == "cloud":
            white = (255, 255, 250, 255)
            base = over(base, layer(white, 16, 0.55))
            base = over(base, layer(white, 6, 0.75))
            base = over(base, layer((255, 255, 252, 235), 1.4))
        else:
            base = over(base, layer((0, 0, 0, 205), 6))
            base = over(base, layer(RED + (120,), 4))
            d = ImageDraw.Draw(base)
            draw_tracked_center(d, cx, top, title, tf, (247, 240, 235), tr)

    if _active(tagline):
        lines = [s for s in tagline.split("|") if s.strip()]
        if lines:
            base = draw_tagline(base, lines, tag_cy, tag_h)

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
    ap.add_argument("--center", type=float, default=0.115)
    ap.add_argument("--cap", type=float, default=0.135)
    ap.add_argument("--style", default="solid", choices=["solid", "cloud", "sky"])
    ap.add_argument("--emb-text", dest="emb_text", default="")
    ap.add_argument("--emb-cx", dest="emb_cx", type=float, default=0.5)
    ap.add_argument("--emb-cy", dest="emb_cy", type=float, default=0.40)
    ap.add_argument("--emb-h", dest="emb_h", type=float, default=0.05)
    ap.add_argument("--tagline", default="")
    ap.add_argument("--tag-cy", dest="tag_cy", type=float, default=0.255)
    ap.add_argument("--tag-h", dest="tag_h", type=float, default=0.024)
    a = ap.parse_args()
    build(a.art, a.title, a.author, a.out, a.center, a.cap, a.style,
          a.emb_text, a.emb_cx, a.emb_cy, a.emb_h, a.tagline, a.tag_cy, a.tag_h)


if __name__ == "__main__":
    main()
