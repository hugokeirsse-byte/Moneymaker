#!/usr/bin/env python3
"""
typo_ornaments.py — embellissements typographiques partagés (noir + rouge).

Cinq ornements validés, appliqués en alternance autour d'un bloc de texte :
    - "wave"     : vague calligraphiée au-dessus et en dessous
    - "double"   : double filet bicolore (noir + rouge) au-dessus et en dessous
    - "sparkles" : étoiles / éclats autour du bloc
    - "quotes"   : grands guillemets décoratifs en coin
    - "frame"    : cadre arrondi noir + liseré rouge intérieur

API :
    name = pick_ornament(i)                       # alternance déterministe
    apply_ornament(draw, name, bbox, ink, accent, # dessine autour du bbox
                   scale=1.0, quote_font=None)

bbox = (x0, y0, x1, y1) du bloc de texte déjà dessiné. Le dessin déborde
au-dessus / en dessous / sur les côtés : prévoir une marge suffisante sur le
canevas (les générateurs recadrent ensuite sur le contenu réel).
"""
import math

from PIL import Image, ImageDraw, ImageFilter

# Ornements dessinés AUTOUR du texte (fond transparent)
ORNAMENTS = ("wave", "double", "sparkles", "quotes", "frame")
# Les 6 modèles distincts ; "sticker" = carte blanche (traité à part)
STYLES = ("wave", "double", "sparkles", "quotes", "frame", "sticker")


def pick_ornament(i):
    """Alternance sur les 5 ornements autour-du-texte."""
    return ORNAMENTS[i % len(ORNAMENTS)]


def pick_style(i):
    """Style unique retenu : les étoiles / éclats (sparkles) sur tous les designs."""
    return "sparkles"


# ─── primitives ─────────────────────────────────────────────────────────────

def _wave(d, cx, y, width, color, thick):
    n = 130
    half = width / 2.0
    pts = []
    for i in range(n + 1):
        t = i / n
        x = cx - half + t * width
        env = math.sin(math.pi * t)
        yy = y + thick * 2.4 * env * math.sin(2 * math.pi * 1.5 * t)
        pts.append((x, yy))
    for i in range(n):
        env = math.sin(math.pi * (i + 0.5) / n)
        w = max(1, thick * (0.28 + 0.72 * env))
        d.line([pts[i], pts[i + 1]], fill=color, width=int(round(w)))
    r = thick * 0.9
    for px, py in (pts[0], pts[-1]):
        d.ellipse([px - r, py - r, px + r, py + r], fill=color)


