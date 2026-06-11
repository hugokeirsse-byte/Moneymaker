#!/usr/bin/env python3
"""
build_flag_hexagon_ball_cdc.py — CDC "ballon hexagones-drapeau", 1 patch par pays.

Patch rond style broderie cousue main : un ballon de foot classique dont les
hexagones noirs sont remplacés par le drapeau du pays, répété dans chaque
hexagone. 48 nations qualifiées (liste corrigée du 11/06 — voir
build_flag_patch_cdc.py pour la provenance).
Texte pays ajouté ensuite via scripts/overlay_patch_text.py (_canva_text).
Génération : FLUX.2 Dev (runware:400@1) 2048×2048 + upscale ×2 → 4096px.
"""
import json
from datetime import datetime, timezone

# (label Canva, description du drapeau à l'échelle hexagone, couleurs du liseré)
COUNTRIES = {
    # ——— Europe (16) ———
    "france": ("FRANCE", "vertical bands of deep royal blue, crisp white and vivid red", "gold and deep navy"),
    "england": ("ENGLAND", "a bold red St George's cross on a pure white ground", "navy blue and red"),
    "spain": ("SPAIN", "horizontal bands of rich crimson red, golden yellow and crimson red", "red and gold"),
    "germany": ("GERMANY", "horizontal bands of jet black, bold red and warm golden yellow", "gold and black"),
    "portugal": ("PORTUGAL", "a vertical split of deep forest green and rich crimson red", "green and red"),
    "netherlands": ("NETHERLANDS", "horizontal bands of vivid red, pure white and deep cobalt blue", "orange and navy"),
    "belgium": ("BELGIUM", "vertical bands of jet black, bright golden yellow and bold red", "gold and black"),
    "switzerland": ("SWITZERLAND", "a bold white cross on a vivid crimson red ground", "red and white"),
    "croatia": ("CROATIA", "horizontal bands of red, white and dark blue with a tiny red and white checkerboard accent", "red and white"),
    "austria": ("AUSTRIA", "horizontal bands of rich red, pure white and rich red", "red and white"),
    "turkey": ("TURKIYE", "a white crescent moon and five-pointed star on a glowing crimson red ground", "red and white"),
    "norway": ("NORWAY", "a deep blue Nordic cross outlined in white on a scarlet red ground", "red and navy"),
    "scotland": ("SCOTLAND", "a bold white diagonal saltire cross on a royal azure blue ground", "navy and white"),
    "sweden": ("SWEDEN", "a golden yellow Nordic cross on a bright royal blue ground", "blue and gold"),
    "czechia": ("CZECHIA", "white over red horizontal halves with a deep royal blue triangle at the left", "red and blue"),
    "bosnia": ("BOSNIA", "a golden yellow triangle and a diagonal row of small white stars on a royal blue ground", "blue and gold"),
    # ——— Amérique du Sud (6) ———
    "argentina": ("ARGENTINA", "horizontal bands of light sky blue, white and light sky blue with a tiny golden sun", "sky blue and gold"),
    "brazil": ("BRAZIL", "a golden yellow diamond on a vivid forest green ground with a tiny royal blue sphere", "green and gold"),
    "uruguay": ("URUGUAY", "alternating white and cerulean blue stripes with a tiny golden sun", "blue and gold"),
    "colombia": ("COLOMBIA", "a wide golden yellow band over narrow deep blue and bold red bands", "gold and red"),
    "ecuador": ("ECUADOR", "horizontal bands of bright golden yellow, vivid royal blue and bold red", "gold and blue"),
    "paraguay": ("PARAGUAY", "horizontal bands of bold red, pure white and royal blue with a tiny golden star emblem", "red and blue"),
    # ——— Amérique du Nord & Caraïbes (6) ———
    "usa": ("USA", "red and white stripes with a deep navy blue canton dotted with tiny white stars", "red and navy"),
    "canada": ("CANADA", "a red maple leaf on a white center between two red side bands", "red and white"),
    "mexico": ("MEXICO", "vertical bands of rich forest green, bright white and bold red with a tiny golden eagle emblem", "green and red"),
    "panama": ("PANAMA", "four quadrants of white and cerulean blue with tiny blue and red five-pointed stars", "red and blue"),
    "haiti": ("HAITI", "royal blue over bold red horizontal halves with a tiny white center panel", "blue and red"),
    "curacao": ("CURACAO", "a deep ultramarine blue ground with a golden yellow stripe and two white stars", "blue and gold"),
    # ——— Asie & Océanie (10) ———
    "japan": ("JAPAN", "a single bold crimson red circle centered on a pure white ground", "red and white"),
    "south_korea": ("SOUTH KOREA", "a red and blue taeguk yin-yang circle with short black trigram bars on a white ground", "navy and red"),
    "australia": ("AUSTRALIA", "a deep azure blue ground with a tiny Union Jack corner and small white stars of the Southern Cross", "navy and gold"),
    "iran": ("IRAN", "horizontal bands of deep forest green, pure white and deep red", "green and red"),
    "saudi_arabia": ("SAUDI ARABIA", "a deep emerald green ground with a tiny white horizontal sword beneath ornamental white scrollwork", "green and white"),
    "qatar": ("QATAR", "a deep maroon ground with a white serrated band of nine sharp points along one side", "maroon and white"),
    "iraq": ("IRAQ", "horizontal bands of bold red, pure white and jet black with a small ornamental green emblem", "red and green"),
    "jordan": ("JORDAN", "horizontal bands of black, white and green with a red triangle bearing a tiny white star", "red and white"),
    "uzbekistan": ("UZBEKISTAN", "horizontal bands of sky blue, white and green separated by thin red lines with a tiny white crescent and stars", "sky blue and green"),
    "new_zealand": ("NEW ZEALAND", "a deep royal azure blue ground with a tiny Union Jack corner and small red stars of the Southern Cross", "navy and white"),
    # ——— Afrique (10) ———
    "morocco": ("MOROCCO", "a green interlaced five-pointed star on a deep crimson red ground", "red and green"),
    "senegal": ("SENEGAL", "vertical bands of forest green, golden yellow and bold red with a tiny green star", "green and gold"),
    "ivory_coast": ("IVORY COAST", "vertical bands of warm tangerine orange, pure white and lush forest green", "orange and green"),
    "algeria": ("ALGERIA", "a vertical split of emerald green and white with a red crescent and star at the center", "green and red"),
    "tunisia": ("TUNISIA", "a bold red ground with a white circle containing a red crescent and star", "red and white"),
    "egypt": ("EGYPT", "horizontal bands of red, white and black with a small golden eagle emblem at the center", "gold and black"),
    "ghana": ("GHANA", "horizontal bands of red, golden yellow and green with a black five-pointed star at the center", "gold and green"),
    "south_africa": ("SOUTH AFRICA", "a green horizontal Y shape edged in white and gold separating red, blue and black sections", "green and gold"),
    "cape_verde": ("CAPE VERDE", "a deep blue ground crossed by white and red stripes with a ring of small golden stars", "blue and gold"),
    "congo_dr": ("DR CONGO", "a sky blue ground with a diagonal red stripe edged in yellow and a golden star in the corner", "sky blue and red"),
}

