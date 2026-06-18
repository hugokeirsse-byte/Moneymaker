#!/usr/bin/env python3
"""
make_collection.py — production des 100 designs « phrase + illustration domaine
public » (0 € de génération IA). Pour chaque entrée de data/typo_collection.json :
  - police demandée téléchargée depuis Google Fonts (OFL/Apache) ou substitut libre ;
  - illustration du domaine public récupérée en HAUTE RÉSOLUTION via l'API Wikimedia
    Commons (min 2000 px sur le grand côté, sinon design typographique seul —
    jamais d'image basse qualité) ;
  - composition affiche : illustration en haut, phrase dans sa police en bas.
Repli garanti : si pas d'image exploitable, design typo transparent (encre sombre
+ variante blanche).

Usage (racine du repo, runner avec Internet) :
    python scripts/make_collection.py --data data/typo_collection.json --out produits/typographies
    python scripts/make_collection.py --data ... --sheet /tmp/collection.png
"""
import argparse
import io
import json
import os
import re
import sys
import urllib.parse
import urllib.request

from PIL import Image, ImageDraw, ImageFont

FONT_DIR = "assets/fonts"
GF = "https://raw.githubusercontent.com/google/fonts/main/"
UA = "Moneymaker/1.0 (POD public-domain art; hugo.keirsse@gmail.com)"
API = "https://commons.wikimedia.org/w/api.php"
PAPER = (250, 247, 237)
INK = (32, 28, 24)
INK_LIGHT = (247, 247, 245)
ACCENT = (150, 42, 38)
MIN_IMG = 2000  # px grand côté : en-dessous on n'utilise pas l'image