def _star(d, cx, cy, r, color):
    pts = []
    for k in range(8):
        ang = math.pi / 4 * k - math.pi / 2
        rr = r if k % 2 == 0 else r * 0.40
        pts.append((cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
    d.polygon(pts, fill=color)


# ─── ornements ──────────────────────────────────────────────────────────────

def _orn_wave(d, x0, y0, x1, y1, ink, accent, scale, qf):
    w = int((x1 - x0) * 0.60)
    cx = (x0 + x1) // 2
    thick = max(3, int(8 * scale))
    gap = int(46 * scale)
    _wave(d, cx, y0 - gap, w, accent, thick)
    _wave(d, cx, y1 + gap, w, accent, thick)


def _orn_double(d, x0, y0, x1, y1, ink, accent, scale, qf):
    cx = (x0 + x1) // 2
    w = int((x1 - x0) * 0.64)
    t1 = max(3, int(7 * scale))
    t2 = max(2, int(5 * scale))
    off = int(16 * scale)
    gap = int(34 * scale)
    for base, s in ((y0 - gap, -1), (y1 + gap, 1)):
        d.line([(cx - w // 2, base), (cx + w // 2, base)], fill=ink, width=t1)
        d.line([(cx - w // 3, base + s * off), (cx + w // 3, base + s * off)],
               fill=accent, width=t2)


def _orn_sparkles(d, x0, y0, x1, y1, ink, accent, scale, qf):
    cx = (x0 + x1) // 2
    cy = (y0 + y1) // 2
    big = int(95 * scale)
    mid = int(64 * scale)
    sm = int(46 * scale)
    xs = int(30 * scale)
    o = int(115 * scale)
    # accent (red) stars — éclats principaux autour du bloc
    spots_a = [
        (x0 - o,                 y0 - int(o * 0.5),     big),
        (x1 + o,                 y0 - int(o * 0.2),     mid),
        (x0 - int(o * 0.5),      y1 + int(o * 0.7),     mid),
        (x1 + int(o * 0.8),      y1 + int(o * 0.5),     big),
        (cx,                     y0 - int(135 * scale), mid),
        (cx,                     y1 + int(135 * scale), sm),
        (x0 - int(o * 0.2),      cy + int(o * 0.1),     sm),
        (x1 + int(o * 0.4),      cy - int(o * 0.2),     sm),
        (cx - int(0.30 * (x1 - x0)), y0 - int(o * 0.75), sm),
        (cx + int(0.30 * (x1 - x0)), y1 + int(o * 0.75), sm),
    ]
    # ink (dark) stars plus petites — profondeur
    spots_i = [
        (x0 - int(o * 0.7),      y1 - int(o * 0.4),     sm),
        (x1 + int(o * 0.6),      y0 + int(o * 0.4),     sm),
        (cx - int(180 * scale),  y0 - int(72 * scale),  int(34 * scale)),
        (cx + int(180 * scale),  y1 + int(72 * scale),  int(34 * scale)),
        (x0 - int(o * 1.05),     cy - int(o * 0.35),    xs),
        (x1 + int(o * 1.05),     cy + int(o * 0.45),    xs),
    ]
    for x, y, r in spots_a:
        _star(d, x, y, r, accent)
    for x, y, r in spots_i:
        _star(d, x, y, r, ink)


def _orn_quotes(d, x0, y0, x1, y1, ink, accent, scale, qf):
    if qf is None:
        # repli : étoiles si pas de police fournie
        _orn_sparkles(d, x0, y0, x1, y1, ink, accent, scale, qf)
        return
    lq, rq = chr(0x201C), chr(0x201D)
    box = qf.getbbox(lq)
    qw, qh = box[2] - box[0], box[3] - box[1]
    d.text((x0 - qw - int(10 * scale), y0 - int(qh * 0.55) - box[1]),
           lq, font=qf, fill=accent)
    d.text((x1 + int(10 * scale), y1 - int(qh * 0.55) - box[1]),
           rq, font=qf, fill=accent)


def _orn_frame(d, x0, y0, x1, y1, ink, accent, scale, qf):
    pad = int(54 * scale)
    box = [x0 - pad, y0 - pad, x1 + pad, y1 + pad]
    rad = int(30 * scale)
    d.rounded_rectangle(box, radius=rad, outline=ink, width=max(4, int(8 * scale)))
    inner = [box[0] + int(16 * scale), box[1] + int(16 * scale),
             box[2] - int(16 * scale), box[3] - int(16 * scale)]
    d.rounded_rectangle(inner, radius=max(2, rad - int(10 * scale)),
                        outline=accent, width=max(2, int(4 * scale)))


_DISPATCH = {
    "wave": _orn_wave,
    "double": _orn_double,
    "sparkles": _orn_sparkles,
    "quotes": _orn_quotes,
    "frame": _orn_frame,
}


def apply_ornament(d, name, bbox, ink, accent, scale=1.0, quote_font=None):
    fn = _DISPATCH.get(name, _orn_wave)
    fn(d, bbox[0], bbox[1], bbox[2], bbox[3], ink, accent, scale, quote_font)


# ─── 6e modèle : étiquette / autocollant ────────────────────────────────────

def _reflect(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    dd = (dx * dx + dy * dy) or 1
    t = ((px - ax) * dx + (py - ay) * dy) / dd
    fx, fy = ax + t * dx, ay + t * dy
    return (2 * fx - px, 2 * fy - py)


def sticker_layer(size, bbox, scale=1.0, dark=False):
    """Carte rectangulaire blanche avec coin bas-droite qui se décolle.

    `bbox` = boîte du texte. La carte est plus large que haute (rectangulaire)
    et la corne tient dans la marge du coin → n'empiète jamais sur le texte.
    Retour : calque RGBA `size` à composer AVANT de dessiner le texte.
    """
    W, H = size
    x0, y0, x1, y1 = bbox
    padx = int(220 * scale)
    pady = int(170 * scale)
    cx0, cy0, cx1, cy1 = x0 - padx, y0 - pady, x1 + padx, y1 + pady
    rad = int(70 * scale)
    # corne : tient dans la marge pour ne pas toucher les mots
    peel = int(min(padx, pady) * 0.78)
    card = (245, 245, 247, 255) if not dark else (236, 236, 238, 255)

    layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # ombre portée
    sh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle(
        [cx0 + int(16 * scale), cy0 + int(20 * scale),
         cx1 + int(16 * scale), cy1 + int(20 * scale)], radius=rad, fill=(0, 0, 0, 85))
    sh = sh.filter(ImageFilter.GaussianBlur(int(24 * scale)))
    layer.alpha_composite(sh)

    # corps (coin bas-droite retiré par le pli)
    A = (cx1 - peel, cy1)
    B = (cx1, cy1 - peel)
    body = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    db = ImageDraw.Draw(body)
    db.rounded_rectangle([cx0, cy0, cx1, cy1], radius=rad, fill=card)
    db.polygon([A, (cx1, cy1), B], fill=(0, 0, 0, 0))
    layer.alpha_composite(body)

    # ombre de la corne sur la carte
    csh = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    o = int(22 * scale)
    ImageDraw.Draw(csh).polygon(
        [(A[0] - o, A[1] - o), (cx1 - o, cy1 - o), (B[0] - o, B[1] - o)],
        fill=(0, 0, 0, 110))
    csh = csh.filter(ImageFilter.GaussianBlur(int(16 * scale)))
    layer.alpha_composite(csh)

    # corne repliée (dos du papier, dégradé)
    tip = _reflect((cx1, cy1), A, B)
    xs = [A[0], B[0], tip[0]]; ys = [A[1], B[1], tip[1]]
    bx0, by0 = int(min(xs)), int(min(ys))
    bx1, by1 = int(max(xs)) + 1, int(max(ys)) + 1
    gw, gh = max(1, bx1 - bx0), max(1, by1 - by0)
    grad = Image.new("RGBA", (gw, gh), (0, 0, 0, 0))
    pg = grad.load()
    nx, ny = (B[1] - A[1]), -(B[0] - A[0])
    nl = math.hypot(nx, ny) or 1
    nx, ny = nx / nl, ny / nl
    projs = [((px - A[0]) * nx + (py - A[1]) * ny) for px, py in (A, B, tip)]
    pmin, pmax = min(projs), max(projs)
    rng = (pmax - pmin) or 1
    for j in range(gh):
        for i in range(gw):
            t = (((bx0 + i) - A[0]) * nx + ((by0 + j) - A[1]) * ny - pmin) / rng
            t = max(0.0, min(1.0, t))
            g = int(230 - 72 * t)
            pg[i, j] = (g, g, g, 255)
    mask = Image.new("L", (gw, gh), 0)
    ImageDraw.Draw(mask).polygon(
        [(A[0] - bx0, A[1] - by0), (B[0] - bx0, B[1] - by0), (tip[0] - bx0, tip[1] - by0)],
        fill=255)
    grad.putalpha(mask)
    layer.alpha_composite(grad, (bx0, by0))
    ImageDraw.Draw(layer).line([A, B], fill=(150, 150, 150, 255),
                               width=max(2, int(6 * scale)))
    return layer
