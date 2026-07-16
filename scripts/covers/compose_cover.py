#!/usr/bin/env python3
"""
Composition des couvertures KDP « CYCLE 404 ».

Prend une image d'art (face) générée par Runware FLUX et produit, pour un concept :
  - cover_ebook.jpg              (1600×2560, RVB, qualité 92)
  - cover_paperback.pdf          (wrap complet : 4e + dos + face, fond perdu, aplati)
  - cover_paperback_sans_texte_4e.pdf  (idem, 4e vierge + repères panneau/marges)
  - preview_montage.png          (4e + dos + face côte à côte)
  - <concept>_panel.json         (géométrie du panneau 4e pour compose_back_text.js)

Aucun texte de résumé n'est écrit sur la 4e (l'auteur le posera via compose_back_text.js).

Usage :
  python compose_cover.py --art face.png --concept chambre404 --title "CYCLE 404" \
      --tagline "Et si votre deuil était un décor ?" --author "SHIRO KEGESU" \
      --pages 400 --out output/covers
"""
from __future__ import annotations

import argparse
import json
import os

from PIL import Image, ImageDraw, ImageFont, ImageFilter

# --------------------------------------------------------------------------- #
# Constantes KDP / impression
# --------------------------------------------------------------------------- #
DPI = 300
MM = DPI / 25.4  # px par mm ≈ 11.811

TRIM_W_MM = 140.0   # 5.5"
TRIM_H_MM = 216.0   # 8.5"
BLEED_MM = 3.2      # 0.125"
PAGE_THICKNESS_MM = 0.0635  # papier crème KDP
SAFETY_MM = 12.0    # marge de sécurité texte 4e (brief)
FACE_SAFETY_MM = 8.0

# Palette
INK_WHITE = (242, 240, 235)     # #F2F0EB blanc cassé
RED = (193, 18, 31)             # #C1121F glow rouge
BACK_BG = (13, 17, 23)          # #0D1117 aplat 4e
BACK_TEXT = (232, 230, 225)     # #E8E6E1

FONT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "assets", "cover_fonts")
F_TITLE = os.path.join(FONT_DIR, "BebasNeue-Regular.ttf")
F_ITAL = os.path.join(FONT_DIR, "Cormorant-Italic.ttf")
F_LABEL = os.path.join(FONT_DIR, "Oswald-SemiBold.ttf")


def px(mm: float) -> int:
    return round(mm * MM)


