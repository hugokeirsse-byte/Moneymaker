#!/usr/bin/env python3
"""
make_collection.py — production des 100 designs à phrases, ÉCRITURES DÉTOURÉES SUR
FOND TRANSPARENT (0 € de génération IA).

Par défaut : pour chaque entrée de data/typo_collection.json, on rend le texte dans
la police demandée (téléchargée depuis Google Fonts, ou substitut libre), sur fond
100 % transparent, en deux variantes : encre sombre (t-shirts clairs) et encre
blanche (t-shirts foncés).

Mots « intraduisibles » (p1) et « faux intraduisibles » (p4) : mise en page
DICTIONNAIRE — le mot en grand, un filet fin, puis la définition en dessous.

Option --posters : compose aussi une affiche papier avec une illustration du
domaine public en haute résolution (Wikimedia Commons, ≥2000 px) quand elle existe.

Usage (racine du repo) :
    python scripts/make_collection.py --data data/typo_collection.json --out produits/typographies
    python scripts/make_collection.py --data ... --sheet /tmp/sheet.png [--posters]
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
INK = (28, 26, 24)
INK_LIGHT = (247, 247, 245)
ACCENT = (150, 42, 38)
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

# définitions « dictionnaire » pour les mots intraduisibles (p1) et faux (p4)
DEFS = {
    "tsundoku": "(n.) the art of buying books and letting them pile up, gloriously unread.",
    "sobremesa": "(n.) the lazy, lingering conversation long after the meal is over.",
    "iktsuarpok": "(n.) the restless urge to keep checking if someone is coming.",
    "waldeinsamkeit": "(n.) the serene, solitary feeling of being alone in the woods.",
    "meraki": "(n.) to do something with soul, creativity and a little bit of love.",
    "utepils": "(n.) a cold beer savoured outside on the first warm day of the year.",
    "d_paysement": "(n.) le doux vertige de se sentir loin de chez soi.",
    "gezellig": "(adj.) a cozy, warm togetherness that simply feels like home.",
    "kummerspeck": "(n.) literally 'grief bacon' — the weight gained from comfort eating.",
    "jayus": "(n.) a joke so bad, told so badly, that you can't help but laugh.",
    "doom_strolling": "(v.) to walk slowly while mentally rehearsing every worst-case scenario.",
    "pre_tired": "(adj.) already exhausted by a day that hasn't even started yet.",
    "chronofatigue": "(n.) la fatigue ressentie rien qu'en regardant l'heure.",
    "socio_phobia": "(n.) the quiet dread of the plans you already agreed to.",
    "micro_panic": "(n.) a three-second internal scream, invisible from the outside.",
    "retro_regret": "(n.) the on-demand cringe of a memory from years ago.",
    "optimistic_nihilism": "(n.) nothing really matters, so you might as well enjoy the snacks.",
    "decaf_energy": "(n.) the vibe of trying very hard while feeling absolutely nothing.",
    "intro_venting": "(v.) to complain loudly and at length inside your own head.",
    "aura_loss": "(n.) the sudden drop in coolness right after one clumsy move.",
    "pr_fatigu": "(adj.) déjà épuisé à la seule idée de la journée qui commence.",
    "cringe_back": "(n.) a flashback so awkward it makes you physically wince.",
    "micro_sieste_mentale": "(n.) s'absenter trois secondes, les yeux grands ouverts.",
    "nihilisme_joyeux": "(n.) rien n'a de sens — autant en rire de bon coeur.",
    "r_lerie_pr_ventive": "(n.) l'art de raler contre un truc avant meme qu'il arrive.",
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


def fit(name, text, max_w, max_lines=4, hi=520, lo=40):
    while lo < hi:
        mid = (lo + hi + 1) // 2
        f = load(name, mid)
        lines = wrap(text, f, max_w)
        if len(lines) <= max_lines and all(tw(f, l)[0] <= max_w for l in lines):
            lo = mid
        else:
            hi = mid - 1
    return lo


def _finish(img, side):
    img = img.crop(img.getbbox())
    pad = int(side * 0.06)
    out = Image.new("RGBA", (img.width + 2 * pad, img.height + 2 * pad), (0, 0, 0, 0))
    out.alpha_composite(img, (pad, pad))
    if max(out.size) and max(out.size) != side:
        r = side / max(out.size)
        out = out.resize((round(out.width * r), round(out.height * r)), Image.LANCZOS)
    return out


def render_typo(item, ink, side=4500):
    """Texte centré sur fond transparent. Si une définition existe (intraduisibles),
    mise en page dictionnaire : mot en grand + filet + définition."""
    margin = int(side * 0.09)
    maxw = side - 2 * margin
    definition = DEFS.get(item["id"])

    if definition:
        # mot en très grand
        wsize = fit(item["font"], item["text"], maxw, max_lines=2, hi=900)
        wf = load(item["font"], wsize)
        wlines = wrap(item["text"], wf, maxw)
        # définition en serif italique, lisible
        dsize = max(int(wsize * 0.16), 70)
        dfont = load("EB Garamond Italic", dsize)
        dlines = wrap(definition, dfont, int(maxw * 0.92))
        gap = int(wsize * 0.10)
        dgap = int(dsize * 0.30)
        wdims = [(l, *tw(wf, l)) for l in wlines]
        ddims = [(l, *tw(dfont, l)) for l in dlines]
        rule_y_gap = int(wsize * 0.22)
        H = (sum(d[2] for d in wdims) + gap * (len(wdims) - 1)
             + rule_y_gap * 2 + sum(d[2] for d in ddims) + dgap * (len(ddims) - 1)
             + 2 * margin)
        img = Image.new("RGBA", (side, H), (0, 0, 0, 0))
        dr = ImageDraw.Draw(img)
        y = margin
        for (l, w, h, off) in wdims:
            dr.text(((side - w) // 2, y - off), l, font=wf, fill=ink)
            y += h + gap
        y += rule_y_gap
        dr.line([(side * 0.33, y), (side * 0.67, y)], fill=ink, width=max(3, side // 900))
        y += rule_y_gap
        for (l, w, h, off) in ddims:
            dr.text(((side - w) // 2, y - off), l, font=dfont, fill=ink)
            y += h + dgap
        return _finish(img, side)

    # phrase normale, transparente
    size = fit(item["font"], item["text"], maxw, max_lines=5)
    f = load(item["font"], size)
    gap = int(size * 0.18)
    dims = [(l, *tw(f, l)) for l in wrap(item["text"], f, maxw)]
    H = sum(d[2] for d in dims) + gap * (len(dims) - 1) + 2 * margin
    img = Image.new("RGBA", (side, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    y = margin
    for (l, w, h, off) in dims:
        dr.text(((side - w) // 2, y - off), l, font=f, fill=ink)
        y += h + gap
    return _finish(img, side)


# --- affiche optionnelle avec image PD (option --posters) ----------------------
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
                     "prop": "imageinfo", "iiprop": "url|size", "iiurlwidth": want})
        ii = next(iter(info["query"]["pages"].values()))["imageinfo"][0]
        if ii.get("width", 0) < MIN_IMG:
            continue
        return ii.get("thumburl") or ii["url"], title
    return None, None


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=120).read())).convert("RGB")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data/typo_collection.json")
    ap.add_argument("--out", default="")
    ap.add_argument("--sheet", default="")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--posters", action="store_true",
                    help="compose aussi une affiche papier avec image PD HD si dispo")
    args = ap.parse_args()
    items = json.load(open(args.data, encoding="utf-8"))["items"]
    if args.limit:
        items = items[:args.limit]

    made = []
    for it in items:
        sub = os.path.join(args.out, it["part"]) if args.out else None
        if sub:
            os.makedirs(sub, exist_ok=True)
        # écritures détourées, fond transparent : sombre + blanc
        for var, ink in (("dark", INK), ("light", INK_LIGHT)):
            img = render_typo(it, ink)
            if sub:
                img.save(os.path.join(sub, f"{it['id']}__{var}.png"), dpi=(300, 300))
            if var == "dark":
                made.append((it["id"], img))
        # affiche illustrée optionnelle
        if args.posters and it.get("commons"):
            try:
                url, title = resolve_hi(it["commons"])
                if url:
                    plate = fetch(url)
                    card = Image.new("RGB", (4500, 5400), PAPER)
                    p = plate.copy(); p.thumbnail((int(4500 * 0.84), int(5400 * 0.5)), Image.LANCZOS)
                    card.paste(p, ((4500 - p.width) // 2, int(5400 * 0.07)))
                    y = int(5400 * 0.07) + p.height + int(5400 * 0.04)
                    over = render_typo(it, INK, side=int(4500 * 0.86)).convert("RGBA")
                    over.thumbnail((int(4500 * 0.86), int(5400 * 0.34)))
                    card.paste(over, ((4500 - over.width) // 2, y), over)
                    if sub:
                        card.save(os.path.join(sub, f"{it['id']}__affiche.png"), dpi=(300, 300))
                    print(f"{it['id']}: affiche {plate.size} <- {title}")
            except Exception as e:  # noqa: BLE001
                print(f"  {it['id']} affiche KO: {str(e)[:120]}", file=sys.stderr)

    if args.sheet and made:
        cols = 5
        rows = (len(made) + cols - 1) // cols
        cell = 320
        sheet = Image.new("RGB", (cols * cell, rows * cell), (236, 235, 231))
        for i, (sid, im) in enumerate(made):
            t = im.convert("RGBA"); t.thumbnail((cell - 16, cell - 16))
            bg = Image.new("RGB", t.size, (246, 246, 246)); bg.paste(t.convert("RGB"), mask=t.split()[-1])
            r, c = divmod(i, cols)
            sheet.paste(bg, (c * cell + 8 + (cell - 16 - bg.width) // 2,
                             r * cell + 8 + (cell - 16 - bg.height) // 2))
        sheet.save(args.sheet, quality=88)
        print("planche:", args.sheet)
    print(f"OK : {len(items)} designs (écritures transparentes, {len(DEFS)} avec définition)")


if __name__ == "__main__":
    sys.exit(main())