PROMPT_TEMPLATE = (
    "Circular embroidery patch depicting EXACTLY ONE classic hand-stitched soccer ball "
    "filling the center of the patch, where EVERY hexagonal panel that would normally be "
    "black is instead embroidered with the {label} flag pattern — {flag} — the same "
    "miniature flag repeated identically in each hexagonal panel, while the remaining "
    "panels stay cream white satin stitch like a traditional football. Bold black "
    "chain-stitch outlines between all panels of the ball. Thick twisted {border} rope "
    "border around the circular patch edge. Embroidered iron-on patch on dark felt, "
    "hand-sewn look with visible satin stitch thread texture throughout each panel. "
    "Ultra-detailed macro embroidery rendering: individual thread strands clearly "
    "visible, raised stitch relief catching soft studio light, subtle textile sheen, "
    "crisp clean edges. Centered composition, full circular design entirely visible "
    "with clear margin, no text no letters no words."
)

NEG = "text, letters, words, watermark, photorealistic, flat design without texture, cropped edges, extra balls"

briefs = []
for cid, (label, flag, border) in COUNTRIES.items():
    briefs.append({
        "name": f"{cid} — Flag Hexagon Ball Patch",
        "_style_id": "embroidery_patch",
        "_expression_id": f"{cid}_flag_ball",
        "_idiom": label,
        "_canva_text": label,
        "ai_generation": {
            "positive_prompt": PROMPT_TEMPLATE.format(label=label.title(), flag=flag, border=border),
            "negative_prompt": NEG,
            "cfg_scale": 4.0,
            "tiling": False,
            "seed_image_url": None,
        },
    })

now = datetime.now(timezone.utc)
doc = {
    "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    "series": "worldcup2026_flag_hexagon_balls_v2",
    "styles": ["embroidery_patch"],
    "description": (
        "World Cup 2026 — soccer ball embroidery patch per nation: the black hexagons "
        "of a classic football replaced by that single country's flag, repeated in every "
        "hexagon. 48 qualified nations, one circular patch each. Country name added via "
        "text overlay. FLUX.2 Dev 2048px + AI upscale x2. "
        "Supersedes worldcup2026_football_hexagons v1 (mixed-flag variants, cancelled)."
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

out = f"reports/redbubble/cahiers_des_charges_worldcup2026_flag_hexagon_balls_v2_{now.strftime('%Y%m%d_%H%M')}.json"
with open(out, "w", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, ensure_ascii=False)
print(f"{out} : {len(briefs)} briefs (1 ballon hexagones-drapeau par pays qualifié)")
