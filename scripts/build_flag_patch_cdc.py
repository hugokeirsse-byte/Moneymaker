#!/usr/bin/env python3
"""
build_flag_patch_cdc.py — CDC drapeaux Coupe du Monde 2026, v2 corrigée.

48 nations réellement qualifiées (source : vagues du 10/06 construites avec
Google Search grounding + vérification web du 11/06).
- Retire 5 pays NON qualifiés de la v1 : denmark, honduras, nigeria, serbia, ukraine.
- Ajoute les 19 qualifiés manquants : algeria, bosnia, cape_verde, congo_dr,
  curacao, czechia, egypt, ghana, haiti, iraq, jordan, norway, paraguay, qatar,
  scotland, south_africa, sweden, tunisia, uzbekistan.
- Réutilise mot pour mot les 29 prompts validés de la v1, enrichis du même
  suffixe qualité macro-broderie (optimisé FLUX.2 Dev).
- Bloc "generation" : FLUX.2 Dev (runware:400@1) 2048×2048 + upscale ×2 → 4096px.
"""
import json
import glob
from datetime import datetime, timezone

V1_GLOB = "reports/redbubble/cahiers_des_charges_worldcup2026_flag_patches_2026*.json"
NOT_QUALIFIED = {"denmark", "honduras", "nigeria", "serbia", "ukraine"}

ENHANCER = (
    "Ultra-detailed macro embroidery rendering: individual thread strands clearly "
    "visible, raised stitch relief catching soft studio light, subtle textile sheen, "
    "crisp clean edges. "
)
FINAL_CLAUSE = "full circular design entirely visible with clear margin"
ENDING = (
    "Embroidered iron-on patch on dark felt, visible thread texture throughout, "
    "full circular design entirely visible with clear margin, no text no letters no words."
)
NEG = "text, letters, words, watermark, photorealistic, extra stitches outside patch, cropped edges"

# 19 qualifiés manquants — même gabarit que les prompts v1
NEW_COUNTRIES = {
    "norway": ("NORWAY", "Circular embroidery patch featuring the Norwegian flag: vivid scarlet red field in dense horizontal satin stitch, crossed by a deep indigo blue Nordic cross outlined in crisp white couching stitch, cross bars offset toward the left in classic Scandinavian style, each color zone showing clean raised thread ridges. Thick red and navy twisted rope border around the circular patch edge. "),
    "scotland": ("SCOTLAND", "Circular embroidery patch featuring the Scottish Saltire: deep royal azure blue field in smooth satin stitch, crossed corner to corner by a bold white diagonal saltire cross in raised satin stitch with clearly visible thread ridges, a tiny embroidered silver thistle accent at the center crossing point. Thick navy and white twisted rope border around the circular patch edge. "),
    "sweden": ("SWEDEN", "Circular embroidery patch featuring the Swedish flag: bright royal blue field in dense horizontal satin stitch crossed by a warm golden yellow Nordic cross offset toward the left, the golden bars in raised satin stitch with rich metallic sheen, a tiny golden crown accent at the cross intersection. Thick blue and gold twisted rope border around the circular patch edge. "),
    "czechia": ("CZECHIA", "Circular embroidery patch featuring the Czech flag: horizontal halves of pure white above bold red in clean parallel satin stitch, a deep royal blue triangle extending from the left edge to the center in dense diagonal satin stitch, a tiny silver double-tailed lion silhouette accent embroidered in the blue triangle. Thick red and blue twisted rope border around the circular patch edge. "),
    "bosnia": ("BOSNIA", "Circular embroidery patch featuring the Bosnian flag: deep royal blue field in smooth satin stitch, a large golden yellow right triangle in dense diagonal satin stitch, a diagonal row of small white five-pointed stars in raised stitch running along the triangle's long edge. Thick blue and gold twisted rope border around the circular patch edge. "),
    "algeria": ("ALGERIA", "Circular embroidery patch featuring the Algerian flag: vertical halves of emerald green and pure white in dense upright satin stitch, a vivid red crescent moon embracing a red five-pointed star at the exact center in raised satin stitch with crisp edges. Thick green and red twisted rope border around the circular patch edge. "),
    "tunisia": ("TUNISIA", "Circular embroidery patch featuring the Tunisian flag: glowing scarlet red field in dense diagonal satin stitch, a pure white circle at the center in smooth flat stitch containing a red crescent moon embracing a red five-pointed star in raised satin stitch. Thick red and white twisted rope border around the circular patch edge. "),
    "egypt": ("EGYPT", "Circular embroidery patch featuring the Egyptian flag: three horizontal bands of bold red, pure white and jet black in dense parallel satin stitch, a small golden eagle emblem embroidered in fine metallic gold thread at the center of the white band. Thick gold and black twisted rope border around the circular patch edge. "),
    "ghana": ("GHANA", "Circular embroidery patch featuring the Ghanaian flag: three horizontal bands of bold red, warm golden yellow and forest green in dense parallel satin stitch, a jet black five-pointed star in raised satin stitch centered on the golden band. Thick gold and green twisted rope border around the circular patch edge. "),
    "south_africa": ("SOUTH AFRICA", "Circular embroidery patch featuring the South African flag: a bold green horizontal Y shape edged in crisp white running from the left edge, a black triangle at the left edged in golden yellow, a band of vivid red above and royal blue below, each zone in dense satin stitch with clean seam lines between colors. Thick green and gold twisted rope border around the circular patch edge. "),
    "cape_verde": ("CAPE VERDE", "Circular embroidery patch featuring the Cape Verdean flag: deep ocean blue field in smooth horizontal satin stitch, crossed below center by a band of white-red-white horizontal stripes, a circle of ten small golden five-pointed stars in raised stitch overlapping the stripes. Thick blue and gold twisted rope border around the circular patch edge. "),
    "congo_dr": ("DR CONGO", "Circular embroidery patch featuring the DR Congo flag: bright sky blue field in smooth satin stitch, a bold diagonal red stripe edged in golden yellow running corner to corner, a large golden five-pointed star in raised satin stitch in the upper left corner. Thick sky blue and red twisted rope border around the circular patch edge. "),
    "qatar": ("QATAR", "Circular embroidery patch featuring the Qatari flag: deep maroon field in dense horizontal satin stitch joined to a pure white band by a serrated zigzag edge of nine sharp points rendered in crisp raised stitch. Thick maroon and white twisted rope border around the circular patch edge. "),
    "iraq": ("IRAQ", "Circular embroidery patch featuring the Iraqi flag: three horizontal bands of bold red, pure white and jet black in dense parallel satin stitch, a small ornamental emerald green emblem embroidered at the center of the white band. Thick red and green twisted rope border around the circular patch edge. "),
    "jordan": ("JORDAN", "Circular embroidery patch featuring the Jordanian flag: three horizontal bands of jet black, pure white and forest green in dense satin stitch, a vivid red triangle extending from the left edge containing a tiny white seven-pointed star in raised stitch. Thick red and white twisted rope border around the circular patch edge. "),
    "uzbekistan": ("UZBEKISTAN", "Circular embroidery patch featuring the Uzbek flag: three horizontal bands of bright sky blue, pure white and emerald green separated by thin red seam lines in fine stitch, a tiny white crescent moon and a cluster of small white stars embroidered in the upper left of the blue band. Thick sky blue and green twisted rope border around the circular patch edge. "),
    "paraguay": ("PARAGUAY", "Circular embroidery patch featuring the Paraguayan flag: three horizontal bands of bold red, pure white and royal blue in dense parallel satin stitch, a small circular golden star emblem ringed by a tiny green wreath embroidered at the center of the white band. Thick red and blue twisted rope border around the circular patch edge. "),
    "haiti": ("HAITI", "Circular embroidery patch featuring the Haitian flag: horizontal halves of royal blue above bold red in dense satin stitch, a small white square panel at the center bearing a tiny embroidered royal palm tree flanked by tiny green flags. Thick blue and red twisted rope border around the circular patch edge. "),
    "curacao": ("CURACAO", "Circular embroidery patch featuring the Curacao flag: deep ultramarine blue field in smooth satin stitch, a horizontal golden yellow stripe across the lower third, two white five-pointed stars of different sizes in raised stitch in the upper left. Thick blue and gold twisted rope border around the circular patch edge. "),
}


