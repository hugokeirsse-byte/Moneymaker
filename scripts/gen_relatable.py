#!/usr/bin/env python3
"""
gen_relatable.py — punchlines « relatable » déadpan, typo minimaliste (style
qui domine Redbubble : introverti, fatigue sociale, sarcasme tendre).

Esthétique épurée : grotesk géométrique, centré, ponctuation sèche, un accent
discret. Phrases ORIGINALES (aucune copie d'un autre shop). Fond transparent,
4500 px.

Usage :
    python scripts/gen_relatable.py --out produits/relatable
    python scripts/gen_relatable.py --sheet /tmp/relatable.png
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402

from PIL import Image, ImageDraw, ImageFont  # noqa: E402

INK = (28, 28, 32, 255)
SOFT = (120, 122, 128, 255)
ACCENT = (190, 60, 48, 255)

# id, lignes, police, mot(s) en accent (index de ligne -> accent) optionnel
# Style chestify : sobre, déadpan, « c'est tellement moi ».
PHRASES = [
    ("professionally_tired", ["PROFESSIONALLY", "TIRED"], "geo", {1: ACCENT}),
    ("emotionally_unavailable_chores", ["EMOTIONALLY UNAVAILABLE", "FOR CHORES"], "sora", {}),
    ("running_on_snacks_spite", ["RUNNING ON", "SNACKS & SPITE"], "geo", {1: ACCENT}),
    ("socially_optional", ["SOCIALLY", "OPTIONAL"], "sora", {1: ACCENT}),
    ("here_unfortunately", ["HERE.", "UNFORTUNATELY."], "geo", {1: SOFT}),
    ("low_battery_high_standards", ["LOW BATTERY", "HIGH STANDARDS"], "sora", {1: ACCENT}),
    ("technically_functioning", ["TECHNICALLY", "FUNCTIONING"], "geo", {1: ACCENT}),
    ("out_of_office_mentally", ["OUT OF OFFICE", "MENTALLY"], "sora", {1: ACCENT}),
    ("doing_my_best_allegedly", ["DOING MY BEST", "(ALLEGEDLY)"], "geo", {1: SOFT}),
    ("emotional_support_overthinker", ["EMOTIONAL SUPPORT", "OVERTHINKER"], "sora", {1: ACCENT}),
    ("mildly_feral", ["MILDLY", "FERAL"], "geo", {1: ACCENT}),
    ("my_hobby_not_perceived", ["MY HOBBY IS", "NOT BEING PERCEIVED"], "sora", {}),
    ("introvert_loading", ["INTROVERT", "LOADING…"], "geo", {1: SOFT}),
    ("not_now_not_ever", ["NOT NOW.", "ALSO NOT LATER."], "sora", {1: SOFT}),
    ("powered_by_caffeine_anxiety", ["POWERED BY", "CAFFEINE & ANXIETY"], "geo", {1: ACCENT}),
    ("im_not_arguing", ["I'M NOT ARGUING", "JUST EXPLAINING", "WHY I'M RIGHT"], "sora", {2: ACCENT}),
]


def measure(font, text):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box[1]


def fit_size(lines, key, max_w, hi=700, lo=20):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load_font(key, mid)
        if max(measure(f, t)[0] for t in lines) <= max_w:
            lo = mid
        else:
            hi = mid - 1
    return lo


def render(lines, key, accents, side=4500, margin_ratio=0.12):
    margin = int(side * margin_ratio)
    max_w = side - 2 * margin
    sz = fit_size(lines, key, max_w)
    f = load_font(key, sz)
    gap = int(sz * 0.28)

    dims = [measure(f, t) for t in lines]
    total_h = sum(dd[1] for dd in dims) + gap * (len(lines) - 1)
    img = Image.new("RGBA", (side, total_h + 2 * margin), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)

    y = margin
    for i, (t, (w, h, off)) in enumerate(zip(lines, dims)):
        col = accents.get(i, INK)
        dr.text(((side - w) // 2, y - off), t, font=f, fill=col)
        y += h + gap

    bbox = img.getbbox()
    if bbox is None:
        return img
    img = img.crop(bbox)
    pad = int(side * 0.10)
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(img, (pad, pad))
    if max(out.size) != side:
        r = side / max(out.size)
        out = out.resize((round(out.width * r), round(out.height * r)), Image.LANCZOS)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="produits/relatable")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    sel = set(args.only.split(",")) if args.only else None
    items = [p for p in PHRASES if not sel or p[0] in sel]

    if args.sheet:
        cols = 4
        rows = (len(items) + cols - 1) // cols
        cell = 560
        sheet = Image.new("RGB", (cols * cell, rows * cell), (244, 244, 246))
        dd = ImageDraw.Draw(sheet)
        try:
            lab = load_font("geo", 17)
        except Exception:
            lab = ImageFont.load_default()
        for i, (pid, lines, key, acc) in enumerate(items):
            im = render(lines, key, acc, side=1400)
            im.thumbnail((cell - 40, cell - 56))
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im.convert("RGB"), mask=im.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 20, r * cell + 20))
            dd.text((c * cell + 20, r * cell + cell - 30), pid[:30],
                    fill=(70, 70, 70), font=lab)
        os.makedirs(os.path.dirname(args.sheet) or ".", exist_ok=True)
        sheet.save(args.sheet, quality=90)
        print(f"planche: {args.sheet} ({len(items)})")
        return

    os.makedirs(args.out, exist_ok=True)
    n = 0
    for pid, lines, key, acc in items:
        im = render(lines, key, acc)
        path = os.path.join(args.out, f"{pid}.png")
        im.save(path, dpi=(300, 300))
        print(f"  {path}")
        n += 1
    print(f"\n{n} fichiers → {args.out}")


if __name__ == "__main__":
    main()