# police demandée -> chemin GF (ou substitut libre équivalent)
FONT_MAP = {
    "Playfair Display": "ofl/playfairdisplay/PlayfairDisplay[wght].ttf",
    "Playfair Display Italic": "ofl/playfairdisplay/PlayfairDisplay-Italic[wght].ttf",
    "Cormorant Garamond": "ofl/cormorantgaramond/CormorantGaramond-Bold.ttf",
    "Lora": "ofl/lora/Lora[wght].ttf",
    "EB Garamond": "ofl/ebgaramond/EBGaramond[wght].ttf",
    "Cinzel": "ofl/cinzel/Cinzel[wght].ttf",
    "Cinzel Decorative": "ofl/cinzeldecorative/CinzelDecorative-Bold.ttf",
    "Oswald": "ofl/oswald/Oswald[wght].ttf",
    "Bodoni Moda": "ofl/bodonimoda/BodoniModa[opsz,wght].ttf",
    "Quicksand": "ofl/quicksand/Quicksand[wght].ttf",
    "DM Serif Display": "ofl/dmserifdisplay/DMSerifDisplay-Regular.ttf",
    "Archivo Black": "ofl/archivoblack/ArchivoBlack-Regular.ttf",
    "Uncial Antiqua": "ofl/uncialantiqua/UncialAntiqua-Regular.ttf",
    "Pacifico": "ofl/pacifico/Pacifico-Regular.ttf",
    "Syne": "ofl/syne/Syne[wght].ttf",
    "Tinos": "apache/tinos/Tinos-Italic.ttf",
    "Chelsea Market": "ofl/chelseamarket/ChelseaMarket-Regular.ttf",
    "Comic Neue": "ofl/comicneue/ComicNeue-Bold.ttf",
    "Gothic A1": "ofl/gothica1/GothicA1-Bold.ttf",
    "Bungee": "ofl/bungee/Bungee-Regular.ttf",
    "Courier Prime": "ofl/courierprime/CourierPrime-Bold.ttf",
    "Montserrat": "ofl/montserrat/Montserrat[wght].ttf",
    "Share Tech Mono": "ofl/sharetechmono/ShareTechMono-Regular.ttf",
    "Space Grotesk": "ofl/spacegrotesk/SpaceGrotesk[wght].ttf",
    "BioRhyme": "ofl/biorhyme/BioRhyme[wdth,wght].ttf",
    "Inter": "ofl/inter/Inter[opsz,wght].ttf",
    "Rubik Mono One": "ofl/rubikmonoone/RubikMonoOne-Regular.ttf",
    "Libre Baskerville": "ofl/librebaskerville/LibreBaskerville-Regular.ttf",
    "Bebas Neue": "ofl/bebasneue/BebasNeue-Regular.ttf",
    "Anonymous Pro": "ofl/anonymouspro/AnonymousPro-Bold.ttf",
    "VT323": "ofl/vt323/VT323-Regular.ttf",
    "Cousine": "apache/cousine/Cousine-Bold.ttf",
    "League Spartan": "ofl/leaguespartan/LeagueSpartan[wght].ttf",
    "Prata": "ofl/prata/Prata-Regular.ttf",
    "Inconsolata": "ofl/inconsolata/Inconsolata[wdth,wght].ttf",
    "UnifrakturMaguntia": "ofl/unifrakturmaguntia/UnifrakturMaguntia-Book.ttf",
    "Anton": "ofl/anton/Anton-Regular.ttf",
    "Chonburi": "ofl/chonburi/Chonburi-Regular.ttf",
    "Krona One": "ofl/kronaone/KronaOne-Regular.ttf",
    "Staatliches": "ofl/staatliches/Staatliches-Regular.ttf",
    "Merriweather": "ofl/merriweather/Merriweather[opsz,wdth,wght].ttf",
    "Barlow Condensed": "ofl/barlowcondensed/BarlowCondensed-Bold.ttf",
    "Alice": "ofl/alice/Alice-Regular.ttf",
    "Tenor Sans": "ofl/tenorsans/TenorSans-Regular.ttf",
    "Newsreader": "ofl/newsreader/Newsreader[opsz,wght].ttf",
    "JetBrains Mono": "ofl/jetbrainsmono/JetBrainsMono[wght].ttf",
    "Jost": "ofl/jost/Jost[wght].ttf",
    "Abhaya Libre": "ofl/abhayalibre/AbhayaLibre-Bold.ttf",
    "PT Serif": "apache/ptserif/PT_Serif-Web-Bold.ttf",
    "Kanit": "ofl/kanit/Kanit-Bold.ttf",
    "Arvo": "apache/arvo/Arvo-Bold.ttf",
    "Fredoka": "ofl/fredoka/Fredoka[wdth,wght].ttf",
    "Cardo": "ofl/cardo/Cardo-Regular.ttf",
    "Saira Stencil One": "ofl/sairastencilone/SairaStencilOne-Regular.ttf",
    "Shrikhand": "ofl/shrikhand/Shrikhand-Regular.ttf",
    "Comfortaa": "ofl/comfortaa/Comfortaa[wght].ttf",
    "Zilla Slab": "ofl/zillaslab/ZillaSlab-Bold.ttf",
    "Goudy Bookletter 1911": "ofl/goudybookletter1911/GoudyBookletter1911-Regular.ttf",
    "Bitter": "ofl/bitter/Bitter[wght].ttf",
    "Overpass": "ofl/overpass/Overpass[wght].ttf",
    "Amatic SC": "ofl/amaticsc/AmaticSC-Bold.ttf",
    "Cabin Sketch": "ofl/cabinsketch/CabinSketch-Bold.ttf",
    "Rubik": "ofl/rubik/Rubik[wght].ttf",
    "Volkhov": "ofl/volkhov/Volkhov-Bold.ttf",
    "Great Vibes": "ofl/greatvibes/GreatVibes-Regular.ttf",
    "Monsieur La Doulaise": "ofl/monsieurladoulaise/MonsieurLaDoulaise-Regular.ttf",
    "Ultra": "ofl/ultra/Ultra-Regular.ttf",
    "Russo One": "ofl/russoone/RussoOne-Regular.ttf",
    "Hammersmith One": "ofl/hammersmithone/HammersmithOne-Regular.ttf",
    "Alfa Slab One": "ofl/alfaslabone/AlfaSlabOne-Regular.ttf",
    "Karla": "ofl/karla/Karla[wght].ttf",
    "Quattrocento": "ofl/quattrocento/Quattrocento-Bold.ttf",
    "Bellota Text": "ofl/bellotatext/BellotaText-Bold.ttf",
    "Cooper Black": "ofl/lilitaone/LilitaOne-Regular.ttf",  # substitut libre
    "DotGothic16": "ofl/dotgothic16/DotGothic16-Regular.ttf",
}
# substitut générique si une police manque (par familles)
FALLBACK = "ofl/archivoblack/ArchivoBlack-Regular.ttf"
_cache = {}


def ensure_font(name):
    """Télécharge (si besoin) la police demandée ou un substitut, renvoie le chemin."""
    if name in _cache:
        return _cache[name]
    os.makedirs(FONT_DIR, exist_ok=True)
    rel = FONT_MAP.get(name, FALLBACK)
    local = os.path.join(FONT_DIR, re.sub(r"[^A-Za-z0-9.]+", "_", name) + ".ttf")
    if not os.path.exists(local):
        for cand in (rel, FALLBACK):
            try:
                url = GF + urllib.parse.quote(cand)
                req = urllib.request.Request(url, headers={"User-Agent": UA})
                data = urllib.request.urlopen(req, timeout=40).read()
                open(local, "wb").write(data)
                break
            except Exception as e:  # noqa: BLE001
                print(f"[font] {name} <- {cand}: {e}", file=sys.stderr)
    _cache[name] = local if os.path.exists(local) else None
    return _cache[name]


def load(name, size):
    p = ensure_font(name)
    if not p:
        p = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    f = ImageFont.truetype(p, size)
    try:  # police variable : viser un gras lisible
        f.set_variation_by_axes([700])
    except Exception:  # noqa: BLE001
        pass
    return f


def tw(font, s):
    b = font.getbbox(s)
    return b[2] - b[0], b[3] - b[1], b[1]


def wrap(text, font, max_w):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if tw(font, t)[0] <= max_w or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def fit(name, text, max_w, max_lines=4, hi=520, lo=44):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load(name, mid)
        lines = wrap(text, f, max_w)
        if len(lines) <= max_lines and all(tw(f, l)[0] <= max_w for l in lines):
            lo = mid
        else:
            hi = mid - 1
    return lo


