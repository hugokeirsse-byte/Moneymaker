#!/usr/bin/env python3
"""
Planche comparative des faces (cover_ebook.jpg de chaque concept) + bande de
vignettes 100 px (test miniature Amazon). Sauve dans le dossier des couvertures.

Usage :
  python contact_sheet.py --covers output/covers --concepts decor_dechire,chambre_plateau,saul_bass,oeil_ecran
"""
from __future__ import annotations

import argparse
import os

from PIL import Image, ImageDraw, ImageFont

BG = (24, 24, 28)
LABEL = (235, 235, 235)


def load_font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--covers", default="output/covers")
    ap.add_argument("--concepts", default="")
    a = ap.parse_args()

    concepts = [c.strip() for c in a.concepts.split(",") if c.strip()]
    if not concepts:
        concepts = sorted(d for d in os.listdir(a.covers)
                          if os.path.isdir(os.path.join(a.covers, d)))

    fronts = []
    for c in concepts:
        p = os.path.join(a.covers, c, "cover_ebook.jpg")
        if os.path.exists(p):
            fronts.append((c, Image.open(p).convert("RGB")))
    if not fronts:
        print("aucune face trouvée")
        return

    # --- planche comparative : faces en ligne, hauteur 1100 px ---
    TH = 1100
    fnt = load_font(34)
    pad = 40
    label_h = 60
    thumbs = []
    for c, im in fronts:
        w = round(im.width * TH / im.height)
        thumbs.append((c, im.resize((w, TH), Image.LANCZOS)))
    total_w = sum(t[1].width for t in thumbs) + pad * (len(thumbs) + 1)
    sheet = Image.new("RGB", (total_w, TH + label_h + pad), BG)
    d = ImageDraw.Draw(sheet)
    x = pad
    for c, im in thumbs:
        sheet.paste(im, (x, pad))
        tw = d.textlength(c, font=fnt)
        d.text((x + (im.width - tw) / 2, pad + TH + 12), c, font=fnt, fill=LABEL)
        x += im.width + pad
    out1 = os.path.join(a.covers, "contact_sheet.png")
    sheet.save(out1)

    # --- bande vignettes 100 px (test miniature Amazon) ---
    TW = 100
    minis = []
    for c, im in fronts:
        h = round(im.height * TW / im.width)
        minis.append((c, im.resize((TW, h), Image.LANCZOS)))
    mh = max(m[1].height for m in minis)
    gap = 16
    strip = Image.new("RGB", (TW * len(minis) + gap * (len(minis) + 1), mh + 2 * gap), (200, 200, 200))
    x = gap
    for c, im in minis:
        strip.paste(im, (x, gap))
        x += TW + gap
    out2 = os.path.join(a.covers, "thumbnails_100px.png")
    strip.save(out2)

    print("planche:", out1)
    print("vignettes 100px:", out2)


if __name__ == "__main__":
    main()
