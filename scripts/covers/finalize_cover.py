#!/usr/bin/env python3
"""
Finalisation KDP « 404 » : compositing définitif sur l'art validé (marionnette).
Face = version B : accroche 3 lignes en haut, titre « 404 » en dessous, auteur en bas.

Produit dans --out :
  - cover_ebook_final.jpg      (1600x2560)
  - cover_paperback_final.pdf  (wrap 4e + dos + face, fond perdu, aplati)
  - cover_paperback_final.png  (raster du wrap)
  - preview_montage.png        (4e + dos + face)
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from compose_cover import (  # noqa: E402
    DPI, px, font, FONT_DIR, F_TITLE, F_ITAL,
    INK_WHITE, RED, BACK_BG, BACK_TEXT, FACE_SAFETY_MM,
    wrap_geometry, fit_cover, add_grain, make_back_ambiance,
    draw_isbn_zone, wrap_text, text_w,
)

F_BODY = os.path.join(FONT_DIR, "Oswald-Regular.ttf")
F_BOLD = os.path.join(FONT_DIR, "Oswald-SemiBold.ttf")


# --------------------------------------------------------------------------- #
# Face (version B)
# --------------------------------------------------------------------------- #
def _stamp_lines(size, lines, f, tr, lh, cx, y0, upper, fill):
    lyr = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lyr)
    y = y0
    for ln in lines:
        s = ln.upper() if upper else ln
        tw = text_w(d, s, f, tr)
        x = cx - tw / 2
        for ch in s:
            d.text((x, y), ch, font=f, fill=fill)
            x += d.textlength(ch, font=f) + tr
        y += lh
    return lyr


def _draw_lines(base, lines, f, tr, lh, cx, y0, upper, fill, shadow=None, sblur=3):
    if shadow:
        sh = _stamp_lines(base.size, lines, f, tr, lh, cx, y0, upper, shadow)
        sh = sh.filter(ImageFilter.GaussianBlur(px(sblur)))
        base = Image.alpha_composite(base.convert("RGBA"), sh).convert("RGB")
    wl = _stamp_lines(base.size, lines, f, tr, lh, cx, y0, upper, fill)
    return Image.alpha_composite(base.convert("RGBA"), wl).convert("RGB")


def _draw_title(base, title, tf, tr, cx, top):
    sh = _stamp_lines(base.size, [title], tf, tr, 0, cx, top, False, (0, 0, 0, 205))
    sh = sh.filter(ImageFilter.GaussianBlur(px(6)))
    base = Image.alpha_composite(base.convert("RGBA"), sh).convert("RGB")
    gl = _stamp_lines(base.size, [title], tf, tr, 0, cx, top, False, RED + (120,))
    gl = gl.filter(ImageFilter.GaussianBlur(px(4)))
    base = Image.alpha_composite(base.convert("RGBA"), gl).convert("RGB")
    tx = _stamp_lines(base.size, [title], tf, tr, 0, cx, top, False, (247, 240, 235, 255))
    return Image.alpha_composite(base.convert("RGBA"), tx).convert("RGB")


def draw_front(base, rect, title, tag_lines, author):
    x0, y0, x1, y1 = rect
    fh = y1 - y0
    cx = (x0 + x1) / 2
    # accroche 3 lignes, centrée à ~11 % de la hauteur
    cap_t = int(fh * 0.024)
    ft = font(F_TITLE, int(cap_t * 1.38))
    trt = int(cap_t * 0.34)
    lht = int(cap_t * 1.75)
    tot = lht * max(1, len(tag_lines))
    ty0 = int(y0 + fh * 0.11 - tot / 2)
    base = _draw_lines(base, tag_lines, ft, trt, lht, cx, ty0, True,
                       INK_WHITE + (217,), shadow=(0, 0, 0, 150), sblur=3)
    # titre 404, centré à ~24 % de la hauteur
    cap = int(fh * 0.12)
    tf = font(F_TITLE, int(cap * 1.38))
    tr = int(cap * 0.05)
    asc, desc = tf.getmetrics()
    lh = asc + desc
    tt_top = int(y0 + fh * 0.24 - lh / 2)
    base = _draw_title(base, title, tf, tr, cx, tt_top)
    # auteur en bas
    af = font(F_TITLE, int(fh * 0.042 * 1.38))
    ay = int(y1 - px(FACE_SAFETY_MM) - fh * 0.05)
    base = _draw_lines(base, [author], af, int(fh * 0.012), 0, cx, ay, False,
                       INK_WHITE + (255,), shadow=(0, 0, 0, 140), sblur=4)
    return base


# --------------------------------------------------------------------------- #
# 4e de couverture (résumé)
# --------------------------------------------------------------------------- #
def _block_spec(style, size):
    if style == "bold":
        return font(F_BOLD, size), size
    if style == "italic":
        us = int(size * 1.18)
        return font(F_ITAL, us), us
    return font(F_BODY, size), size


def _layout_blocks(d, blocks, size, max_w):
    items = []
    total = 0
    for i, b in enumerate(blocks):
        f, used = _block_spec(b["style"], size)
        lh = int(used * 1.3)
        indent = px(4) if b["style"] == "question" else 0
        lines = wrap_text(d, b["text"], f, max_w - indent)
        gap_before = int(size * 0.55) if i > 0 else 0
        gap_after = 0
        if b["style"] == "question":
            gap_before = int(size * 0.75)
            gap_after = int(size * 0.55)
        elif b["style"] == "italic":
            gap_before = int(size * 0.85)
        items.append({"font": f, "lines": lines, "lh": lh, "indent": indent,
                      "gap_before": gap_before, "gap_after": gap_after})
        total += gap_before + len(lines) * lh + gap_after
    return items, total


def draw_veil(base, rect, opacity):
    x0, y0, x1, y1 = rect
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    ImageDraw.Draw(overlay).rounded_rectangle(
        [x0, y0, x1, y1], radius=px(4), fill=(0, 0, 0, int(255 * opacity)))
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")


def draw_back(canvas, g, blocks):
    bx0, by0, bx1, by1 = g["back_x0"], g["trim_y0"], g["back_x1"], g["trim_y1"]
    bw = bx1 - bx0
    bh = by1 - by0
    pad = px(7)
    panel_w = int(bw * 0.78)
    text_wmax = panel_w - 2 * pad
    top = by0 + int(bh * 0.09)
    max_text_h = int(bh * 0.60)
    d = ImageDraw.Draw(canvas)
    chosen = None
    for pt in (12, 11.5, 11, 10.5, 10, 9.5, 9):
        size = round(pt / 72 * DPI)
        items, total = _layout_blocks(d, blocks, size, text_wmax)
        if total <= max_text_h:
            chosen = (size, items, total)
            break
    if chosen is None:
        size = round(9 / 72 * DPI)
        items, total = _layout_blocks(d, blocks, size, text_wmax)
        chosen = (size, items, total)
    size, items, total = chosen
    panel_h = total + 2 * pad
    px0 = bx0 + (bw - panel_w) // 2
    prect = (px0, top, px0 + panel_w, top + panel_h)
    canvas = draw_veil(canvas, prect, 0.32)
    d = ImageDraw.Draw(canvas)
    ty = top + pad
    for it in items:
        ty += it["gap_before"]
        for ln in it["lines"]:
            d.text((px0 + pad + it["indent"], ty), ln, font=it["font"], fill=BACK_TEXT)
            ty += it["lh"]
        ty += it["gap_after"]
    return canvas, prect


def draw_spine(canvas, g, title, author):
    sw = g["spine"]
    sh = g["trim_h"]
    if sw < px(10):
        return canvas
    strip = Image.new("RGB", (sh, sw), BACK_BG)
    d = ImageDraw.Draw(strip)
    s = f"{title}   —   {author}"
    cap = int(sw * 0.40)
    f = font(F_TITLE, int(cap * 1.38))
    tw = d.textlength(s, font=f)
    x = (sh - tw) / 2
    y = (sw - cap) / 2 - int(cap * 0.12)
    d.text((x, y), s, font=f, fill=INK_WHITE)
    strip = strip.rotate(-90, expand=True)
    canvas.paste(strip, (g["spine_x0"], g["trim_y0"]))
    return canvas


# --------------------------------------------------------------------------- #
# Assemblage
# --------------------------------------------------------------------------- #
def build_ebook(art, tj, title, author, out):
    W, H = 1600, 2560
    base = add_grain(fit_cover(art, W, H), 0.04)
    base = draw_front(base, (0, 0, W, H), title, tj["tagline"], author)
    path = os.path.join(out, "cover_ebook_final.jpg")
    base.convert("RGB").save(path, "JPEG", quality=92, dpi=(DPI, DPI))
    return path


def build_wrap(art, tj, title, author, pages, out):
    g = wrap_geometry(pages)
    W, H = g["W"], g["H"]
    canvas = Image.new("RGB", (W, H), BACK_BG)
    front_w = W - g["front_x0"]
    front = add_grain(fit_cover(art, front_w, H), 0.04)
    canvas.paste(front, (g["front_x0"], 0))
    back = make_back_ambiance(art, g["spine_x0"], H)
    canvas.paste(back, (0, 0))
    canvas, _ = draw_back(canvas, g, tj["resume_blocks"])
    draw_isbn_zone(canvas, g["back_x1"], g["trim_y1"])
    canvas = draw_spine(canvas, g, title, author)
    face_rect = (g["front_x0"] + px(FACE_SAFETY_MM), g["trim_y0"] + px(FACE_SAFETY_MM),
                 g["front_x1"] - px(FACE_SAFETY_MM), g["trim_y1"] - px(FACE_SAFETY_MM))
    canvas = draw_front(canvas, face_rect, title, tj["tagline"], author)
    pdf = os.path.join(out, "cover_paperback_final.pdf")
    canvas.save(pdf, "PDF", resolution=DPI)
    canvas.save(os.path.join(out, "cover_paperback_final.png"))
    return pdf, g, canvas


def build_montage(wrap_canvas, g, out):
    crop = wrap_canvas.crop((g["bleed"], g["bleed"], g["W"] - g["bleed"], g["H"] - g["bleed"]))
    scale = 1400 / crop.height
    m = crop.resize((round(crop.width * scale), 1400), Image.LANCZOS)
    path = os.path.join(out, "preview_montage.png")
    m.save(path)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", required=True)
    ap.add_argument("--textjson", required=True)
    ap.add_argument("--title", default="404")
    ap.add_argument("--author", default="SHIRO KEGESU")
    ap.add_argument("--pages", type=int, default=400)
    ap.add_argument("--out", default="output/final")
    a = ap.parse_args()

    with open(a.textjson, encoding="utf-8") as f:
        tj = json.load(f)
    os.makedirs(a.out, exist_ok=True)
    art = Image.open(a.art).convert("RGB")

    eb = build_ebook(art, tj, a.title, a.author, a.out)
    pdf, g, canvas = build_wrap(art, tj, a.title, a.author, a.pages, a.out)
    mo = build_montage(canvas, g, a.out)
    print(f"dos={g['spine_mm']:.1f}mm wrap={g['total_w_mm']:.1f}x{g['total_h_mm']:.1f}mm "
          f"({g['W']}x{g['H']}px)")
    for p in (eb, pdf, mo):
        print("  ->", os.path.relpath(p))


if __name__ == "__main__":
    main()
