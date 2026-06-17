#!/usr/bin/env python3
"""
pd_illustrations.py — affiches POD à partir d'illustrations du DOMAINE PUBLIC,
réhabilitées avec une phrase décalée. Zéro génération d'image payante.

Source : planches botaniques de « Köhler's Medizinal-Pflanzen » (1887, domaine
public), récupérées via l'API Wikimedia Commons (le runner CI a Internet).
Chaque planche est résolue par recherche (binôme latin + « Köhler »), téléchargée
en grande taille, puis composée en affiche d'apothicaire : planche + nom commun
(Playfair), phrase humoristique (condensé Anton), nom latin en italique et
crédit de source.

Aucune marque déposée. Domaine public vérifié (œuvre publiée en 1887).

Usage (depuis la racine du repo) :
    python scripts/pd_illustrations.py --out produits/illustrations_vintage
    python scripts/pd_illustrations.py --sheet /tmp/pd.png   # planche-contact
"""
import argparse
import io
import json
import os
import sys
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from text_designs import load, measure  # noqa: E402

UA = "Moneymaker/1.0 (POD public-domain art; contact hugo.keirsse@gmail.com)"
API = "https://commons.wikimedia.org/w/api.php"
PAPER = (250, 247, 237)
INK = (38, 32, 26)
ACCENT = (150, 42, 38)

# id, terme de recherche Commons, nom affiché, phrase (lignes), nom latin, cat
PLATES = [
    ("foxglove",   "Digitalis purpurea Köhler Medizinal", "FOXGLOVE",
     ["PRETTY.", "DEADLY.", "DRAMATIC."], "Digitalis purpurea"),
    ("coffee",     "Coffea arabica Köhler Medizinal", "COFFEA",
     ["DO NOT APPROACH", "BEFORE COFFEE"], "Coffea arabica"),
    ("belladonna", "Atropa belladonna Köhler Medizinal", "BELLADONNA",
     ["RESTING", "WITCH FACE"], "Atropa belladonna"),
    ("chamomile",  "Matricaria chamomilla Köhler Medizinal", "CHAMOMILE",
     ["EMOTIONAL", "SUPPORT TEA"], "Matricaria chamomilla"),
    ("peppermint", "Mentha piperita Köhler Medizinal", "PEPPERMINT",
     ["FRESH.", "PETTY.", "UNBOTHERED."], "Mentha piperita"),
    ("valerian",   "Valeriana officinalis Köhler Medizinal", "VALERIAN",
     ["PROFESSIONAL", "NAP COACH"], "Valeriana officinalis"),
]


def _get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def resolve_plate(search, want=2400):
    """Retourne (thumb_url, license, page_title) de la 1re planche trouvée."""
    res = _get({"action": "query", "format": "json", "list": "search",
                "srsearch": search, "srnamespace": 6, "srlimit": 5})
    hits = res.get("query", {}).get("search", [])
    if not hits:
        raise RuntimeError(f"aucune planche pour « {search} »")
    for h in hits:
        title = h["title"]
        if not title.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff")):
            continue
        info = _get({"action": "query", "format": "json", "titles": title,
                     "prop": "imageinfo", "iiprop": "url|extmetadata",
                     "iiurlwidth": want})
        pages = info["query"]["pages"]
        ii = next(iter(pages.values()))["imageinfo"][0]
        lic = ii.get("extmetadata", {}).get("LicenseShortName", {}).get("value", "?")
        return ii.get("thumburl") or ii["url"], lic, title
    raise RuntimeError(f"pas de fichier image exploitable pour « {search} »")


def download_img(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as r:
        return Image.open(io.BytesIO(r.read())).convert("RGB")


def compose(plate_img, name, caption, latin, credit, W=4500, H=5400):
    card = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(card)

    # planche centrée dans la moitié haute
    box_w, box_h = int(W * 0.82), int(H * 0.52)
    p = plate_img.copy()
    p.thumbnail((box_w, box_h), Image.LANCZOS)
    px = (W - p.width) // 2
    py = int(H * 0.07)
    card.paste(p, (px, py))

    y = py + p.height + int(H * 0.035)
    # filet décoratif
    d.line([(W * 0.20, y), (W * 0.80, y)], fill=ACCENT, width=6)
    y += int(H * 0.025)

    # nom commun (Playfair), ajusté à la largeur
    maxw = int(W * 0.84)
    size = 360
    while size > 80 and measure(load("playfair", size), name)[0] > maxw:
        size -= 8
    f = load("playfair", size)
    w, h, off = measure(f, name)
    d.text(((W - w) // 2, y - off), name, font=f, fill=INK)
    y += h + int(H * 0.02)

    # phrase humoristique (Anton condensé)
    for ln in caption:
        cs = 300
        while cs > 60 and measure(load("anton", cs), ln)[0] > maxw:
            cs -= 6
        cf = load("anton", cs)
        w, h, off = measure(cf, ln)
        d.text(((W - w) // 2, y - off), ln, font=cf, fill=ACCENT)
        y += h + int(cs * 0.12)

    # nom latin (italique) + crédit
    lf = load("mont_light", 86)
    w, h, off = measure(lf, latin)
    d.text(((W - w) // 2, int(H * 0.92) - off), latin, font=lf, fill=INK)
    cf = load("mont_light", 52)
    w, h, off = measure(cf, credit)
    d.text(((W - w) // 2, int(H * 0.95) - off), credit, font=cf, fill=(120, 110, 96))
    return card


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="")
    ap.add_argument("--sheet", default="")
    args = ap.parse_args()

    credit = "Köhler's Medizinal-Pflanzen, 1887 — public domain"
    made = []
    for pid, search, name, caption, latin in PLATES:
        try:
            url, lic, title = resolve_plate(search)
            print(f"{pid}: {title}  [{lic}]")
            plate = download_img(url)
        except Exception as e:  # noqa: BLE001
            print(f"  ⏭️ {pid}: {e}")
            continue
        card = compose(plate, name, caption, latin, credit)
        made.append((pid, card))
        if args.out:
            d = os.path.join(args.out, "botanique")
            os.makedirs(d, exist_ok=True)
            card.save(os.path.join(d, f"{pid}__vintage_botanique.png"), dpi=(300, 300))

    if args.sheet and made:
        cols = 3
        rows = (len(made) + cols - 1) // cols
        cell = 560
        sheet = Image.new("RGB", (cols * cell, rows * cell), (228, 226, 220))
        for i, (pid, card) in enumerate(made):
            t = card.copy(); t.thumbnail((cell - 24, cell - 24))
            r, c = divmod(i, cols)
            sheet.paste(t, (c * cell + 12 + (cell - 24 - t.width) // 2, r * cell + 12))
        sheet.save(args.sheet, quality=90)
        print("planche:", args.sheet)
    print(f"{len(made)}/{len(PLATES)} affiches composées" + (f" -> {args.out}" if args.out else ""))


if __name__ == "__main__":
    main()
