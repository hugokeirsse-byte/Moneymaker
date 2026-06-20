#!/usr/bin/env python3
"""
gen_fake_quotes.py — fausses « citations d'auteur » absurdes.

Une phrase stupide présentée comme une citation profonde, attribuée à un auteur
célèbre (domaine public). Mise en page citation élégante (serif Playfair,
guillemets, filet, attribution en petites capitales).

Portrait OPTIONNEL : si assets/portraits/<slug>.(jpg|png) existe, il est
détouré en médaillon rond en haut ; sinon un médaillon monogramme élégant.
(NB : récupération des photos PD à faire hors de cet environnement — Wikimedia
y est bloqué.)

Deux variantes maillot, fond transparent, 4500 px.

Usage :
    python scripts/gen_fake_quotes.py --out produits/fake_quotes
    python scripts/gen_fake_quotes.py --sheet /tmp/quotes.png
"""
import argparse
import glob
import os
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from typo_fonts import load_font  # noqa: E402
from typo_variants import VARIANTS, adapt  # noqa: E402

from PIL import Image, ImageDraw, ImageOps  # noqa: E402

INK = (28, 26, 24, 255)
PORTRAITS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                             "assets", "portraits")

# id, lang, slug_portrait, citation, auteur, dates
QUOTES = [
    ("hugo_saucisse", "fr", "victor_hugo", "Ho-hisse la saucisse !", "Victor Hugo", "1802–1885"),
    ("descartes_fatigue", "fr", "descartes", "Je pense, donc je suis fatigué.", "René Descartes", "1596–1650"),
    ("napoleon_escrime", "fr", "napoleon", "Pas ce soir, j'ai escrime.", "Napoléon Bonaparte", "1769–1821"),
    ("voltaire_wifi", "fr", "voltaire", "Le wifi de l'âme, c'est l'amitié.", "Voltaire", "1694–1778"),
    ("moliere_steak", "fr", "moliere", "Couvrez ce steak que je ne saurais cuire.", "Molière", "1622–1673"),
    ("shakespeare_nap", "en", "shakespeare", "To nap, or not to nap. Dumb question.", "William Shakespeare", "1564–1616"),
    ("poe_raven", "en", "poe", "Quoth the raven: not today.", "Edgar Allan Poe", "1809–1849"),
    ("darwin_lazy", "en", "darwin", "Survival of the laziest.", "Charles Darwin", "1809–1882"),
    ("nietzsche_running", "en", "nietzsche", "That which doesn't kill me better start running.", "Friedrich Nietzsche", "1844–1900"),
    ("beethoven_excuses", "en", "beethoven", "I can't hear your excuses either.", "Ludwig van Beethoven", "1770–1827"),
]


def measure(font, text):
    box = font.getbbox(text)
    return box[2] - box[0], box[3] - box[1], box[1]


def find_portrait(slug):
    for ext in ("jpg", "jpeg", "png", "webp"):
        hits = glob.glob(os.path.join(PORTRAITS_DIR, f"{slug}.{ext}"))
        if hits:
            return hits[0]
    return None


def medallion(slug, author, diam, ink):
    """Médaillon rond : photo PD si dispo, sinon monogramme élégant."""
    m = Image.new("RGBA", (diam, diam), (0, 0, 0, 0))
    d = ImageDraw.Draw(m)
    ring = max(6, diam // 40)
    p = find_portrait(slug)
    if p:
        try:
            photo = Image.open(p).convert("RGB")
            photo = ImageOps.fit(photo, (diam, diam), Image.LANCZOS)
            mask = Image.new("L", (diam, diam), 0)
            ImageDraw.Draw(mask).ellipse([0, 0, diam, diam], fill=255)
            m.paste(photo, (0, 0), mask)
        except Exception:
            p = None
    if not p:
        d.ellipse([ring, ring, diam - ring, diam - ring], outline=ink, width=ring)
        initials = "".join(w[0] for w in author.split()[:2]).upper()
        f = load_font("elegant", int(diam * 0.42))
        iw, ih, ioff = measure(f, initials)
        d.text(((diam - iw) // 2, (diam - ih) // 2 - ioff), initials, font=f, fill=ink)
    # liseré
    d.ellipse([ring // 2, ring // 2, diam - ring // 2, diam - ring // 2],
              outline=ink, width=ring)
    return m


def render(q, variant, side=4500):
    ink = adapt(INK, variant)
    _, lang, slug, quote, author, dates = q
    img = Image.new("RGBA", (side, side), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    margin = int(side * 0.12)
    max_w = side - 2 * margin

    # médaillon en haut
    diam = int(side * 0.30)
    med = medallion(slug, author, diam, ink)
    img.alpha_composite(med, ((side - diam) // 2, int(side * 0.10)))

    # citation : Playfair italic, multi-lignes, gros guillemets
    qf_size = int(side * 0.085)
    quote_txt = f"“{quote}”"
    # wrap pour tenir dans max_w
    for size in range(qf_size, 40, -6):
        f = load_font("elegant", size)
        avg = measure(f, "n")[0] or 1
        wrapped = textwrap.wrap(quote_txt, width=max(8, int(max_w / avg)))
        if wrapped and max(measure(f, ln)[0] for ln in wrapped) <= max_w and len(wrapped) <= 4:
            break
    f = load_font("elegant", size)
    line_h = int(size * 1.18)
    y = int(side * 0.50)
    for ln in wrapped:
        w, h, off = measure(f, ln)
        d.text(((side - w) // 2, y - off), ln, font=f, fill=ink)
        y += line_h

    # filet + attribution
    y += int(side * 0.02)
    rule_w = int(side * 0.16)
    d.line([(side // 2 - rule_w, y), (side // 2 + rule_w, y)], fill=ink, width=max(4, side // 700))
    y += int(side * 0.035)
    af = load_font("cond", int(side * 0.045))
    attr = "— " + author.upper()
    aw, ah, aoff = measure(af, attr)
    d.text(((side - aw) // 2, y - aoff), attr, font=af, fill=ink)
    y += int(ah * 1.5)
    df = load_font("cond", int(side * 0.026))
    dw, dh, doff = measure(df, dates)
    d.text(((side - dw) // 2, y - doff), dates, font=df, fill=adapt((120, 118, 116, 255), variant))

    bbox = img.getbbox()
    img = img.crop(bbox)
    pad = int(side * 0.08)
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(img, (pad, pad))
    if max(out.size) != side:
        k = side / max(out.size)
        out = out.resize((round(out.width * k), round(out.height * k)), Image.LANCZOS)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="produits/fake_quotes")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--only", default="")
    ap.add_argument("--lang", default="")
    ap.add_argument("--variant", default="both", choices=["both", "dark", "light"])
    args = ap.parse_args()

    sel = set(args.only.split(",")) if args.only else None
    items = [q for q in QUOTES if (not sel or q[0] in sel) and (not args.lang or q[1] == args.lang)]

    if args.sheet:
        cols = 3
        rows = (len(items) + cols - 1) // cols
        cell = 640
        sheet = Image.new("RGB", (cols * cell, rows * cell), (244, 242, 238))
        for i, q in enumerate(items):
            im = render(q, "dark", side=1400)
            im.thumbnail((cell - 40, cell - 40))
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
    for q in items:
        for v in variants:
            im = render(q, v)
            im.save(os.path.join(args.out, f"{q[0]}__{q[1]}__{v}.png"), dpi=(300, 300))
            n += 1
    print(f"{n} fichiers ({len(items)} × {len(variants)}) → {args.out}")


if __name__ == "__main__":
    main()
