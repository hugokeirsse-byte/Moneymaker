#!/usr/bin/env python3
"""
gen_heart.py — série « I ❤ X ».

Deux usages dans le même générateur :
  - barré/remplacé : « I ❤ Men » (Men barré) → « Cats » en rouge en dessous
    (champ "replacement" présent) ;
  - parenthèses / jeu de mots : « I ❤ (Wo)Men » sur une ligne, markup *rouge*
    possible (pas de "replacement").

Cœur dessiné (courbe paramétrique), rempli en rouge. Écriture Pacifico,
encre noire, fond transparent, 4500 px, 300 DPI, deux variantes maillot.

Usage :
    python scripts/gen_heart.py --out produits/heart
    python scripts/gen_heart.py --sheet /tmp/heart.png
"""
import argparse
import json
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402
from typo_variants import VARIANTS, adapt  # noqa: E402
from typo_ornaments import pick_style, apply_ornament, sticker_layer  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

DATA_PATH = "data/heart.json"
FONT = "script"
INK = (28, 28, 32, 255)
RED = (190, 46, 38, 255)


def heart_points(cx, cy, w):
    """Polygone d'un cœur centré en (cx, cy), largeur ~w."""
    raw = []
    n = 120
    for i in range(n + 1):
        t = 2 * math.pi * i / n
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t)
              - 2 * math.cos(3 * t) - math.cos(4 * t))
        raw.append((x, y))
    xs = [p[0] for p in raw]
    ys = [p[1] for p in raw]
    k = w / (max(xs) - min(xs))
    mx = (max(xs) + min(xs)) / 2
    my = (max(ys) + min(ys)) / 2
    return [(cx + (x - mx) * k, cy + (y - my) * k) for x, y in raw]


def parse_seg(line):
    parts = line.split("*")
    return [(s, i % 2 == 1) for i, s in enumerate(parts) if s != ""]


def seg_w(f, toks):
    return sum(f.getlength(t) for t, _ in toks)


