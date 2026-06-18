#!/usr/bin/env python3
"""
make_collection.py — 100 designs à phrases, ÉCRITURES STYLISÉES SUR FOND TRANSPARENT.

Trois variantes par design, fond 100 % transparent :
  - __outline : intérieur blanc, contour noir (s'adapte à toute couleur de support) ;
  - __rainbow : lettres en dégradé arc-en-ciel avec contour noir ;
  - __black   : aplat noir (supports clairs).

Mots « intraduisibles » (p1) et « faux intraduisibles » (p4) : mise en page
DICTIONNAIRE — le mot en grand, l'ORIGINE (langue · nature) en petites capitales,
un filet, puis la DÉFINITION en anglais (serif italique).

Option --posters : ajoute une affiche papier avec illustration du domaine public HD.

Usage :
    python scripts/make_collection.py --data data/typo_collection.json --out produits/typographies
"""
import argparse
import colorsys
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
BLACK = (17, 17, 19, 255)
WHITE = (250, 250, 250, 255)
MIN_IMG = 2000

FONT_MAP = {
    "Playfair Display": "ofl/playfairdisplay/PlayfairDisplay[wght].ttf",
    "Cormorant Garamond": "ofl/cormorantgaramond/CormorantGaramond-Bold.ttf",
    "Lora": "ofl/lora/Lora[wght].ttf",
    "EB Garamond": "ofl/ebgaramond/EBGaramond[wght].ttf",
    "EB Garamond Italic": "ofl/ebgaramond/EBGaramond-Italic[wght].ttf",
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
    "Cooper Black": "ofl/lilitaone/LilitaOne-Regular.ttf",
    "DotGothic16": "ofl/dotgothic16/DotGothic16-Regular.ttf",
}
FALLBACK = "ofl/archivoblack/ArchivoBlack-Regular.ttf"

# definition (EN) + origine (langue · nature)
DEFS = {
    "tsundoku": ("Japanese · noun", "the art of buying books and letting them pile up, gloriously unread."),
    "sobremesa": ("Spanish · noun", "the lazy, lingering conversation long after the meal is over."),
    "iktsuarpok": ("Inuit · noun", "the restless urge to keep checking if someone is coming."),
    "waldeinsamkeit": ("German · noun", "the serene, solitary feeling of being alone in the woods."),
    "meraki": ("Greek · verb", "to do something with soul, creativity and a little bit of love."),
    "utepils": ("Norwegian · noun", "a cold beer savoured outside on the first warm day of the year."),
    "d_paysement": ("French · noun", "the pleasant disorientation of being far from home."),
    "gezellig": ("Dutch · adjective", "a cozy, warm togetherness that simply feels like home."),
    "kummerspeck": ("German · noun", "literally 'grief bacon' — the weight gained from comfort eating."),
    "jayus": ("Indonesian · noun", "a joke so bad, told so badly, that you can't help but laugh."),
    "doom_strolling": ("modern slang · verb", "to walk slowly while rehearsing every worst-case scenario."),
    "pre_tired": ("modern slang · adjective", "already exhausted by a day that hasn't even started yet."),
    "chronofatigue": ("mock-Latin · noun", "the tiredness that comes simply from checking the time."),
    "socio_phobia": ("mock-clinical · noun", "the quiet dread of the plans you already agreed to."),
    "micro_panic": ("internet English · noun", "a three-second internal scream, invisible from the outside."),
    "retro_regret": ("internet English · noun", "the on-demand cringe of a memory from years ago."),
    "optimistic_nihilism": ("ironic philosophy · noun", "nothing matters, so you might as well enjoy the snacks."),
    "decaf_energy": ("modern slang · noun", "trying very hard while feeling absolutely nothing."),
    "intro_venting": ("modern slang · verb", "to complain loudly and at length inside your own head."),
    "aura_loss": ("internet English · noun", "the sudden drop in coolness right after one clumsy move."),
    "pr_fatigu": ("franglais · adjective", "already exhausted at the mere thought of the day ahead."),
    "cringe_back": ("internet English · noun", "a flashback so awkward it makes you physically wince."),
    "micro_sieste_mentale": ("franglais · noun", "to mentally check out for three seconds, eyes wide open."),
    "nihilisme_joyeux": ("mock-philosophy · noun", "nothing matters, so you might as well laugh about it."),
    "r_lerie_pr_ventive": ("franglais · noun", "the art of complaining about something before it even happens."),
}
_cache = {}


