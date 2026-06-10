#!/usr/bin/env python3
"""
build_publication_pack.py — pack de publication Redbubble complet.

Scanne output/rb_*/{expr}/*.png, croise avec les CDCs reports/redbubble/*.json,
et produit reports/listings/publication_pack.csv : 1 ligne par image avec
titre, description et tags anglais prêts à copier-coller, + indication
transparent/full-bleed selon le style.
"""
from __future__ import annotations
import csv, glob, json, os, re
from datetime import date
from pathlib import Path

# ── Styles : libellé humain + tags + fond détourable ────────────────────────
STYLE_META = {
    "embroidery_patch":    ("Embroidered Patch Style", ["embroidered patch", "iron on patch look", "badge"], True),
    "risograph":           ("Risograph Print", ["risograph", "riso print", "zine art"], False),
    "flat_vector":         ("Flat Vector Art", ["flat design", "vector art", "minimal graphic"], True),
    "ukiyo_e":             ("Ukiyo-e Japanese Print", ["ukiyo e", "japanese woodblock", "japan art"], False),
    "retro_neon_80s":      ("80s Retro Neon", ["synthwave", "retro 80s", "neon aesthetic"], False),
    "cut_paper_collage":   ("Paper Collage Art", ["paper collage", "papercraft", "handmade look"], False),
    "vintage_watercolor":  ("Vintage Watercolor", ["watercolor", "vintage illustration", "antique art"], False),
    "cartoon_network":     ("Cartoon Style", ["cartoon", "cute cartoon", "animated style"], True),
    "victorian_engraving": ("Victorian Engraving", ["engraving", "victorian", "vintage etching"], False),
    "memphis_design":      ("Memphis Design", ["memphis style", "80s design", "postmodern"], False),
    "ghibli_painted":      ("Painted Anime Style", ["anime style", "painted illustration", "storybook art"], False),
    "pixel_art":           ("Pixel Art", ["pixel art", "8 bit", "retro gaming"], False),
    "minimalist_line":     ("Minimalist Line Art", ["line art", "minimalist", "one line drawing"], True),
    "gothic_dark":         ("Gothic Art", ["gothic", "dark art", "spooky cute"], False),
    "psychedelic_60s":     ("60s Psychedelic Art", ["psychedelic", "groovy", "60s poster"], False),
    "kawaii_chibi":        ("Kawaii Chibi", ["kawaii", "chibi", "cute pastel"], True),
    "woodcut_linocut":     ("Linocut Print", ["linocut", "woodcut", "block print"], False),
    "tattoo_flash":        ("Tattoo Flash Art", ["tattoo flash", "old school tattoo", "sailor jerry style"], True),
    "art_nouveau":         ("Art Nouveau", ["art nouveau", "mucha style", "ornamental"], False),
    "swiss_constructivist":("Swiss Poster Design", ["swiss design", "bauhaus", "constructivist"], True),
    "pop_art":             ("Pop Art Comic", ["pop art", "comic style", "halftone"], False),
}

# ── Contexte par série (détecté via nom du dossier rb_*) ─────────────────────
SERIES_CONTEXT = [
    ("worldcup", "World Cup 2026", ["world cup 2026", "football", "soccer", "fan art", "supporter"]),
    ("fathers_day", "Father's Day", ["fathers day", "dad", "papa", "gift for dad", "funny dad", "best dad"]),
    ("zevents", "", []),       # événements multiples → contexte par expression
    ("events_flood", "", []),  # idem
    ("visual_puns", "", ["funny", "pun", "wordplay", "humor"]),
    ("professions", "", ["profession", "job humor", "work gift"]),
    ("hobbies", "", ["hobby", "passion gift"]),
    ("zodiac", "Zodiac", ["zodiac", "astrology", "star sign", "horoscope"]),
    ("petparents", "Pet Parent", ["pet lover", "pet parent", "animal lover"]),
    ("french", "", ["french expression", "humour francais", "france"]),
]

EVENT_CONTEXT = {
    "pride":      ("Pride", ["pride", "lgbtq", "rainbow", "love is love", "pride month"]),
    "juneteenth": ("Juneteenth", ["juneteenth", "freedom day", "black history", "emancipation"]),
    "midsommar":  ("Midsummer", ["midsummer", "midsommar", "swedish", "scandinavian", "solstice"]),
    "musicday":   ("Music Day", ["music", "musician gift", "fete de la musique", "music lover"]),
    "fete_musique": ("Music Day", ["music", "musician gift", "fete de la musique", "music lover"]),
    "dragonboat": ("Dragon Boat Festival", ["dragon boat", "dragon boat festival", "duanwu", "paddling"]),
    "fathersday": ("Father's Day", ["fathers day", "dad", "papa", "gift for dad", "funny dad"]),
    "fathers_day": ("Father's Day", ["fathers day", "dad", "papa", "gift for dad", "funny dad"]),
}