def render(entry, variant, idx=0, side=4500):
    style = entry.get("ornament", pick_style(idx))
    sticker = (style == "sticker")
    if sticker:
        ink, red = INK, RED
    else:
        ink = adapt(INK, variant)
        red = adapt(RED, variant)

    pre = entry.get("pre", "I")
    post = entry["post"]
    repl = entry.get("replacement")
    heart_ratio = 0.92  # cœur ≈ hauteur de capitale

    # ligne 1 = pre + [cœur] + post   (post peut contenir *markup* si pas de strike)
    pre_toks = parse_seg(pre)
    post_toks = parse_seg(post) if not repl else [(post, False)]
    repl_toks = parse_seg(repl) if repl else []

    margin = int(side * (0.16 if sticker else 0.12))
    max_w = side - 2 * margin

    # cœur collé à l'apostrophe quand pre finit par « ' » (« J'❤ »)
    tight = pre.rstrip().endswith("'")

    # estimation taille : la ligne 1 inclut le cœur (~1 cap + gaps)
    def line1_w(f):
        cap = f.getbbox("M")
        ch = (cap[3] - cap[1]) * heart_ratio
        gap = f.size * 0.22
        gb = f.size * 0.02 if tight else gap
        return seg_w(f, pre_toks) + gb + ch + gap + seg_w(f, post_toks)

    lo, hi = 20, int(side * 0.16)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load_font(FONT, mid)
        w1 = line1_w(f)
        w2 = seg_w(f, repl_toks) if repl_toks else 0
        if max(w1, w2) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    sz = lo
    f = load_font(FONT, sz)
    fr = load_font(FONT, int(sz * 1.08))

    cap = f.getbbox("ÀÇgjpqy")
    lh = cap[3] - cap[1]
    base_off = cap[1]
    capbox = f.getbbox("M")
    ch = (capbox[3] - capbox[1]) * heart_ratio
    gap_h = sz * 0.22
    gap_v = int(sz * 0.18)

    # hauteur totale
    n_lines = 1 + (1 if repl_toks else 0)
    if repl_toks:
        rcap = fr.getbbox("ÀÇgjpqy")
        rlh = rcap[3] - rcap[1]
        roff = rcap[1]
        total_h = lh + gap_v + int(sz * 0.10) + rlh
    else:
        total_h = lh

    img = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx = side // 2
    top = side // 2 - total_h // 2

    w1 = line1_w(f)
    block_w = max(w1, seg_w(fr, repl_toks) if repl_toks else 0)
    bbox = (cx - block_w / 2, top, cx + block_w / 2, top + total_h)

    if sticker:
        img.alpha_composite(sticker_layer((side, side), bbox, side / 4500.0))

    # ── ligne 1 : pre  ❤  post ──
    y = top
    x = cx - w1 / 2
    for seg, acc in pre_toks:
        d.text((x, y - base_off), seg, font=f, fill=red if acc else ink)
        x += f.getlength(seg)
    x += (sz * 0.02 if tight else gap_h)
    hy = y - base_off + (capbox[1] + (capbox[3] - capbox[1]) / 2)
    pts = heart_points(x + ch / 2, hy, ch)
    d.polygon(pts, fill=red)
    x += ch + gap_h
    post_x0 = x
    for seg, acc in post_toks:
        d.text((x, y - base_off), seg, font=f, fill=red if (acc and not repl) else ink)
        x += f.getlength(seg)
    post_x1 = x

    # barre le mot "post" si remplacement
    if repl_toks:
        line_y = y - base_off + capbox[1] + (capbox[3] - capbox[1]) / 2
        lw = max(9, int(sz * 0.075))
        ext = int(sz * 0.06)
        d.line([(post_x0 - ext, line_y), (post_x1 + ext, line_y)], fill=red, width=lw)
        # ── ligne 2 : remplacement (rouge) ──
        y2 = top + lh + gap_v + int(sz * 0.10)
        w2 = seg_w(fr, repl_toks)
        x = cx - w2 / 2
        for seg, acc in repl_toks:
            d.text((x, y2 - roff), seg, font=fr, fill=red)
            x += fr.getlength(seg)

    if style and not sticker:
        qf = load_font(FONT, int(sz * 1.5))
        apply_ornament(d, style, bbox, ink, red, scale=side / 4500.0, quote_font=qf)

    bb = img.getbbox()
    if bb is None:
        return img
    img = img.crop(bb)
    pad = int(side * 0.09)
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(img, (pad, pad))
    if max(out.size) != side:
        k = side / max(out.size)
        out = out.resize((round(out.width * k), round(out.height * k)), Image.LANCZOS)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="produits/heart")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--lang", default="")
    ap.add_argument("--data", default=DATA_PATH)
    ap.add_argument("--variant", default="both", choices=["both", "dark", "light"])
    args = ap.parse_args()

    data = json.load(open(args.data, encoding="utf-8"))
    entries = data["entries"]
    sel = set(args.only.split(",")) if args.only else None
    items = [(i, e) for i, e in enumerate(entries)
             if (not sel or e["id"] in sel) and (not args.lang or e.get("lang") == args.lang)]

    if args.sheet:
        cols = 4
        cell = 600
        rows = (len(items) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * cell, rows * cell), (246, 246, 248))
        dd = ImageDraw.Draw(sheet)
        try:
            lab = load_font("fjalla", 16)
        except Exception:
            lab = ImageFont.load_default()
        for k, (i, e) in enumerate(items):
            im = render(e, "dark", idx=i, side=1300)
            im.thumbnail((cell - 40, cell - 60))
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(k, cols)
            sheet.paste(bg, (c * cell + 20, r * cell + 20))
            dd.text((c * cell + 20, r * cell + cell - 26), e["id"][:34],
                    fill=(70, 70, 70), font=lab)
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=88)
        print(f"planche: {args.sheet} ({len(items)})")
        return

    variants = list(VARIANTS) if args.variant == "both" else [args.variant]
    os.makedirs(args.out, exist_ok=True)
    n = 0
    for i, e in items:
        for v in variants:
            im = render(e, v, idx=i)
            im.save(os.path.join(args.out, f"{e['id']}__{v}.png"), dpi=(300, 300))
            n += 1
    print(f"{n} fichiers ({len(items)} × {len(variants)} variantes) → {args.out}")


if __name__ == "__main__":
    main()
