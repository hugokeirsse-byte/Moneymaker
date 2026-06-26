#!/usr/bin/env python3
"""
gen_illustrated.py — designs texte + icône minimaliste en trait fin.

Chaque design combine une phrase Pacifico et un dessin au trait propre
(chat, chien, abeille, patte, café, vinyle, disque de golf, etc.).
Fond transparent, 4500 px, 300 DPI, deux variantes maillot.

Usage :
    python scripts/gen_illustrated.py --out produits/illustrated
    python scripts/gen_illustrated.py --sheet /tmp/illus.png
    python scripts/gen_illustrated.py --only cat_appartient_fr
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402
from typo_variants import VARIANTS, adapt  # noqa: E402

from PIL import Image, ImageDraw  # noqa: E402

INK    = (30, 30, 34, 255)
RED    = (190, 46, 38, 255)
STROKE = 14   # line width base at 4500px; scaled per render size


# ─── Icônes minimalistes ────────────────────────────────────────────────────

def _lw(size, base=4500):
    """Scale a stroke width from base resolution to current size."""
    return max(2, int(STROKE * size / base))


def draw_paw(d, cx, cy, r, color, lw):
    """Empreinte de patte : 1 grande ellipse + 4 petites."""
    pad_rx, pad_ry = int(r * 0.52), int(r * 0.44)
    toe_r = int(r * 0.22)
    d.ellipse([cx - pad_rx, cy - pad_ry, cx + pad_rx, cy + pad_ry],
              outline=color, width=lw)
    offsets = [(-0.55, -0.72), (-0.18, -0.88), (0.18, -0.88), (0.55, -0.72)]
    for dx, dy in offsets:
        tx, ty = int(cx + dx * r), int(cy + dy * r)
        d.ellipse([tx - toe_r, ty - toe_r, tx + toe_r, ty + toe_r],
                  outline=color, width=lw)


def draw_cat(d, cx, cy, r, color, lw):
    """Chat en trait minimal : corps ovale, tête ronde, oreilles, moustaches, queue."""
    # corps
    bx, by = int(r * 0.55), int(r * 0.45)
    body_cy = cy + int(r * 0.38)
    d.ellipse([cx - bx, body_cy - by, cx + bx, body_cy + by], outline=color, width=lw)
    # tête
    hr = int(r * 0.40)
    head_cy = cy - int(r * 0.22)
    d.ellipse([cx - hr, head_cy - hr, cx + hr, head_cy + hr], outline=color, width=lw)
    # oreilles pointues
    ear_h = int(hr * 0.70)
    ear_w = int(hr * 0.38)
    for side in (-1, 1):
        ex = cx + side * int(hr * 0.52)
        pts = [(ex, head_cy - hr),
               (ex - side * ear_w, head_cy - hr - ear_h),
               (ex + side * ear_w, head_cy - hr + int(ear_h * 0.15))]
        d.polygon(pts, outline=color, fill=None)
        d.line(pts + [pts[0]], fill=color, width=lw)
    # yeux
    ey = head_cy - int(hr * 0.12)
    er = max(2, int(hr * 0.14))
    for side in (-1, 1):
        ex = cx + side * int(hr * 0.34)
        d.ellipse([ex - er, ey - er, ex + er, ey + er], fill=color)
    # moustaches
    my = head_cy + int(hr * 0.10)
    mlen = int(hr * 0.85)
    for side in (-1, 1):
        base_x = cx + side * int(hr * 0.08)
        for angle_deg in (-8, 0, 8):
            ang = math.radians(angle_deg + (0 if side == 1 else 180))
            ex2 = base_x + int(math.cos(ang) * mlen * side)
            ey2 = my + int(math.sin(ang) * mlen * 0.3)
            d.line([(base_x, my), (ex2, ey2)], fill=color, width=max(1, lw // 2))
    # queue recourbée (série de points)
    tail_pts = []
    n = 24
    tail_r = int(r * 0.62)
    for i in range(n + 1):
        t = i / n
        angle = math.pi * 0.5 + math.pi * 0.9 * t
        tx = cx + int(bx * 1.05) + int(tail_r * math.cos(angle) * (0.4 + 0.6 * t))
        ty = body_cy + by - int(r * 0.10) - int(tail_r * math.sin(angle) * (0.4 + 0.6 * t))
        tail_pts.append((tx, ty))
    for i in range(len(tail_pts) - 1):
        d.line([tail_pts[i], tail_pts[i + 1]], fill=color, width=lw)


def draw_dog(d, cx, cy, r, color, lw):
    """Chien en trait minimal : corps ovale, tête, oreilles tombantes, queue."""
    # corps
    bx, by = int(r * 0.60), int(r * 0.40)
    body_cy = cy + int(r * 0.35)
    d.ellipse([cx - bx, body_cy - by, cx + bx, body_cy + by], outline=color, width=lw)
    # tête
    hr = int(r * 0.38)
    head_cy = cy - int(r * 0.28)
    d.ellipse([cx - hr, head_cy - hr, cx + hr, head_cy + hr], outline=color, width=lw)
    # oreilles tombantes
    for side in (-1, 1):
        ex = cx + side * int(hr * 0.76)
        ear_pts = [
            (ex, head_cy - int(hr * 0.55)),
            (ex + side * int(hr * 0.44), head_cy - int(hr * 0.20)),
            (ex + side * int(hr * 0.46), head_cy + int(hr * 0.55)),
            (ex + side * int(hr * 0.18), head_cy + int(hr * 0.72)),
            (ex, head_cy + int(hr * 0.50)),
        ]
        d.line(ear_pts, fill=color, width=lw)
    # nez
    nz = max(2, int(hr * 0.20))
    d.ellipse([cx - nz, head_cy + int(hr * 0.38) - nz,
               cx + nz, head_cy + int(hr * 0.38) + nz], fill=color)
    # yeux
    ey = head_cy - int(hr * 0.12)
    er = max(2, int(hr * 0.12))
    for side in (-1, 1):
        ex = cx + side * int(hr * 0.34)
        d.ellipse([ex - er, ey - er, ex + er, ey + er], fill=color)
    # queue recourbée vers le haut
    qx = cx + bx
    qy = body_cy - int(by * 0.30)
    tail_pts = []
    for i in range(18):
        t = i / 17
        ang = math.pi * 0.5 * t
        tail_pts.append((qx + int(r * 0.30 * math.sin(ang)),
                         qy - int(r * 0.48 * t * math.cos(ang * 0.6))))
    for i in range(len(tail_pts) - 1):
        d.line([tail_pts[i], tail_pts[i + 1]], fill=color, width=lw)


def draw_bee(d, cx, cy, r, color, lw):
    """Abeille stylisée : corps ovale, ailes, antennes, rayures."""
    # corps
    bx, by = int(r * 0.35), int(r * 0.55)
    d.ellipse([cx - bx, cy - by, cx + bx, cy + by], outline=color, width=lw)
    # rayures (3 lignes horizontales)
    for frac in (-0.22, 0.0, 0.22):
        y_r = cy + int(by * frac)
        xo = int(math.sqrt(max(0, bx**2 * (1 - (frac * by / by)**2))))
        d.line([(cx - xo + lw, y_r), (cx + xo - lw, y_r)], fill=color, width=lw)
    # ailes
    for side in (-1, 1):
        wx, wy = int(r * 0.72), int(r * 0.36)
        wing_pts = [(cx + side * bx, cy - int(by * 0.28)),
                    (cx + side * (bx + wx), cy - int(by * 0.28) - wy),
                    (cx + side * (bx + wx * 0.55), cy - int(by * 0.05))]
        d.line(wing_pts + [wing_pts[0]], fill=color, width=lw)
    # antennes
    for side in (-1, 1):
        ax = cx + side * int(bx * 0.45)
        d.line([(ax, cy - by), (ax + side * int(r * 0.22), cy - by - int(r * 0.30))],
               fill=color, width=lw)
        d.ellipse([ax + side * int(r * 0.22) - lw * 2,
                   cy - by - int(r * 0.30) - lw * 2,
                   ax + side * int(r * 0.22) + lw * 2,
                   cy - by - int(r * 0.30) + lw * 2], fill=color)


def draw_coffee(d, cx, cy, r, color, lw):
    """Tasse de café avec soucoupe et vapeur."""
    mw, mh = int(r * 0.68), int(r * 0.56)
    top_y = cy - int(r * 0.10)
    bot_y = top_y + mh
    # corps tasse (trapèze)
    tw = int(mw * 0.86)
    pts = [(cx - tw, bot_y), (cx + tw, bot_y),
           (cx + mw, top_y), (cx - mw, top_y)]
    d.polygon(pts, outline=color, fill=None)
    d.line(pts + [pts[0]], fill=color, width=lw)
    # anse
    hx = cx + tw + int(r * 0.04)
    hy_top = top_y + int(mh * 0.20)
    hy_bot = top_y + int(mh * 0.68)
    d.arc([hx, hy_top, hx + int(r * 0.36), hy_bot], -90, 90, fill=color, width=lw)
    # soucoupe
    sw = int(mw * 1.20)
    sy = bot_y + int(r * 0.06)
    d.arc([cx - sw, sy, cx + sw, sy + int(r * 0.15)], 0, 180, fill=color, width=lw)
    # vapeur (3 petites ondes)
    for i, xoff in enumerate((-int(r * 0.22), 0, int(r * 0.22))):
        vx = cx + xoff
        vy = top_y - int(r * 0.10)
        pts_v = [(vx, vy)]
        for j in range(8):
            t = j / 7
            pts_v.append((vx + int(r * 0.08 * math.sin(t * math.pi * 1.5)),
                           vy - int(r * 0.28 * t)))
        d.line(pts_v, fill=color, width=max(1, lw - 2))


def draw_heart(d, cx, cy, r, color, lw):
    """Cœur en trait, construit arc par arc."""
    n = 80
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x = r * 0.95 * (16 * math.sin(t) ** 3) / 16
        y = r * 0.95 * -(15 * math.cos(t) - 5 * math.cos(2 * t)
                         - 2 * math.cos(3 * t) - math.cos(4 * t)) / 15
        pts.append((cx + int(x), cy + int(y)))
    for i in range(len(pts)):
        d.line([pts[i], pts[(i + 1) % len(pts)]], fill=color, width=lw)


def draw_leaf(d, cx, cy, r, color, lw):
    """Feuille simple avec nervure centrale."""
    n = 40
    pts_l, pts_r = [], []
    for i in range(n + 1):
        t = i / n
        angle = math.pi * t - math.pi / 2
        xo = int(r * 0.45 * math.sin(math.pi * t))
        yo = int(r * 0.90 * (t - 0.5))
        pts_l.append((cx - xo, cy + yo))
        pts_r.append((cx + xo, cy + yo))
    all_pts = pts_l + list(reversed(pts_r))
    for i in range(len(all_pts) - 1):
        d.line([all_pts[i], all_pts[i + 1]], fill=color, width=lw)
    d.line([(cx, cy - int(r * 0.45)), (cx, cy + int(r * 0.45))],
           fill=color, width=max(1, lw - 2))
    # quelques nervures latérales
    for frac in (-0.25, 0.0, 0.25):
        y_n = cy + int(r * 0.55 * frac)
        xo_n = int(r * 0.38 * math.sin(math.pi * (0.5 + frac * 0.6)))
        for side in (-1, 1):
            d.line([(cx, y_n), (cx + side * xo_n, y_n - int(r * 0.15))],
                   fill=color, width=max(1, lw - 4))


def draw_vinyl(d, cx, cy, r, color, lw):
    """Disque vinyle : grand cercle, sillon, étiquette centrale."""
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=color, width=lw)
    for fr in (0.72, 0.60, 0.48):
        rr = int(r * fr)
        d.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], outline=color,
                  width=max(1, lw // 3))
    lr = int(r * 0.28)
    d.ellipse([cx - lr, cy - lr, cx + lr, cy + lr], outline=color, width=lw)
    hr = max(2, int(r * 0.06))
    d.ellipse([cx - hr, cy - hr, cx + hr, cy + hr], fill=color)


def draw_disc_golf(d, cx, cy, r, color, lw):
    """Disque de golf : ellipse aplatie avec ligne de vol."""
    rx, ry = r, int(r * 0.30)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=color, width=lw)
    inner_rx, inner_ry = int(rx * 0.60), int(ry * 0.60)
    d.ellipse([cx - inner_rx, cy - inner_ry, cx + inner_rx, cy + inner_ry],
              outline=color, width=max(1, lw // 2))
    # trajectoire hyzer
    traj = []
    for i in range(30):
        t = i / 29
        traj.append((cx - r + int(2 * r * t),
                     cy - ry - int(r * 0.55 * math.sin(math.pi * t * 0.7))))
    for i in range(len(traj) - 1):
        d.line([traj[i], traj[i + 1]], fill=color, width=max(1, lw - 4))


def draw_bread(d, cx, cy, r, color, lw):
    """Miche de pain ronde (sourdough) avec oreille."""
    # corps
    bx, by = int(r * 0.80), int(r * 0.68)
    d.ellipse([cx - bx, cy - by, cx + bx, cy + by], outline=color, width=lw)
    # grigne (ear) en biais
    g_pts = [(cx - int(r * 0.25), cy - int(r * 0.35)),
             (cx + int(r * 0.35), cy - int(r * 0.60)),
             (cx + int(r * 0.32), cy - int(r * 0.45)),
             (cx - int(r * 0.28), cy - int(r * 0.20))]
    d.polygon(g_pts, outline=color, fill=None)
    d.line(g_pts + [g_pts[0]], fill=color, width=lw)
    # croûte lines déco
    for ang_deg in (200, 230, 260):
        ang = math.radians(ang_deg)
        x1 = cx + int(bx * 0.42 * math.cos(ang))
        y1 = cy + int(by * 0.42 * math.sin(ang))
        x2 = cx + int(bx * 0.74 * math.cos(ang))
        y2 = cy + int(by * 0.74 * math.sin(ang))
        d.line([(x1, y1), (x2, y2)], fill=color, width=max(1, lw - 4))


def draw_mushroom(d, cx, cy, r, color, lw):
    """Champignon : pied + chapeau avec spots."""
    stem_w, stem_h = int(r * 0.30), int(r * 0.45)
    cap_rx, cap_ry = int(r * 0.72), int(r * 0.55)
    stem_top = cy + int(r * 0.08)
    # pied
    pts_stem = [(cx - stem_w, cy + r), (cx - stem_w, stem_top),
                (cx + stem_w, stem_top), (cx + stem_w, cy + r)]
    d.line(pts_stem, fill=color, width=lw)
    d.line([(cx - int(r * 0.50), stem_top), (cx + int(r * 0.50), stem_top)],
           fill=color, width=lw)
    # chapeau (demi-ellipse)
    cap_cy = stem_top - int(cap_ry * 0.15)
    for i in range(60):
        t1 = math.pi + math.pi * i / 60
        t2 = math.pi + math.pi * (i + 1) / 60
        d.line([(cx + int(cap_rx * math.cos(t1)), cap_cy + int(cap_ry * math.sin(t1))),
                (cx + int(cap_rx * math.cos(t2)), cap_cy + int(cap_ry * math.sin(t2)))],
               fill=color, width=lw)
    d.line([(cx - cap_rx, cap_cy), (cx + cap_rx, cap_cy)], fill=color, width=lw)
    # spots
    for sx, sy, sr in ((-int(r * 0.28), -int(r * 0.18), int(r * 0.10)),
                        (int(r * 0.22), -int(r * 0.25), int(r * 0.09)),
                        (0, -int(r * 0.40), int(r * 0.08))):
        d.ellipse([cx + sx - sr, cap_cy + sy - sr,
                   cx + sx + sr, cap_cy + sy + sr], outline=color, width=lw)


def draw_camera(d, cx, cy, r, color, lw):
    """Appareil photo : boîtier + objectif + flash."""
    bw, bh = int(r * 0.85), int(r * 0.62)
    top = cy - int(bh * 0.60)
    bot = cy + int(bh * 0.40)
    # boîtier
    d.rectangle([cx - bw, top, cx + bw, bot], outline=color, width=lw)
    # hump (flash + viseur)
    hw = int(bw * 0.34)
    hh = int(bh * 0.24)
    d.rectangle([cx - hw, top - hh, cx + hw, top], outline=color, width=lw)
    # objectif
    lr = int(r * 0.34)
    d.ellipse([cx - lr, cy - lr + int(bh * 0.05),
               cx + lr, cy + lr + int(bh * 0.05)], outline=color, width=lw)
    lr2 = int(lr * 0.62)
    d.ellipse([cx - lr2, cy - lr2 + int(bh * 0.05),
               cx + lr2, cy + lr2 + int(bh * 0.05)], outline=color, width=lw)


def draw_needle_yarn(d, cx, cy, r, color, lw):
    """Aiguille à tricoter et pelote de laine."""
    # pelote
    ball_r = int(r * 0.46)
    ball_cx, ball_cy = cx - int(r * 0.18), cy + int(r * 0.12)
    d.ellipse([ball_cx - ball_r, ball_cy - ball_r,
               ball_cx + ball_r, ball_cy + ball_r], outline=color, width=lw)
    # lignes de laine
    for ang_deg in (30, 60, 90, 120, 150):
        ang = math.radians(ang_deg)
        d.line([(ball_cx - int(ball_r * 0.70 * math.cos(ang)),
                 ball_cy - int(ball_r * 0.70 * math.sin(ang))),
                (ball_cx + int(ball_r * 0.70 * math.cos(ang)),
                 ball_cy + int(ball_r * 0.70 * math.sin(ang)))],
               fill=color, width=max(1, lw // 2))
    # aiguille
    nx1 = cx - int(r * 0.10)
    ny1 = cy - int(r * 0.70)
    nx2 = cx + int(r * 0.62)
    ny2 = cy + int(r * 0.64)
    d.line([(nx1, ny1), (nx2, ny2)], fill=color, width=lw)
    # pointe
    d.polygon([(nx2, ny2),
               (nx2 - lw * 3, ny2 - lw * 5),
               (nx2 - lw * 5, ny2 - lw * 3)], fill=color)
    # tête de l'aiguille
    d.ellipse([nx1 - lw * 2, ny1 - lw * 2, nx1 + lw * 2, ny1 + lw * 2], fill=color)


ICON_MAP = {
    "paw":        draw_paw,
    "cat":        draw_cat,
    "dog":        draw_dog,
    "bee":        draw_bee,
    "coffee":     draw_coffee,
    "heart":      draw_heart,
    "leaf":       draw_leaf,
    "vinyl":      draw_vinyl,
    "disc":       draw_disc_golf,
    "bread":      draw_bread,
    "mushroom":   draw_mushroom,
    "camera":     draw_camera,
    "yarn":       draw_needle_yarn,
}


# ─── Catalogue ──────────────────────────────────────────────────────────────
# (id, lang, icon_key, lines[], accent_index, icon_color_key)
# icon_color_key : "ink" ou "accent"

DESIGNS = [
    # Chats
    ("cat_appartient_fr",  "fr", "cat",
     ["J'APPARTIENS", "À MON CHAT"], 1, "accent"),
    ("cat_appartient_en",  "en", "cat",
     ["I BELONG", "TO MY CAT"], 1, "accent"),
    ("cat_appartient_de",  "de", "cat",
     ["ICH GEHÖRE", "MEINER KATZE"], 1, "accent"),

    # Chiens
    ("dog_appartient_fr",  "fr", "dog",
     ["J'APPARTIENS", "À MON CHIEN"], 1, "accent"),
    ("dog_appartient_en",  "en", "dog",
     ["I BELONG", "TO MY DOG"], 1, "accent"),

    # Patte / amour animaux
    ("paw_love_fr",        "fr", "paw",
     ["ADOPTE, NE", "MAGASINE PAS"], 1, "accent"),
    ("paw_love_en",        "en", "paw",
     ["ADOPT", "DON'T SHOP"], 1, "accent"),

    # Abeille
    ("bee_save_fr",        "fr", "bee",
     ["SAUVEZ LES ABEILLES", "DEMANDEZ-MOI COMMENT"], 0, "accent"),
    ("bee_save_en",        "en", "bee",
     ["SAVE THE BEES", "I'M THE BEEKEEPER"], 1, "ink"),

    # Café
    ("coffee_fr",          "fr", "coffee",
     ["MAIS D'ABORD", "LE CAFÉ"], 1, "accent"),
    ("coffee_en",          "en", "coffee",
     ["BUT FIRST", "COFFEE"], 1, "accent"),
    ("coffee_blood_en",    "en", "coffee",
     ["MY BLOOD TYPE", "IS COFFEE"], 0, "accent"),

    # Cœur
    ("heart_sourdough_fr", "fr", "heart",
     ["LE LEVAIN", "C'EST L'AMOUR"], 1, "accent"),
    ("heart_sourdough_en", "en", "heart",
     ["SOURDOUGH", "IS MY LOVE LANGUAGE"], 0, "accent"),
    ("heart_plants_fr",    "fr", "leaf",
     ["MES PLANTES", "NE JUGENT PAS"], 1, "accent"),

    # Vinyle
    ("vinyl_fr",           "fr", "vinyl",
     ["LA VIE EST TROP COURTE", "POUR LE MP3"], 1, "accent"),
    ("vinyl_en",           "en", "vinyl",
     ["LIFE IS TOO SHORT", "FOR STREAMING"], 1, "accent"),

    # Disc golf
    ("disc_hyzer_fr",      "fr", "disc",
     ["HYZER", "OU MOURIR"], 1, "accent"),
    ("disc_hyzer_en",      "en", "disc",
     ["HYZER", "OR DIE TRYING"], 1, "accent"),

    # Pain / sourdough
    ("bread_starter_fr",   "fr", "bread",
     ["J'AI NOURRI MON LEVAIN", "AVANT DE TE RÉPONDRE"], 0, "accent"),
    ("bread_starter_en",   "en", "bread",
     ["I FED MY STARTER", "BEFORE TEXTING BACK"], 0, "accent"),

    # Champignon
    ("mush_forager_fr",    "fr", "mushroom",
     ["CUEILLEUR", "DE CHAMPIGNONS"], 0, "ink"),
    ("mush_forager_en",    "en", "mushroom",
     ["I FIND", "THE GOOD FUNGI"], 1, "accent"),

    # Photo
    ("photo_shoot_fr",     "fr", "camera",
     ["JE TIRE D'ABORD", "JE DEMANDE APRÈS"], 0, "accent"),
    ("photo_shoot_en",     "en", "camera",
     ["SHOOT FIRST", "ASK QUESTIONS LATER"], 0, "accent"),

    # Tricot
    ("yarn_frog_fr",       "fr", "yarn",
     ["JE DETRICOTE ENCORE", "MAIS JE REFERAI"], 0, "accent"),
    ("yarn_gauge_en",      "en", "yarn",
     ["THE GAUGE LIED.", "I FROGGED ANYWAY."], 0, "accent"),
]


# ─── Rendu ──────────────────────────────────────────────────────────────────

def measure(font, text):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box[1]


def fit_size(lines, max_w, hi=760, lo=20):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load_font("script", mid)
        if max(measure(f, t)[0] for t in lines) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


def render(design, variant, side=4500, margin_ratio=0.09):
    _, _lang, icon_key, lines, accent_idx, icon_col_key = design
    ink_col  = adapt(INK, variant)
    red_col  = adapt(RED, variant)
    icon_color = red_col if icon_col_key == "accent" else ink_col

    margin  = int(side * margin_ratio)
    # Layout: icon occupe ~38% de la largeur, texte ~52%, gap ~4%
    icon_w  = int(side * 0.38)
    gap_w   = int(side * 0.04)
    text_w  = side - icon_w - gap_w - 2 * margin

    sz = fit_size(lines, text_w, hi=int(side * 0.18))
    f  = load_font("script", sz)
    line_gap = int(sz * 0.12)

    dims = [measure(f, t) for t in lines]
    text_h = sum(d[1] for d in dims) + line_gap * (len(lines) - 1)

    icon_r = int(icon_w * 0.42)
    total_h = max(text_h, icon_r * 2) + 2 * margin

    img = Image.new("RGBA", (side, total_h), (0, 0, 0, 0))
    dr  = ImageDraw.Draw(img)

    # icône : centré verticalement à gauche
    icon_cx = margin + icon_w // 2
    icon_cy = total_h // 2
    if icon_key in ICON_MAP:
        ICON_MAP[icon_key](dr, icon_cx, icon_cy, icon_r, icon_color, _lw(side))

    # texte : centré verticalement à droite de l'icône
    text_x_center = margin + icon_w + gap_w + text_w // 2
    y = (total_h - text_h) // 2
    for i, (t, (w, h, off)) in enumerate(zip(lines, dims)):
        col = red_col if i == accent_idx else ink_col
        dr.text((text_x_center - w // 2, y - off), t, font=f, fill=col)
        y += h + line_gap

    bbox = img.getbbox()
    if bbox is None:
        return img
    img = img.crop(bbox)
    pad = int(side * 0.07)
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(img, (pad, pad))
    if max(out.size) != side:
        k = side / max(out.size)
        out = out.resize((round(out.width * k), round(out.height * k)), Image.LANCZOS)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out",     default="produits/illustrated")
    ap.add_argument("--sheet",   default="")
    ap.add_argument("--only",    default="")
    ap.add_argument("--lang",    default="")
    ap.add_argument("--variant", default="both", choices=["both", "dark", "light"])
    args = ap.parse_args()

    sel   = set(args.only.split(",")) if args.only else None
    items = [d for d in DESIGNS
             if (not sel or d[0] in sel)
             and (not args.lang or d[1] == args.lang)]

    if args.sheet:
        cols = 3
        cell = 780
        rows = (len(items) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, rows * cell), (244, 244, 246))
        for i, d in enumerate(items):
            im = render(d, "dark", side=1500)
            im.thumbnail((cell - 40, cell - 60))
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 20, r * cell + 20))
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=90)
        print(f"planche: {args.sheet} ({len(items)})")
        return

    variants = list(VARIANTS) if args.variant == "both" else [args.variant]
    os.makedirs(args.out, exist_ok=True)
    n = 0
    for d in items:
        for v in variants:
            im = render(d, v)
            im.save(os.path.join(args.out, f"{d[0]}__{v}.png"), dpi=(300, 300))
            n += 1
    print(f"{n} fichiers ({len(items)} × {len(variants)}) → {args.out}")


if __name__ == "__main__":
    main()