def enhance(prompt: str) -> str:
    """Insère le suffixe qualité macro-broderie avant la clause finale."""
    idx = prompt.find(FINAL_CLAUSE)
    if idx == -1:
        return prompt.rstrip() + " " + ENHANCER.strip()
    return prompt[:idx] + ENHANCER + prompt[idx:]


def make_brief(cid: str, label: str, prompt: str) -> dict:
    return {
        "name": f"{cid} — Flag Patch",
        "_style_id": "embroidery_patch",
        "_expression_id": cid,
        "_idiom": label,
        "_canva_text": label,
        "ai_generation": {
            "positive_prompt": enhance(prompt),
            "negative_prompt": NEG,
            "cfg_scale": 4.0,
            "tiling": False,
            "seed_image_url": None,
        },
    }


v1_path = sorted(glob.glob(V1_GLOB))[0]
v1 = json.load(open(v1_path, encoding="utf-8"))

briefs = []
kept = []
for b in v1["briefs"]:
    cid = b["_expression_id"].replace("-", "_")
    if cid in NOT_QUALIFIED:
        continue
    kept.append(cid)
    briefs.append(make_brief(cid, b["_canva_text"], b["ai_generation"]["positive_prompt"]))

for cid, (label, prompt) in NEW_COUNTRIES.items():
    briefs.append(make_brief(cid, label, prompt + ENDING))

now = datetime.now(timezone.utc)
doc = {
    "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "series": "worldcup2026_flag_patches_v2",
    "styles": ["embroidery_patch"],
    "description": (
        "World Cup 2026 — 48 qualified-nation flag embroidery patches (corrected list: "
        "removes 5 non-qualified nations from v1, adds the 19 missing qualifiers). "
        "One circular patch per nation, country name via text overlay. "
        "FLUX.2 Dev 2048px + AI upscale x2."
    ),
    "platform": "redbubble",
    "total_briefs": len(briefs),
    "generation": {
        "model": "runware:400@1",
        "width": 2048,
        "height": 2048,
        "steps": 30,
        "upscale_factor": 2,
        "target_px": 4000,
    },
    "briefs": briefs,
}

out = f"reports/redbubble/cahiers_des_charges_worldcup2026_flag_patches_v2_{now.strftime('%Y%m%d_%H%M')}.json"
with open(out, "w", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, ensure_ascii=False)
print(f"{out} : {len(briefs)} briefs ({len(kept)} repris de v1 + {len(NEW_COUNTRIES)} nouveaux)")