NUM_WORDS = {"ONE": "one", "TWO": "two", "THREE": "three", "FOUR": "four",
             "FIVE": "five", "SIX": "six"}


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")


def _scene_from_prompt(prompt: str) -> str:
    """Extrait la scène lisible du positive_prompt (avant le bloc style)."""
    scene = prompt.split(" Illustrated ")[0]
    for k, v in NUM_WORDS.items():
        scene = scene.replace(f"EXACTLY {k}", v)
    scene = re.sub(r"\s+", " ", scene).strip().rstrip(".")
    # Première lettre en majuscule
    return scene[:1].upper() + scene[1:] if scene else scene


def load_brief_index(reports_dir: str = "reports/redbubble") -> dict:
    """Index {(slug_prefix, style_id): brief_meta} depuis tous les CDCs."""
    index = {}
    for path in glob.glob(os.path.join(reports_dir, "cahiers_des_charges_*.json")):
        try:
            data = json.load(open(path))
        except Exception:
            continue
        for b in data.get("briefs", []):
            style = b.get("_style_id", "")
            name = b.get("name", "")
            prefix = _slug(name.split("—")[0]) if "—" in name else _slug(name)
            meta = {
                "label": b.get("_canva_text") or b.get("_idiom") or prefix,
                "scene": _scene_from_prompt(b.get("ai_generation", {}).get("positive_prompt", "")),
                "expression": b.get("_expression_id", prefix),
            }
            index[(prefix, style)] = meta
            index[(_slug(b.get("_expression_id", "")), style)] = meta
    return index


def series_context(folder: str, expr: str):
    """(context_label, context_tags) pour un dossier rb_* et une expression."""
    f = folder.lower()
    # événements : contexte par préfixe d'expression
    for key, (label, tags) in EVENT_CONTEXT.items():
        if expr.startswith(key):
            return label, tags
    for key, label, tags in SERIES_CONTEXT:
        if key in f:
            return label, tags
    return "", []


def build_title(label: str, context: str, style_label: str) -> str:
    label_t = label.title() if label.isupper() else label
    parts = [label_t]
    if context and context.lower() not in label_t.lower():
        parts.append(context)
    title = " — ".join(parts) + f" | {style_label}"
    return title[:100]


def build_tags(label: str, context_tags: list, style_tags: list) -> str:
    tags, seen = [], set()
    words = [w for w in re.split(r"[^\w']+", label.lower()) if len(w) > 2]
    candidates = ([label.lower()] + words + context_tags + style_tags +
                  ["sticker", "gift idea", "no text", "illustration"])
    for t in candidates:
        t = t.strip().lower()[:50]
        if t and t not in seen and len(t) > 2:
            seen.add(t)
            tags.append(t)
        if len(tags) >= 15:
            break
    return ", ".join(tags)


def build_description(scene: str, style_label: str, context: str) -> str:
    parts = []
    if scene:
        parts.append(f"{style_label} illustration: {scene.lower()[:400]}.")
    else:
        parts.append(f"Original {style_label} illustration.")
    if context:
        parts.append(f"Perfect for {context} — a fun, instantly readable design with no text.")
    else:
        parts.append("A bold, instantly readable design with no text.")
    parts.append("Looks great on stickers, t-shirts, mugs, phone cases and posters.")
    return " ".join(parts)[:1000]


def main():
    idx = load_brief_index()
    rows = []
    for png in sorted(glob.glob("output/rb_*/*/*.png")):
        if "thumbnails" in png or png.endswith("_transparent.png"):
            continue
        folder = png.split(os.sep)[1]          # rb_xxx
        base = os.path.basename(png)
        parts = base.split("___")
        if len(parts) < 2:
            continue
        prefix, style = parts[0], parts[1]
        style_label, style_tags, can_transparent = STYLE_META.get(
            style, (style.replace("_", " ").title(), [], False))
        meta = idx.get((prefix, style)) or idx.get((_slug(prefix), style)) or {}
        label = meta.get("label", prefix.replace("_", " ").upper())
        scene = meta.get("scene", "")
        context, ctx_tags = series_context(folder, prefix)
        transparent_file = png.replace(".png", "_transparent.png")
        rows.append({
            "series": folder,
            "image": png,
            "upload_file": transparent_file if (can_transparent and os.path.exists(transparent_file)) else png,
            "background": "transparent" if can_transparent else "full-bleed (keep square)",
            "expression": prefix,
            "style": style,
            "title": build_title(label, context, style_label),
            "tags": build_tags(label, ctx_tags, style_tags),
            "description": build_description(scene, style_label, context),
        })

    os.makedirs("reports/listings", exist_ok=True)
    out = f"reports/listings/publication_pack_{date.today().isoformat()}.csv"
    if rows:
        with open(out, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            w.writeheader()
            w.writerows(rows)
    print(f"{out} : {len(rows)} listings")
    # Stats par série
    from collections import Counter
    for s, n in Counter(r["series"] for r in rows).most_common():
        print(f"  {s}: {n}")


if __name__ == "__main__":
    main()
