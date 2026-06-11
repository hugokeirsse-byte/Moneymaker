#!/usr/bin/env python3
"""
build_flag_hexagon_ball_cdc.py — CDC "ballon hexagones-drapeau", 1 patch par pays.

Patch rond style broderie cousue main : un ballon de foot classique dont les
hexagones noirs sont remplacés par le drapeau du pays, répété dans chaque
hexagone. 34 nations (mêmes participants que le CDC flag_patches v1).
Texte pays ajouté ensuite via scripts/overlay_patch_text.py (_canva_text).
"""
import json
from datetime import datetime, timezone

# (label Canva, description du drapeau à l'échelle hexagone, couleurs du liseré)
COUNTRIES = {
    "france": ("FRANCE", "vertical bands of deep royal blue, crisp white and vivid red", "gold and deep navy"),
    "england": ("ENGLAND", "a bold red St George's cross on a pure white ground", "navy blue and red"),
    "spain": ("SPAIN", "horizontal bands of rich crimson red, golden yellow and crimson red", "red and gold"),
    "germany": ("GERMANY", "horizontal bands of jet black, bold red and warm golden yellow", "gold and black"),
    "portugal": ("PORTUGAL", "a vertical split of deep forest green and rich crimson red", "green and red"),
    "netherlands": ("NETHERLANDS", "horizontal bands of vivid red, pure white and deep cobalt blue", "orange and navy"),
    "belgium": ("BELGIUM", "vertical bands of jet black, bright golden yellow and bold red", "gold and black"),
    "switzerland": ("SWITZERLAND", "a bold white cross on a vivid crimson red ground", "red and white"),
    "croatia": ("CROATIA", "horizontal bands of red, white and dark blue with a tiny red and white checkerboard accent", "red and white"),
    "denmark": ("DENMARK", "a white Nordic cross on a deep cherry red ground", "red and white"),
    "austria": ("AUSTRIA", "horizontal bands of rich red, pure white and rich red", "red and white"),
    "serbia": ("SERBIA", "horizontal bands of deep royal blue, vivid red and white", "red and navy"),
    "turkey": ("TURKEY", "a white crescent moon and five-pointed star on a glowing crimson red ground", "red and white"),
    "ukraine": ("UKRAINE", "a horizontal split of vivid cerulean blue over warm golden yellow", "blue and gold"),
    "argentina": ("ARGENTINA", "horizontal bands of light sky blue, white and light sky blue with a tiny golden sun", "sky blue and gold"),
    "brazil": ("BRAZIL", "a golden yellow diamond on a vivid forest green ground with a tiny royal blue sphere", "green and gold"),
    "uruguay": ("URUGUAY", "alternating white and cerulean blue stripes with a tiny golden sun", "blue and gold"),
    "colombia": ("COLOMBIA", "a wide golden yellow band over narrow deep blue and bold red bands", "gold and red"),
    "ecuador": ("ECUADOR", "horizontal bands of bright golden yellow, vivid royal blue and bold red", "gold and blue"),
    "usa": ("USA", "red and white stripes with a deep navy blue canton dotted with tiny white stars", "red and navy"),
    "canada": ("CANADA", "a red maple leaf on a white center between two red side bands", "red and white"),
    "mexico": ("MEXICO", "vertical bands of rich forest green, bright white and bold red with a tiny golden eagle emblem", "green and red"),
    "panama": ("PANAMA", "four quadrants of white and cerulean blue with tiny blue and red five-pointed stars", "red and blue"),
    "honduras": ("HONDURAS", "horizontal bands of cerulean blue, pure white and cerulean blue with tiny blue stars", "blue and white"),
    "japan": ("JAPAN", "a single bold crimson red circle centered on a pure white ground", "red and white"),
    "south_korea": ("SOUTH KOREA", "a red and blue taeguk yin-yang circle with short black trigram bars on a white ground", "navy and red"),
    "australia": ("AUSTRALIA", "a deep azure blue ground with a tiny Union Jack corner and small white stars of the Southern Cross", "navy and gold"),
    "iran": ("IRAN", "horizontal bands of deep forest green, pure white and deep red", "green and red"),
    "saudi_arabia": ("SAUDI ARABIA", "a deep emerald green ground with a tiny white horizontal sword beneath ornamental white scrollwork", "green and white"),
    "morocco": ("MOROCCO", "a green interlaced five-pointed star on a deep crimson red ground", "red and green"),
    "senegal": ("SENEGAL", "vertical bands of forest green, golden yellow and bold red with a tiny green star", "green and gold"),
    "nigeria": ("NIGERIA", "vertical bands of deep forest green, pure white and deep forest green", "green and white"),
    "ivory_coast": ("IVORY COAST", "vertical bands of warm tangerine orange, pure white and lush forest green", "orange and green"),
    "new_zealand": ("NEW ZEALAND", "a deep royal azure blue ground with a tiny Union Jack corner and small red stars of the Southern Cross", "navy and white"),
}

PROMPT_TEMPLATE = (
    "Circular embroidery patch depicting EXACTLY ONE classic hand-stitched soccer ball "
    "filling the center of the patch, where EVERY hexagonal panel that would normally be "
    "black is instead embroidered with the {label} flag pattern — {flag} — the same "
    "miniature flag repeated identically in each hexagonal panel, while the remaining "
    "panels stay cream white satin stitch like a traditional football. Bold black "
    "chain-stitch outlines between all panels of the ball. Thick twisted {border} rope "
    "border around the circular patch edge. Embroidered iron-on patch on dark felt, "
    "hand-sewn look with visible satin stitch thread texture throughout each panel, "
    "centered composition, full circular design entirely visible with clear margin, "
    "no text no letters no words."
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
        "hexagon. 34 nations, one circular patch each. Country name added via text overlay. "
        "Supersedes worldcup2026_football_hexagons v1 (mixed-flag variants, cancelled)."
    ),
    "platform": "redbubble",
    "total_briefs": len(briefs),
    "briefs": briefs,
}

out = f"reports/redbubble/cahiers_des_charges_worldcup2026_flag_hexagon_balls_{now.strftime('%Y%m%d_%H%M')}.json"
with open(out, "w", encoding="utf-8") as fh:
    json.dump(doc, fh, indent=2, ensure_ascii=False)
print(f"{out} : {len(briefs)} briefs (1 ballon hexagones-drapeau par pays)")