# --- récupération image PD haute résolution -----------------------------------
def _api(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return json.load(urllib.request.urlopen(req, timeout=40))


def resolve_hi(search, want=3800):
    res = _api({"action": "query", "format": "json", "list": "search",
                "srsearch": search, "srnamespace": 6, "srlimit": 6})
    for h in res.get("query", {}).get("search", []):
        title = h["title"]
        if not title.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff")):
            continue
        info = _api({"action": "query", "format": "json", "titles": title,
                     "prop": "imageinfo", "iiprop": "url|size",
                     "iiurlwidth": want})
        ii = next(iter(info["query"]["pages"].values()))["imageinfo"][0]
        full_w = ii.get("width", 0)
        if full_w < MIN_IMG:
            continue  # source trop petite -> on refuse (qualité supérieure exigée)
        return ii.get("thumburl") or ii["url"], title
    return None, None


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=120).read())).convert("RGB")


# --- compositions --------------------------------------------------------------
def poster(item, plate, W=4500, H=5400):
    card = Image.new("RGB", (W, H), PAPER)
    d = ImageDraw.Draw(card)
    p = plate.copy()
    p.thumbnail((int(W * 0.84), int(H * 0.55)), Image.LANCZOS)
    card.paste(p, ((W - p.width) // 2, int(H * 0.06)))
    y = int(H * 0.06) + p.height + int(H * 0.03)
    d.line([(W * 0.22, y), (W * 0.78, y)], fill=ACCENT, width=6)
    y += int(H * 0.03)
    maxw = int(W * 0.86)
    size = fit(item["font"], item["text"], maxw, max_lines=4)
    f = load(item["font"], size)
    for ln in wrap(item["text"], f, maxw):
        w, h, off = tw(f, ln)
        d.text(((W - w) // 2, y - off), ln, font=f, fill=INK)
        y += h + int(size * 0.16)
    return card


def typo(item, ink, side=4500):
    margin = int(side * 0.09)
    maxw = side - 2 * margin
    size = fit(item["font"], item["text"], maxw, max_lines=5)
    f = load(item["font"], size)
    lines = wrap(item["text"], f, maxw)
    gap = int(size * 0.18)
    dims = [(l, *tw(f, l)) for l in lines]
    th = sum(d[2] for d in dims) + gap * (len(dims) - 1)
    img = Image.new("RGBA", (side, th + 2 * margin), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    y = margin
    for (l, w, h, off) in dims:
        dr.text(((side - w) // 2, y - off), l, font=f, fill=ink)
        y += h + gap
    img = img.crop(img.getbbox())
    pad = int(side * 0.06)
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(img, (pad, pad))
    if max(out.size) != side and max(out.size) > 0:
        r = side / max(out.size)
        out = out.resize((round(out.width * r), round(out.height * r)), Image.LANCZOS)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/typo_collection.json")
    ap.add_argument("--out", default="")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    items = json.load(open(args.data, encoding="utf-8"))["items"]
    if args.limit:
        items = items[:args.limit]

    made = []
    n_img = n_typo = 0
    for it in items:
        plate = None
        if it.get("commons"):
            try:
                url, title = resolve_hi(it["commons"])
                if url:
                    plate = fetch(url)
                    print(f"{it['id']}: image {plate.size} <- {title}")
            except Exception as e:  # noqa: BLE001
                print(f"  {it['id']} image KO: {str(e)[:120]}", file=sys.stderr)
        sub = os.path.join(args.out, it["part"]) if args.out else None
        if sub:
            os.makedirs(sub, exist_ok=True)
        if plate is not None:
            card = poster(it, plate)
            made.append((it["id"], card.convert("RGBA")))
            n_img += 1
            if sub:
                card.save(os.path.join(sub, f"{it['id']}__affiche.png"), dpi=(300, 300))
        else:
            for var, ink in (("dark", INK), ("light", INK_LIGHT)):
                t = typo(it, ink)
                if sub:
                    t.save(os.path.join(sub, f"{it['id']}__{var}.png"), dpi=(300, 300))
                if var == "dark":
                    made.append((it["id"], t))
            n_typo += 1

    if args.sheet and made:
        cols = 5
        rows = (len(made) + cols - 1) // cols
        cell = 320
        sheet = Image.new("RGB", (cols * cell, rows * cell), (235, 234, 230))
        for i, (sid, im) in enumerate(made):
            t = im.convert("RGBA"); t.thumbnail((cell - 16, cell - 16))
            bg = Image.new("RGB", t.size, (245, 245, 245)); bg.paste(t.convert("RGB"), mask=t.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 8 + (cell - 16 - bg.width) // 2, r * cell + 8))
        sheet.save(args.sheet, quality=88)
        print("planche:", args.sheet)
    print(f"OK : {n_img} affiches (image PD HD) + {n_typo} typo seules = {len(items)}")


if __name__ == "__main__":
    sys.exit(main())