def ensure_font(name):
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
                open(local, "wb").write(urllib.request.urlopen(req, timeout=40).read())
                break
            except Exception as e:  # noqa: BLE001
                print(f"[font] {name} <- {cand}: {e}", file=sys.stderr)
    _cache[name] = local if os.path.exists(local) else None
    return _cache[name]


def load(name, size):
    p = ensure_font(name) or "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    f = ImageFont.truetype(p, size)
    try:
        f.set_variation_by_axes([700])
    except Exception:  # noqa: BLE001
        pass
    return f


def tw(font, s):
    b = font.getbbox(s)
    return b[2] - b[0], b[3] - b[1], b[1]


def wrap(text, font, max_w):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if tw(font, t)[0] <= max_w or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def fit(name, text, max_w, max_lines=4, hi=820, lo=40):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load(name, mid)
        lines = wrap(text, f, max_w)
        if len(lines) <= max_lines and all(tw(f, l)[0] <= max_w for l in lines):
            lo = mid
        else:
            hi = mid - 1
    return lo


def rainbow(w, h):
    grad = Image.new("RGBA", (max(w, 1), max(h, 1)))
    px = grad.load()
    for x in range(grad.width):
        hue = 0.92 - 0.92 * (x / max(grad.width - 1, 1))  # rouge -> violet
        r, g, b = colorsys.hsv_to_rgb(hue, 0.82, 0.95)
        col = (int(r * 255), int(g * 255), int(b * 255), 255)
        for y in range(grad.height):
            px[x, y] = col
    return grad


def build_rows(item):
    side = 4500
    margin = int(side * 0.09)
    maxw = side - 2 * margin
    rows = []
    if item["id"] in DEFS:
        origin, definition = DEFS[item["id"]]
        ws = fit(item["font"], item["text"], maxw, max_lines=2, hi=820)
        for l in wrap(item["text"], load(item["font"], ws), maxw):
            rows.append((l, item["font"], ws, "word"))
        os_ = max(int(ws * 0.12), 58)
        rows.append((" ".join(origin.upper()), "Montserrat", os_, "origin"))
        rows.append(("__rule__", None, max(int(ws * 0.02), 6), "rule"))
        ds = max(int(ws * 0.17), 72)
        for l in wrap(definition, load("EB Garamond Italic", ds), int(maxw * 0.92)):
            rows.append((l, "EB Garamond Italic", ds, "def"))
    else:
        s = fit(item["font"], item["text"], maxw, max_lines=5)
        for l in wrap(item["text"], load(item["font"], s), maxw):
            rows.append((l, item["font"], s, "phrase"))
    return rows, maxw, margin, side