def font(path: str, size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(path, size)


# --------------------------------------------------------------------------- #
# Géométrie
# --------------------------------------------------------------------------- #
def spine_mm(pages: int) -> float:
    return pages * PAGE_THICKNESS_MM


def wrap_geometry(pages: int) -> dict:
    spine = spine_mm(pages)
    total_w = BLEED_MM + TRIM_W_MM + spine + TRIM_W_MM + BLEED_MM
    total_h = BLEED_MM + TRIM_H_MM + BLEED_MM
    g = {
        "pages": pages, "spine_mm": spine,
        "total_w_mm": total_w, "total_h_mm": total_h,
        "W": px(total_w), "H": px(total_h),
        "bleed": px(BLEED_MM), "spine": px(spine),
        "trim_w": px(TRIM_W_MM), "trim_h": px(TRIM_H_MM),
    }
    # bornes en px (x depuis la gauche)
    g["back_x0"] = g["bleed"]
    g["back_x1"] = g["bleed"] + g["trim_w"]
    g["spine_x0"] = g["back_x1"]
    g["spine_x1"] = g["back_x1"] + g["spine"]
    g["front_x0"] = g["spine_x1"]
    g["front_x1"] = g["spine_x1"] + g["trim_w"]
    g["trim_y0"] = g["bleed"]
    g["trim_y1"] = g["bleed"] + g["trim_h"]
    return g


# --------------------------------------------------------------------------- #
# Utilitaires image
# --------------------------------------------------------------------------- #
def fit_cover(img: Image.Image, w: int, h: int) -> Image.Image:
    """Redimensionne en 'cover' (remplit, rogne le débordement)."""
    iw, ih = img.size
    scale = max(w / iw, h / ih)
    nw, nh = round(iw * scale), round(ih * scale)
    img = img.resize((nw, nh), Image.LANCZOS)
    left = (nw - w) // 2
    top = (nh - h) // 2
    return img.crop((left, top, left + w, top + h))


def add_grain(img: Image.Image, opacity: float = 0.05) -> Image.Image:
    """Grain filmique subtil."""
    noise = Image.effect_noise(img.size, 22).convert("L")
    noise = Image.merge("RGB", (noise, noise, noise))
    return Image.blend(img, noise, opacity)


def darken(img: Image.Image, factor: float) -> Image.Image:
    """Assombrit vers le noir (factor 0..1, 1 = inchangé)."""
    black = Image.new("RGB", img.size, (0, 0, 0))
    return Image.blend(black, img, factor)


def make_back_ambiance(art: Image.Image, w: int, h: int) -> Image.Image:
    """4e : prolonge l'ambiance de la face en secondaire (sombre, flou, aplati vers #0D1117)."""
    base = fit_cover(art, w, h)
    base = base.filter(ImageFilter.GaussianBlur(px(6)))
    base = darken(base, 0.32)
    # fondu vers l'aplat #0D1117 pour homogénéiser
    flat = Image.new("RGB", (w, h), BACK_BG)
    base = Image.blend(base, flat, 0.5)
    base = add_grain(base, 0.045)
    return base


# --------------------------------------------------------------------------- #
# Typographie
# --------------------------------------------------------------------------- #
def text_w(draw, s, fnt, tracking=0):
    w = draw.textlength(s, font=fnt)
    return w + tracking * max(0, len(s) - 1)


def draw_tracked(draw, xy, s, fnt, fill, tracking=0, anchor_center_x=None):
    """Dessine du texte avec inter-lettrage (tracking en px). xy = (x,y) coin haut-gauche
    sauf si anchor_center_x fourni (centre horizontal)."""
    total = text_w(draw, s, fnt, tracking)
    x, y = xy
    if anchor_center_x is not None:
        x = anchor_center_x - total / 2
    for ch in s:
        draw.text((x, y), ch, font=fnt, fill=fill)
        x += draw.textlength(ch, font=fnt) + tracking


def draw_face_typography(base: Image.Image, rect, title, tagline, author):
    """
    Compose titre + accroche + auteur dans le rectangle 'face' (x0,y0,x1,y1) en coords base.
    'CYCLE' + '404' avec glow rouge sur 404. Retourne la hauteur de cap du titre (debug).
    """
    x0, y0, x1, y1 = rect
    fw = x1 - x0
    fh = y1 - y0
    cx = (x0 + x1) / 2
    safe = px(FACE_SAFETY_MM)

    draw = ImageDraw.Draw(base)

    # --- Titre : deux mots CYCLE / 404, cap height ~15% de la hauteur trim
    title_cap = int(fh * 0.150)
    # Bebas : la taille en points ≈ 1.4× la cap height visuelle
    tf = font(F_TITLE, int(title_cap * 1.38))
    words = title.split()
    w1 = words[0] if words else title
    w2 = words[1] if len(words) > 1 else ""

    # positions : titre dans le tiers supérieur
    top = y0 + int(fh * 0.10)
    # ligne 1 (blanc)
    asc, desc = tf.getmetrics()
    line_h = asc + desc
    # glow rouge derrière 404 : couche floue
    glow = Image.new("RGBA", base.size, (0, 0, 0, 0))
    gdraw = ImageDraw.Draw(glow)

    # CYCLE (ligne 1)
    tr1 = int(title_cap * 0.06)
    draw_tracked(draw, (0, top), w1, tf, INK_WHITE, tracking=tr1, anchor_center_x=cx)
    y2 = top + int(line_h * 0.86)
    # 404 (ligne 2) avec glow
    if w2:
        w2_width = text_w(gdraw, w2, tf, tr1)
        gx = cx - w2_width / 2
        # glow : dessiner en rouge, flouter
        xx = gx
        for ch in w2:
            gdraw.text((xx, y2), ch, font=tf, fill=RED + (255,))
            xx += gdraw.textlength(ch, font=tf) + tr1
        glow = glow.filter(ImageFilter.GaussianBlur(px(2.2)))
        base.paste(Image.alpha_composite(base.convert("RGBA"), glow).convert("RGB"), (0, 0))
        draw = ImageDraw.Draw(base)
        # texte 404 net par-dessus, teinte chaude claire
        draw_tracked(draw, (0, y2), w2, tf, (247, 233, 228), tracking=tr1, anchor_center_x=cx)
        title_bottom = y2 + line_h
    else:
        title_bottom = top + line_h

    # --- Accroche : italique fine, blanc 80 %, sous le titre
    if tagline:
        tg = font(F_ITAL, int(fh * 0.042))
        tgy = title_bottom + int(fh * 0.02)
        # léger tracking négatif naturel de l'italique -> 0
        draw_tracked(draw, (0, tgy), tagline, tg, (INK_WHITE + (0,))[:3],
                     tracking=0, anchor_center_x=cx)
        # abaisser un voile ? non. opacité 80 % via couleur grisée
        # (redessine en gris clair pour simuler 80 %)
    # --- Auteur : bas de face, capitales tracking large, ~4.5 % hauteur
    af = font(F_TITLE, int(fh * 0.050 * 1.38))
    ay = y1 - safe - int(fh * 0.050)
    draw_tracked(draw, (0, ay), author, af, INK_WHITE,
                 tracking=int(fh * 0.014), anchor_center_x=cx)
    return base


def draw_tagline_soft(base, rect, tagline, fh_ref):
    """Redessine l'accroche en blanc 80 % (appelée après pour l'opacité)."""
    return base  # gérée inline


# --------------------------------------------------------------------------- #
# 4e : panneau de lisibilité + zone ISBN
# --------------------------------------------------------------------------- #
def panel_rect(bx0, by0, bx1, by1):
    """Panneau ≈ 70 % largeur × 60 % hauteur, centré horizontalement, 2/3 supérieurs."""
    bw = bx1 - bx0
    bh = by1 - by0
    pw = int(bw * 0.70)
    ph = int(bh * 0.60)
    pxl = bx0 + (bw - pw) // 2
    # positionné dans les 2/3 supérieurs : haut à ~12 % de la 4e
    pyt = by0 + int(bh * 0.12)
    return (pxl, pyt, pxl + pw, pyt + ph)


def draw_back_panel(base, prect, opacity=0.30):
    """Voile sombre coins adoucis pour recevoir le futur texte."""
    x0, y0, x1, y1 = prect
    overlay = Image.new("RGBA", base.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    rad = px(4)
    od.rounded_rectangle([x0, y0, x1, y1], radius=rad,
                         fill=(0, 0, 0, int(255 * opacity)))
    base_rgba = base.convert("RGBA")
    base_rgba = Image.alpha_composite(base_rgba, overlay)
    return base_rgba.convert("RGB")


def wrap_text(draw, text, fnt, max_w):
    """Découpe le texte en lignes tenant dans max_w (respecte les \\n)."""
    lines = []
    for para in text.split("\n"):
        if not para.strip():
            lines.append("")
            continue
        words = para.split()
        cur = ""
        for w in words:
            test = (cur + " " + w).strip()
            if draw.textlength(test, font=fnt) <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    return lines


def draw_back_text(base, prect, text):
    """Compose le résumé (fourni ultérieurement) dans le panneau de la 4e."""
    x0, y0, x1, y1 = prect
    pad = px(6)
    max_w = (x1 - x0) - 2 * pad
    d = ImageDraw.Draw(base)
    # dimensionne le corps pour tenir dans le panneau (min 9pt ≈ px(9pt))
    min_px = round(9 / 72 * DPI)  # 9 pt
    size = round(13 / 72 * DPI)   # départ 13 pt
    body = font(F_LABEL, size)
    while size > min_px:
        body = font(F_LABEL, size)
        lines = wrap_text(d, text, body, max_w)
        lh = int(size * 1.3)
        if len(lines) * lh <= (y1 - y0) - 2 * pad:
            break
        size -= 2
    lines = wrap_text(d, text, body, max_w)
    lh = int(size * 1.3)
    ty = y0 + pad
    for ln in lines:
        d.text((x0 + pad, ty), ln, font=body, fill=BACK_TEXT)
        ty += lh
    return base


def draw_isbn_zone(base, bx1, by1):
    """Rectangle blanc 50×30 mm en bas à droite de la 4e, ≥6 mm des bords de coupe."""
    d = ImageDraw.Draw(base)
    margin = px(6)
    w, h = px(50), px(30)
    x1 = bx1 - margin
    y1 = by1 - margin
    x0 = x1 - w
    y0 = y1 - h
    d.rectangle([x0, y0, x1, y1], fill=(255, 255, 255))
    return (x0, y0, x1, y1)


def dashed_rect(draw, rect, color, dash=24, gap=16, width=3):
    x0, y0, x1, y1 = rect
    def hline(y):
        x = x0
        while x < x1:
            draw.line([x, y, min(x + dash, x1), y], fill=color, width=width)
            x += dash + gap
    def vline(x):
        y = y0
        while y < y1:
            draw.line([x, y, x, min(y + dash, y1)], fill=color, width=width)
            y += dash + gap
    hline(y0); hline(y1); vline(x0); vline(x1)


def draw_spine(base, g, title, author):
    """Dos vertical : titre + auteur, même famille typo."""
    sw = g["spine"]
    sh = g["trim_h"]
    if sw < px(9):  # dos trop fin pour du texte (<9mm) -> on laisse nu
        return base
    strip = Image.new("RGB", (sh, sw), (0, 0, 0))  # horizontale, on tournera
    # fond sombre
    strip.paste(Image.new("RGB", (sh, sw), BACK_BG), (0, 0))
    d = ImageDraw.Draw(strip)
    cap = int(sw * 0.42)
    tf = font(F_TITLE, int(cap * 1.38))
    # titre à gauche, auteur à droite
    tt = title
    tw = d.textlength(tt, font=tf)
    d.text((int(sh * 0.06), (sw - cap) / 2 - int(cap * 0.15)), tt, font=tf, fill=INK_WHITE)
    af = font(F_TITLE, int(sw * 0.30 * 1.38))
    at = author
    aw = d.textlength(at, font=af)
    d.text((sh - int(sh * 0.06) - aw, (sw - sw * 0.30) / 2 - int(sw * 0.30 * 0.15)),
           at, font=af, fill=INK_WHITE)
    strip = strip.rotate(90, expand=True)  # vertical, lecture bas->haut
    base.paste(strip, (g["spine_x0"], g["trim_y0"]))
    return base


# --------------------------------------------------------------------------- #
# Assemblage
# --------------------------------------------------------------------------- #
def build_ebook(art, concept, title, tagline, author, out):
    W, H = 1600, 2560
    base = fit_cover(art, W, H)
    base = add_grain(base, 0.04)
    rect = (px(FACE_SAFETY_MM) // 3, 0, W - px(FACE_SAFETY_MM) // 3, H)
    # marges internes propres
    m = int(W * 0.055)
    rect = (m, int(H * 0.02), W - m, H - int(H * 0.02))
    base = draw_face_typography(base, rect, title, tagline, author)
    path = os.path.join(out, "cover_ebook.jpg")
    base.convert("RGB").save(path, "JPEG", quality=92, dpi=(DPI, DPI))
    return path


def build_wrap(art, concept, title, tagline, author, pages, out, work=False, resume=None):
    g = wrap_geometry(pages)
    W, H = g["W"], g["H"]
    canvas = Image.new("RGB", (W, H), BACK_BG)

    # --- FACE (droite) : art plein cadre + fond perdu
    front_w = W - g["front_x0"]
    front = fit_cover(art, front_w, H)
    front = add_grain(front, 0.04)
    canvas.paste(front, (g["front_x0"], 0))

    # --- 4e (gauche) : ambiance secondaire
    back_w = g["spine_x0"]
    back = make_back_ambiance(art, back_w, H)
    canvas.paste(back, (0, 0))

    # --- panneau 4e + ISBN
    prect = panel_rect(g["back_x0"], g["trim_y0"], g["back_x1"], g["trim_y1"])
    canvas = draw_back_panel(canvas, prect, opacity=0.30)
    if resume and not work:
        canvas = draw_back_text(canvas, prect, resume)
    isbn = draw_isbn_zone(canvas, g["back_x1"], g["trim_y1"])

    # --- dos
    canvas = draw_spine(canvas, g, title, author)

    # --- typo face (dans le trim face, pas dans le fond perdu)
    face_rect = (g["front_x0"] + px(FACE_SAFETY_MM), g["trim_y0"] + px(FACE_SAFETY_MM),
                 g["front_x1"] - px(FACE_SAFETY_MM), g["trim_y1"] - px(FACE_SAFETY_MM))
    canvas = draw_face_typography(canvas, face_rect, title, tagline, author)

    # --- repères (version travail uniquement)
    if work:
        d = ImageDraw.Draw(canvas)
        dashed_rect(d, prect, (255, 255, 255), dash=28, gap=18, width=3)
        # marges de sécurité 12 mm sur la 4e
        s = px(SAFETY_MM)
        safe_rect = (g["back_x0"] + s, g["trim_y0"] + s, g["back_x1"] - s, g["trim_y1"] - s)
        dashed_rect(d, safe_rect, (193, 18, 31), dash=18, gap=14, width=2)
        # lignes de coupe (trim) sur tout le wrap
        for x in (g["back_x1"], g["spine_x1"]):
            d.line([x, 0, x, H], fill=(120, 200, 255), width=2)
        d.rectangle([g["bleed"], g["bleed"], W - g["bleed"], H - g["bleed"]],
                    outline=(120, 200, 255), width=2)

    name = "cover_paperback_sans_texte_4e.pdf" if work else "cover_paperback.pdf"
    path = os.path.join(out, name)
    canvas.save(path, "PDF", resolution=DPI)
    if not work:
        # raster du wrap (sans résumé) pour l'itération JS (compose_back_text.js)
        canvas.save(os.path.join(out, "cover_paperback_base.png"))
    # sidecar géométrie panneau + params (pour compose_back_text.js)
    if not work:
        meta = {
            "concept": concept, "pages": pages,
            "wrap_px": [W, H], "dpi": DPI,
            "panel_px": list(prect),
            "panel_mm": [round(v / MM, 2) for v in prect],
            "isbn_px": list(isbn),
            "back_bg": BACK_BG, "text_color": BACK_TEXT,
            "safety_mm": SAFETY_MM,
            # params pour régénérer le PDF final avec le résumé, sans Runware :
            "params": {"title": title, "tagline": tagline, "author": author},
        }
        with open(os.path.join(out, f"{concept}_panel.json"), "w") as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
    return path, g


def build_montage(art, concept, title, tagline, author, pages, out):
    """Aperçu face + dos côte à côte (basse déf pour validation)."""
    g = wrap_geometry(pages)
    # reconstruit une face typographiée + une 4e pour l'aperçu
    face = fit_cover(art, g["trim_w"], g["trim_h"])
    face = add_grain(face, 0.04)
    frect = (px(FACE_SAFETY_MM), px(FACE_SAFETY_MM),
             g["trim_w"] - px(FACE_SAFETY_MM), g["trim_h"] - px(FACE_SAFETY_MM))
    face = draw_face_typography(face, frect, title, tagline, author)

    back = make_back_ambiance(art, g["trim_w"], g["trim_h"])
    prect = panel_rect(0, 0, g["trim_w"], g["trim_h"])
    back = draw_back_panel(back, prect, 0.30)
    draw_isbn_zone(back, g["trim_w"], g["trim_h"])

    gap = px(8)
    m = Image.new("RGB", (g["trim_w"] * 2 + gap, g["trim_h"]), (30, 30, 34))
    m.paste(back, (0, 0))
    m.paste(face, (g["trim_w"] + gap, 0))
    # réduit pour un aperçu léger
    scale = 1400 / m.height
    m = m.resize((round(m.width * scale), round(m.height * scale)), Image.LANCZOS)
    path = os.path.join(out, "preview_montage.png")
    m.save(path)
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--art", required=True)
    ap.add_argument("--concept", required=True)
    ap.add_argument("--title", default="CYCLE 404")
    ap.add_argument("--tagline", default="Et si votre deuil était un décor ?")
    ap.add_argument("--author", default="SHIRO KEGESU")
    ap.add_argument("--pages", type=int, default=400)
    ap.add_argument("--out", default="output/covers")
    ap.add_argument("--resume", help="Fichier texte du résumé 4e (optionnel, ajouté au PDF final)")
    a = ap.parse_args()

    resume_text = None
    if a.resume and os.path.exists(a.resume):
        with open(a.resume, encoding="utf-8") as f:
            resume_text = f.read().strip()

    outdir = os.path.join(a.out, a.concept)
    os.makedirs(outdir, exist_ok=True)
    art = Image.open(a.art).convert("RGB")

    eb = build_ebook(art, a.concept, a.title, a.tagline, a.author, outdir)
    wf, g = build_wrap(art, a.concept, a.title, a.tagline, a.author, a.pages, outdir,
                       work=False, resume=resume_text)
    wk, _ = build_wrap(art, a.concept, a.title, a.tagline, a.author, a.pages, outdir, work=True)
    mo = build_montage(art, a.concept, a.title, a.tagline, a.author, a.pages, outdir)

    print(f"[{a.concept}] dos={g['spine_mm']:.1f}mm wrap={g['total_w_mm']:.1f}×{g['total_h_mm']:.1f}mm "
          f"({g['W']}×{g['H']}px)")
    for p in (eb, wf, wk, mo):
        print("  →", os.path.relpath(p))


if __name__ == "__main__":
    main()
