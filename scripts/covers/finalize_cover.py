#!/usr/bin/env python3
"""
Finalisation KDP « CYCLE 404 » : compositing typographique définitif sur l'art
validé (aucune regénération d'image).

Produit dans --out :
  - cover_ebook_final.jpg      (1600x2560, accroche + titre + auteur, SANS ISBN)
  - cover_paperback_final.pdf  (wrap complet 4e + dos + face, fond perdu, aplati)
  - cover_paperback_final.png  (raster du wrap, pour l'aperçu)
  - preview_montage.png        (4e + dos + face côte à côte)

Textes (accroche + résumé) lus depuis --textjson, à la lettre.

Usage :
  python finalize_cover.py --art face.png --textjson text/cycle404_text.json \
     --title "CYCLE 404" --author "SHIRO KEGESU" --pages 400 --out output/final
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

# Polices supplémentaires (graisses légères pour accroche et corps 4e).
F_BODY = os.path.join(FONT_DIR, "Oswald-Regular.ttf")
F_BOLD = os.path.join(FONT_DIR, "Oswald-SemiBold.ttf")
_light = os.path.join(FONT_DIR, "Oswald-Light.ttf")
F_TAG = _light if os.path.exists(_light) else F_BODY


def draw_tracked_center(d, cx, y, s, f, fill, tracking):
    total = text_w(d, s, f, tracking)
    x = cx - total / 2
    for ch in s:
        d.text((x, y), ch, font=f, fill=fill)
        x += d.textlength(ch, font=f) + tracking


def gradient_scrim_top(base, rect, height_frac=0.24, max_alpha=72):
    """Voile sombre dégradé en haut du rect (lisibilité de l'accroche)."""
    x0, y0, x1, y1 = rect
    h = max(1, int((y1 - y0) * height_frac))
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for i in range(h):
        a = int(max_alpha * (1 - i / h))
        od.line([(x0, y0 + i), (x1, y0 + i)], fill=(0, 0, 0, a))
    return Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")


def draw_tagline(base, rect, lines):
    """Accroche : 3 lignes empilées, tout en haut, petites capitales, tracking large,
    blanc cassé 85 %, aucun glow."""
    x0, y0, x1, y1 = rect
    fh = y1 - y0
    cx = (x0 + x1) / 2
    cap = int(fh * 0.040)
    f = font(F_TAG, int(cap * 1.35))
    tracking = int(cap * 0.38)
    asc, desc = f.getmetrics()
    lh = int((asc + desc) * 1.10)
    top = y0 + int(fh * 0.075)
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    col = INK_WHITE + (217,)  # 85 %
    y = top
    for ln in lines:
        s = ln.upper()
        total = text_w(od, s, f, tracking)
        x = cx - total / 2
        for ch in s:
            od.text((x, y), ch, font=f, fill=col)
            x += od.textlength(ch, font=f) + tracking
        y += lh
    out = Image.alpha_composite(base.convert("RGBA"), overlay).convert("RGB")
    return out


def draw_title_block(base, rect, title):
    x0, y0, x1, y1 = rect
    fh = y1 - y0
    cx = (x0 + x1) / 2
    cap = int(fh * 0.150)
    tf = font(F_TITLE, int(cap * 1.38))
    words = title.split()
    w1 = words[0] if words else title
    w2 = words[1] if len(words) > 1 else ""
    asc, desc = tf.getmetrics()
    line_h = asc + desc
    top = y0 + int(fh * 0.170)
    tr = int(cap * 0.06)
    d = ImageDraw.Draw(base)
    draw_tracked_center(d, cx, top, w1, tf, INK_WHITE, tr)
    y2 = top + int(line_h * 0.86)
    if w2:
        glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow)
        total = text_w(gd, w2, tf, tr)
        xx = cx - total / 2
        for ch in w2:
            gd.text((xx, y2), ch, font=tf, fill=RED + (255,))
            xx += gd.textlength(ch, font=tf) + tr
        glow = glow.filter(ImageFilter.GaussianBlur(px(2.4)))
        base = Image.alpha_composite(base.convert("RGBA"), glow).convert("RGB")
        d = ImageDraw.Draw(base)
        draw_tracked_center(d, cx, y2, w2, tf, (247, 233, 228), tr)
    return base


def draw_author(base, rect, author):
    x0, y0, x1, y1 = rect
    fh = y1 - y0
    cx = (x0 + x1) / 2
    f = font(F_TITLE, int(fh * 0.050 * 1.38))
    y = y1 - px(FACE_SAFETY_MM) - int(fh * 0.050)
    d = ImageDraw.Draw(base)
    draw_tracked_center(d, cx, y, author, f, INK_WHITE, int(fh * 0.014))
    return base


def draw_front(base, rect, title, tagline_lines, author):
    base = gradient_scrim_top(base, rect, 0.24, 72)
    base = draw_tagline(base, rect, tagline_lines)
    base = draw_title_block(base, rect, title)
    base = draw_author(base, rect, author)
    return base


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
    if sw < px(10):  # dos < 10 mm : aucun texte (règle KDP fine tranche)
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
    strip = strip.rotate(-90, expand=True)  # lecture haut -> bas
    canvas.paste(strip, (g["spine_x0"], g["trim_y0"]))
    return canvas


def build_ebook(art, tj, title, author, out):
    W, H = 1600, 2560
    base = fit_cover(art, W, H)
    base = add_grain(base, 0.04)
    m = int(W * 0.055)
    rect = (m, int(H * 0.02), W - m, H - int(H * 0.02))
    base = draw_front(base, rect, title, tj["tagline"], author)
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
    ap.add_argument("--title", default="CYCLE 404")
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