def render(item, variant):
    rows, maxw, margin, side = build_rows(item)
    laid = []
    y = margin
    for (text, fname, size, kind) in rows:
        if kind == "rule":
            gap = int(size * 6)
            laid.append((None, None, kind, y + gap, size, 0, 0))
            y += gap * 2 + size
            continue
        f = load(fname, size)
        w, h, off = tw(f, text)
        gap = int(size * (0.30 if kind == "def" else 0.16 if kind in ("word", "phrase") else 0.4))
        pre = int(size * (0.5 if kind == "origin" else 0.0))
        y += pre
        laid.append((text, f, kind, y, size, w, off))
        y += h + gap
    H = y + margin

    outline = Image.new("RGBA", (side, H), (0, 0, 0, 0))
    mask = Image.new("RGBA", (side, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(outline)
    md = ImageDraw.Draw(mask)

    for (text, f, kind, yy, size, w, off) in laid:
        sw = max(2, round(size * (0.06 if kind in ("word", "phrase") else 0.05)))
        if kind == "rule":
            x0, x1 = side * 0.36, side * 0.64
            od.line([(x0, yy), (x1, yy)], fill=BLACK, width=size + 2 * sw)
            md.line([(x0, yy), (x1, yy)], fill=WHITE, width=size)
            continue
        x = (side - w) // 2
        if variant == "black":
            od.text((x, yy - off), text, font=f, fill=BLACK)
        else:
            od.text((x, yy - off), text, font=f, fill=BLACK, stroke_width=sw, stroke_fill=BLACK)
            md.text((x, yy - off), text, font=f, fill=WHITE)

    if variant == "black":
        result = outline
    else:
        if variant == "rainbow":
            fill_img = rainbow(side, H)
        else:
            fill_img = Image.new("RGBA", (side, H), WHITE)
        fill_img.putalpha(mask.split()[-1])
        result = Image.alpha_composite(outline, fill_img)

    bbox = result.getbbox()
    if not bbox:
        return result
    result = result.crop(bbox)
    pad = int(side * 0.06)
    out = Image.new("RGBA", (result.width + 2 * pad, result.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(result, (pad, pad))
    if max(out.size) and max(out.size) != side:
        r = side / max(out.size)
        out = out.resize((round(out.width * r), round(out.height * r)), Image.LANCZOS)
    return out


def _api(params):
    url = API + "?" + urllib.parse.urlencode(params)
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40))


def resolve_hi(search, want=3800):
    res = _api({"action": "query", "format": "json", "list": "search",
                "srsearch": search, "srnamespace": 6, "srlimit": 6})
    for h in res.get("query", {}).get("search", []):
        title = h["title"]
        if not title.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".tiff")):
            continue
        info = _api({"action": "query", "format": "json", "titles": title,
                     "prop": "imageinfo", "iiprop": "url|size", "iiurlwidth": want})
        ii = next(iter(info["query"]["pages"].values()))["imageinfo"][0]
        if ii.get("width", 0) < MIN_IMG:
            continue
        return ii.get("thumburl") or ii["url"], title
    return None, None


def fetch(url):
    return Image.open(io.BytesIO(urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": UA}), timeout=120).read())).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/typo_collection.json")
    ap.add_argument("--out", default="")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--variants", default="outline,rainbow,black")
    ap.add_argument("--posters", action="store_true")
    args = ap.parse_args()
    items = json.load(open(args.data, encoding="utf-8"))["items"]
    if args.limit:
        items = items[:args.limit]
    variants = args.variants.split(",")

    made = []
    for it in items:
        sub = os.path.join(args.out, it["part"]) if args.out else None
        if sub:
            os.makedirs(sub, exist_ok=True)
        for v in variants:
            img = render(it, v)
            if sub:
                img.save(os.path.join(sub, f"{it['id']}__{v}.png"), dpi=(300, 300))
            if v == variants[0]:
                made.append((it["id"], img))
        if args.posters and it.get("commons"):
            try:
                url, title = resolve_hi(it["commons"])
                if url:
                    plate = fetch(url)
                    card = Image.new("RGB", (4500, 5400), PAPER)
                    p = plate.copy(); p.thumbnail((3780, 2700), Image.LANCZOS)
                    card.paste(p, ((4500 - p.width) // 2, 380))
                    over = render(it, "black"); over.thumbnail((3870, 1800))
                    card.paste(over, ((4500 - over.width) // 2, 420 + p.height + 200), over)
                    if sub:
                        card.save(os.path.join(sub, f"{it['id']}__affiche.png"), dpi=(300, 300))
            except Exception as e:  # noqa: BLE001
                print(f"  {it['id']} affiche KO: {str(e)[:120]}", file=sys.stderr)

    if args.sheet and made:
        cols = 5
        rows = (len(made) + cols - 1) // cols
        cell = 320
        sheet = Image.new("RGB", (cols * cell, rows * cell), (60, 60, 66))
        for i, (sid, im) in enumerate(made):
            t = im.convert("RGBA"); t.thumbnail((cell - 16, cell - 16))
            r, c = divmod(i, cols)
            sheet.paste(t, (c * cell + 8 + (cell - 16 - t.width) // 2,
                            r * cell + 8 + (cell - 16 - t.height) // 2), t)
        sheet.save(args.sheet, quality=88)
        print("planche:", args.sheet)
    print(f"OK : {len(items)} designs x {len(variants)} variantes (transparent, {len(DEFS)} dictionnaire)")


if __name__ == "__main__":
    sys.exit(main())
