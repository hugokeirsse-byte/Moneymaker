#!/usr/bin/env python3
"""
exp_formats.py — un prototype par format officiel détourné, pour choisir.

Génère une image-mockup par idée (alerte enlèvement, panneau STOP, étiquette
nutritionnelle, étiquette de lavage, date de péremption, ordonnance, avis de
recherche, ruban CAUTION, erreur 404, barre de chargement, panneau danger,
carton rouge, sortie de secours). Mockups uniquement, pour validation.

Usage :
    python scripts/exp_formats.py --out /tmp/formats
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

ARIAL = "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"
ARIALR = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"


def af(sz, reg=False):
    return ImageFont.truetype(ARIALR if reg else ARIAL, int(sz))


def ctext(d, cx, y, text, font, fill, anchor="ma"):
    d.text((cx, y), text, font=font, fill=fill, anchor=anchor)


def newimg(side, bg=(0, 0, 0, 0)):
    im = Image.new("RGBA", (side, side), bg)
    return im, ImageDraw.Draw(im)


# ── 1. ALERTE ENLÈVEMENT ──────────────────────────────────────────────────
def f_alerte(side=1200):
    im, d = newimg(side)
    W = int(side * 0.86); H = int(side * 0.52)
    x0 = (side - W) // 2; y0 = (side - H) // 2
    d.rounded_rectangle([x0, y0, x0 + W, y0 + H], radius=18, fill=(247, 148, 29, 255))
    bar = int(H * 0.26)
    d.rounded_rectangle([x0, y0, x0 + W, y0 + bar], radius=18, fill=(20, 20, 22, 255))
    d.rectangle([x0, y0 + bar // 2, x0 + W, y0 + bar], fill=(20, 20, 22, 255))
    ctext(d, side // 2, y0 + bar * 0.16, "⚠ ALERTE ENLÈVEMENT", af(side * 0.045),
          (247, 148, 29, 255))
    ctext(d, side // 2, y0 + bar + int(H * 0.12), "DÉMOCRATIE", af(side * 0.085),
          (20, 20, 22, 255))
    ctext(d, side // 2, y0 + bar + int(H * 0.34), "PORTÉE DISPARUE", af(side * 0.085),
          (20, 20, 22, 255))
    ctext(d, side // 2, y0 + bar + int(H * 0.60),
          "Vue en bonne santé pour la dernière fois en 2017",
          af(side * 0.030, reg=True), (20, 20, 22, 255))
    return im


# ── 2. PANNEAU STOP ───────────────────────────────────────────────────────
def f_stop(side=1200):
    im, d = newimg(side)
    cx = cy = side // 2
    R = int(side * 0.34)
    pts = [(cx + R * math.cos(math.pi / 8 + k * math.pi / 4),
            cy + R * math.sin(math.pi / 8 + k * math.pi / 4)) for k in range(8)]
    d.polygon(pts, fill=(200, 16, 24, 255))
    pts2 = [(cx + R * 0.86 * math.cos(math.pi / 8 + k * math.pi / 4),
             cy + R * 0.86 * math.sin(math.pi / 8 + k * math.pi / 4)) for k in range(8)]
    d.line(pts2 + [pts2[0]], fill=(255, 255, 255, 255), width=int(side * 0.012))
    ctext(d, cx, cy - int(side * 0.085), "STOP", af(side * 0.115), (255, 255, 255, 255))
    ctext(d, cx, cy + int(side * 0.02), "AU PATRIARCAT", af(side * 0.05),
          (255, 255, 255, 255))
    return im


# ── 3. ÉTIQUETTE NUTRITIONNELLE ───────────────────────────────────────────
def f_ingredients(side=1200):
    im, d = newimg(side)
    W = int(side * 0.6); H = int(side * 0.72)
    x0 = (side - W) // 2; y0 = (side - H) // 2
    d.rectangle([x0, y0, x0 + W, y0 + H], fill=(255, 255, 255, 255),
                outline=(0, 0, 0, 255), width=int(side * 0.006))
    ctext(d, side // 2, y0 + int(H * 0.03), "VALEURS", af(side * 0.07), (0, 0, 0, 255))
    ctext(d, side // 2, y0 + int(H * 0.12), "PERSONNELLES", af(side * 0.045),
          (0, 0, 0, 255))
    d.line([x0 + 20, y0 + int(H * 0.22), x0 + W - 20, y0 + int(H * 0.22)],
           fill=(0, 0, 0, 255), width=int(side * 0.012))
    rows = [("Rage", "100%"), ("Patience", "0%"), ("Sarcasme", "95%"),
            ("Caféine", "∞"), ("Empathie", "88%"), ("Filtre", "0%")]
    fy = af(side * 0.040); fr = af(side * 0.040, reg=True)
    yy = y0 + int(H * 0.27)
    for name, val in rows:
        d.text((x0 + 28, yy), name, font=fr, fill=(0, 0, 0, 255))
        d.text((x0 + W - 28, yy), val, font=fy, fill=(0, 0, 0, 255), anchor="ra")
        d.line([x0 + 20, yy + int(H * 0.085), x0 + W - 20, yy + int(H * 0.085)],
               fill=(0, 0, 0, 255), width=2)
        yy += int(H * 0.11)
    return im


# ── 4. ÉTIQUETTE DE LAVAGE ────────────────────────────────────────────────
def f_care(side=1200):
    im, d = newimg(side)
    W = int(side * 0.78); H = int(side * 0.4)
    x0 = (side - W) // 2; y0 = (side - H) // 2
    d.rectangle([x0, y0, x0 + W, y0 + H], outline=(0, 0, 0, 255),
                width=int(side * 0.006))
    n = 4; cw = W / n; sy = y0 + int(H * 0.22); s = int(side * 0.07)
    cxs = [x0 + cw * (i + 0.5) for i in range(n)]
    lw = max(3, int(side * 0.006))
    # bac à laver
    d.polygon([(cxs[0]-s, sy-s*0.4), (cxs[0]+s, sy-s*0.4), (cxs[0]+s*0.7, sy+s),
               (cxs[0]-s*0.7, sy+s)], outline=(0, 0, 0, 255), width=lw)
    d.arc([cxs[0]-s*0.6, sy-s*0.1, cxs[0]+s*0.6, sy+s*0.5], 0, 180,
          fill=(0, 0, 0, 255), width=lw)
    # triangle (blanchiment)
    d.polygon([(cxs[1], sy-s), (cxs[1]-s, sy+s), (cxs[1]+s, sy+s)],
              outline=(0, 0, 0, 255), width=lw)
    # carré (séchage)
    d.rectangle([cxs[2]-s, sy-s, cxs[2]+s, sy+s], outline=(0, 0, 0, 255), width=lw)
    d.ellipse([cxs[2]-s*0.3, sy-s*0.3, cxs[2]+s*0.3, sy+s*0.3], outline=(0, 0, 0, 255),
              width=lw)
    # fer à repasser
    d.polygon([(cxs[3]-s, sy+s*0.5), (cxs[3]+s, sy+s*0.5), (cxs[3]+s*0.6, sy-s*0.3),
               (cxs[3]-s*0.3, sy-s*0.3)], outline=(0, 0, 0, 255), width=lw)
    ctext(d, side // 2, y0 + int(H * 0.66), "NE PAS LAVER MON CERVEAU",
          af(side * 0.040), (0, 0, 0, 255))
    ctext(d, side // 2, y0 + int(H * 0.80), "Lavage à froid, comme mon ex",
          af(side * 0.030, reg=True), (0, 0, 0, 255))
    return im


# ── 5. DATE DE PÉREMPTION ─────────────────────────────────────────────────
def f_bestbefore(side=1200):
    im, d = newimg(side)
    layer, dl = newimg(side)
    W = int(side * 0.7); H = int(side * 0.3)
    x0 = (side - W) // 2; y0 = (side - H) // 2
    dl.rounded_rectangle([x0, y0, x0 + W, y0 + H], radius=14, outline=(30, 30, 34, 255),
                         width=int(side * 0.009))
    ctext(dl, side // 2, y0 + int(H * 0.14), "À CONSOMMER AVANT", af(side * 0.05),
          (30, 30, 34, 255))
    ctext(dl, side // 2, y0 + int(H * 0.46), "LA RÉVOLUTION", af(side * 0.075),
          (30, 30, 34, 255))
    layer = layer.rotate(-7, resample=Image.BICUBIC, center=(side // 2, side // 2))
    im.alpha_composite(layer)
    return im


# ── 6. ORDONNANCE ─────────────────────────────────────────────────────────
def f_prescription(side=1200):
    im, d = newimg(side)
    W = int(side * 0.68); H = int(side * 0.74)
    x0 = (side - W) // 2; y0 = (side - H) // 2
    d.rectangle([x0, y0, x0 + W, y0 + H], fill=(255, 255, 255, 255),
                outline=(30, 30, 34, 255), width=int(side * 0.005))
    ctext(d, side // 2, y0 + int(H * 0.04), "ORDONNANCE", af(side * 0.055),
          (30, 30, 34, 255))
    d.text((x0 + 26, y0 + int(H * 0.18)), "℞", font=af(side * 0.1), fill=(30, 30, 34, 255))
    fh = load_font("hand", int(side * 0.052))
    items = ["2 siestes par jour", "Café à volonté", "Toucher de l'herbe",
             "0 réunion inutile", "Limiter les cons"]
    yy = y0 + int(H * 0.30)
    for it in items:
        d.text((x0 + int(W * 0.24), yy), "• " + it, font=fh, fill=(20, 30, 90, 255))
        yy += int(H * 0.12)
    d.line([x0 + int(W * 0.45), y0 + int(H * 0.9), x0 + W - 26, y0 + int(H * 0.9)],
           fill=(30, 30, 34, 255), width=2)
    d.text((x0 + int(W * 0.5), y0 + int(H * 0.91)), "Dr. Bon Sens",
           font=load_font("hand", int(side * 0.04)), fill=(30, 30, 34, 255))
    return im


# ── 7. AVIS DE RECHERCHE (WANTED) ─────────────────────────────────────────
def f_wanted(side=1200):
    im, d = newimg(side, bg=(244, 235, 214, 255))
    W = int(side * 0.84); H = int(side * 0.86)
    x0 = (side - W) // 2; y0 = (side - H) // 2
    for k, col in ((int(side * 0.012), (40, 28, 16, 255)),):
        d.rectangle([x0, y0, x0 + W, y0 + H], outline=col, width=k)
    ctext(d, side // 2, y0 + int(H * 0.04), "WANTED", load_font("fatserif", side * 0.13),
          (40, 28, 16, 255))
    ctext(d, side // 2, y0 + int(H * 0.22), "DEAD OR ALIVE", af(side * 0.04),
          (40, 28, 16, 255))
    d.rectangle([x0 + int(W * 0.22), y0 + int(H * 0.30), x0 + int(W * 0.78),
                 y0 + int(H * 0.62)], outline=(40, 28, 16, 255), width=int(side * 0.006))
    ctext(d, side // 2, y0 + int(H * 0.42), "?", load_font("fatserif", side * 0.16),
          (40, 28, 16, 255))
    ctext(d, side // 2, y0 + int(H * 0.66), "LE PATRIARCAT", af(side * 0.07),
          (40, 28, 16, 255))
    ctext(d, side // 2, y0 + int(H * 0.80), "RÉCOMPENSE : L'ÉGALITÉ",
          af(side * 0.035), (40, 28, 16, 255))
    return im


# ── 8. RUBAN CAUTION ──────────────────────────────────────────────────────
def f_caution(side=1200):
    im, d = newimg(side)
    H = int(side * 0.42); y0 = (side - H) // 2
    yellow = (250, 204, 21, 255); black = (20, 20, 22, 255)
    d.rectangle([0, y0, side, y0 + H], fill=yellow)
    sw = int(side * 0.07)
    for band in (y0, y0 + H - int(H * 0.16)):
        for x in range(-side, side, sw * 2):
            d.polygon([(x, band), (x + sw, band), (x + sw - 40, band + int(H * 0.16)),
                       (x - 40, band + int(H * 0.16))], fill=black)
    ctext(d, side // 2, y0 + int(H * 0.30), "CAUTION", af(side * 0.085), black)
    ctext(d, side // 2, y0 + int(H * 0.52), "ZONE FÉMINISTE", af(side * 0.05), black)
    return im


# ── 9. ERREUR 404 ─────────────────────────────────────────────────────────
def f_error(side=1200):
    im, d = newimg(side)
    W = int(side * 0.82); H = int(side * 0.56)
    x0 = (side - W) // 2; y0 = (side - H) // 2
    d.rounded_rectangle([x0, y0, x0 + W, y0 + H], radius=16, fill=(24, 26, 32, 255))
    bar = int(H * 0.13)
    d.rounded_rectangle([x0, y0, x0 + W, y0 + bar * 2], radius=16, fill=(40, 44, 52, 255))
    d.rectangle([x0, y0 + bar, x0 + W, y0 + bar * 2], fill=(40, 44, 52, 255))
    for i, c in enumerate(((255, 95, 86), (255, 189, 46), (39, 201, 63))):
        d.ellipse([x0 + 24 + i * 40, y0 + bar * 0.5, x0 + 50 + i * 40, y0 + bar * 0.5 + 26],
                  fill=c + (255,))
    ctext(d, side // 2, y0 + int(H * 0.26), "404", load_font("code", side * 0.16),
          (236, 238, 244, 255))
    ctext(d, side // 2, y0 + int(H * 0.62), "JUSTICE_NOT_FOUND",
          load_font("mono", side * 0.045), (120, 220, 150, 255))
    return im


# ── 10. BARRE DE CHARGEMENT ───────────────────────────────────────────────
def f_loading(side=1200):
    im, d = newimg(side)
    ctext(d, side // 2, int(side * 0.34), "RÉVOLUTION EN COURS…",
          load_font("geo", side * 0.055), (30, 30, 34, 255))
    W = int(side * 0.66); H = int(side * 0.075)
    x0 = (side - W) // 2; y0 = int(side * 0.48)
    d.rounded_rectangle([x0, y0, x0 + W, y0 + H], radius=H // 2,
                        outline=(30, 30, 34, 255), width=int(side * 0.006))
    fillw = int(W * 0.47)
    d.rounded_rectangle([x0 + 6, y0 + 6, x0 + fillw, y0 + H - 6], radius=H // 2,
                        fill=(201, 162, 39, 255))
    ctext(d, side // 2, y0 + H + int(side * 0.03), "47 % — n'abandonnez pas",
          load_font("geo", side * 0.035), (90, 90, 96, 255))
    return im


# ── 11. PANNEAU DANGER ────────────────────────────────────────────────────
def f_hazard(side=1200):
    im, d = newimg(side)
    cx = side // 2; cy = int(side * 0.42); R = int(side * 0.3)
    tri = [(cx, cy - R), (cx - R * 0.92, cy + R * 0.75), (cx + R * 0.92, cy + R * 0.75)]
    d.polygon(tri, fill=(250, 204, 21, 255))
    d.line(tri + [tri[0]], fill=(20, 20, 22, 255), width=int(side * 0.018))
    d.rounded_rectangle([cx - int(side * 0.022), cy - int(R * 0.35),
                         cx + int(side * 0.022), cy + int(R * 0.32)], radius=10,
                        fill=(20, 20, 22, 255))
    d.ellipse([cx - int(side * 0.022), cy + int(R * 0.42),
               cx + int(side * 0.022), cy + int(R * 0.42) + int(side * 0.044)],
              fill=(20, 20, 22, 255))
    ctext(d, cx, int(side * 0.74), "TOXIC : MASCULINITÉ", af(side * 0.055),
          (20, 20, 22, 255))
    return im


# ── 12. CARTON ROUGE ──────────────────────────────────────────────────────
def f_carton(side=1200):
    im, d = newimg(side)
    layer, dl = newimg(side)
    W = int(side * 0.44); H = int(side * 0.62)
    x0 = (side - W) // 2; y0 = (side - H) // 2
    dl.rounded_rectangle([x0, y0, x0 + W, y0 + H], radius=22, fill=(206, 26, 32, 255))
    ctext(dl, side // 2, y0 + int(H * 0.30), "CARTON", af(side * 0.06),
          (255, 255, 255, 255))
    ctext(dl, side // 2, y0 + int(H * 0.44), "ROUGE", af(side * 0.06),
          (255, 255, 255, 255))
    ctext(dl, side // 2, y0 + int(H * 0.62), "AU RACISME", af(side * 0.045),
          (255, 255, 255, 255))
    layer = layer.rotate(8, resample=Image.BICUBIC, center=(side // 2, side // 2))
    im.alpha_composite(layer)
    return im


# ── 13. SORTIE DE SECOURS ─────────────────────────────────────────────────
def f_sortie(side=1200):
    im, d = newimg(side)
    W = int(side * 0.8); H = int(side * 0.34)
    x0 = (side - W) // 2; y0 = (side - H) // 2
    green = (22, 145, 80, 255); white = (255, 255, 255, 255)
    d.rounded_rectangle([x0, y0, x0 + W, y0 + H], radius=14, fill=green)
    # bonhomme qui court
    mx = x0 + int(W * 0.16); my = y0 + H // 2
    s = int(H * 0.30)
    d.ellipse([mx - s * 0.3, my - s * 1.3, mx + s * 0.3, my - s * 0.7], fill=white)
    d.line([(mx, my - s * 0.7), (mx + s * 0.5, my + s * 0.1)], fill=white, width=int(side*0.012))
    d.line([(mx + s * 0.2, my - s * 0.3), (mx + s * 0.8, my - s * 0.45)], fill=white, width=int(side*0.012))
    d.line([(mx + s * 0.2, my - s * 0.3), (mx - s * 0.4, my - s * 0.5)], fill=white, width=int(side*0.012))
    d.line([(mx + s * 0.5, my + s * 0.1), (mx + s, my + s * 0.7)], fill=white, width=int(side*0.012))
    d.line([(mx + s * 0.5, my + s * 0.1), (mx - s * 0.1, my + s * 0.7)], fill=white, width=int(side*0.012))
    # porte + flèche
    dx = x0 + int(W * 0.34)
    d.rectangle([dx, my - s * 1.3, dx + s * 1.1, my + s * 0.8], outline=white, width=int(side*0.01))
    ax = x0 + int(W * 0.60)
    d.line([(ax, my), (ax + int(W * 0.12), my)], fill=white, width=int(side * 0.016))
    d.polygon([(ax + int(W * 0.12) + 4, my - 18), (ax + int(W * 0.12) + 4, my + 18),
               (ax + int(W * 0.18), my)], fill=white)
    ctext(d, side // 2, y0 + H + int(side * 0.02), "SORTIE DE SECOURS DU CAPITALISME",
          af(side * 0.038), (30, 30, 34, 255))
    return im


FORMATS = [
    ("alerte_enlevement", f_alerte), ("panneau_stop", f_stop),
    ("etiquette_nutrition", f_ingredients), ("etiquette_lavage", f_care),
    ("date_peremption", f_bestbefore), ("ordonnance", f_prescription),
    ("avis_recherche", f_wanted), ("ruban_caution", f_caution),
    ("erreur_404", f_error), ("barre_chargement", f_loading),
    ("panneau_danger", f_hazard), ("carton_rouge", f_carton),
    ("sortie_secours", f_sortie),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="/tmp/formats")
    ap.add_argument("--sheet", default="")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)
    ims = []
    for name, fn in FORMATS:
        im = fn(1200)
        bg = Image.new("RGB", im.size, (250, 250, 252))
        bg.paste(im.convert("RGB"), mask=im.split()[-1])
        p = os.path.join(args.out, f"{name}.png")
        bg.save(p, quality=92)
        ims.append((name, bg))
        print(p)
    if args.sheet:
        cols = 4
        cell = 470
        rows = (len(ims) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, rows * cell), (255, 255, 255))
        dd = ImageDraw.Draw(sheet)
        lab = af(20, reg=True)
        for i, (name, bg) in enumerate(ims):
            t = bg.copy(); t.thumbnail((cell - 24, cell - 60))
            r, c = divmod(i, cols)
            sheet.paste(t, (c * cell + 12, r * cell + 12))
            dd.text((c * cell + 14, r * cell + cell - 34), name, fill=(40, 40, 40), font=lab)
        sheet.save(args.sheet, quality=90)
        print("sheet:", args.sheet)


if __name__ == "__main__":
    main()
