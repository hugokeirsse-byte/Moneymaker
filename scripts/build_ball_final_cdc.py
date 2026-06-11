#!/usr/bin/env python3
"""
build_ball_final_cdc.py — CDC ballons Telstar finals, prompt durci définitif.

Usage:
    python scripts/build_ball_final_cdc.py <serie> <sha_seeds> pays1 pays2 ...

Pré-requis : les seeds data/seeds/<pays>_telstar_seed.png existent au commit
<sha_seeds> (URLs épinglées au SHA pour éviter tout cache raw.githubusercontent).
Les descriptions de drapeau et couleurs de liseré sont dans COUNTRY_META.
"""
import json
import sys
from datetime import datetime, timezone

# Gabarit DURCI (11/06) : géométrie verrouillée par le seed, fidélité stricte,
# taille des drapeaux PROPORTIONNELLE à chaque pentagone (perspective sphérique).
BASE = (
    "Transform this exact image into a photographic macro shot of a circular embroidered "
    "iron-on patch on dark charcoal felt. The source image is the exact blueprint: do not "
    "move, resize, merge, add or omit ANY panel, and do not change the number of stripes, "
    "stars, leaves, crosses or emblem elements of any flag. Only the material rendering "
    "changes: flat colors become dense embroidered thread. The ball is a classic 32-panel "
    "Telstar soccer ball; every pentagon panel carries {flag_desc}; every hexagon panel "
    "stays plain cream-white satin stitch with no pattern whatsoever. The flag design is "
    "strictly identical in every pentagon and fills the same fraction of its panel — "
    "pentagons near the silhouette are smaller because of the spherical perspective, so "
    "their flags are proportionally smaller but otherwise identical, exactly as in the "
    "source image. Render all panel seams as clean black chain-stitch embroidery "
    "following the curvature of the sphere, give the ball gentle three-dimensional "
    "spherical shading, and turn the colored rings into a thick twisted {border} rope "
    "border around the circular patch edge. Dense embroidery texture everywhere: "
    "individual thread strands clearly visible, raised satin-stitch relief catching soft "
    "studio light, subtle textile sheen. The whole circular patch fully visible with a "
    "clear margin of dark felt all around. No text, no letters, no numbers, no logos, "
    "no watermark."
)

COUNTRY_META = {
    "france": ("FRANCE", "the flag of France — vertical royal blue, white and red bands", "gold and navy"),
    "usa": ("USA", "the flag of the United States — thirteen red and white stripes with the navy star-filled canton", "navy and red"),
    "england": ("ENGLAND", "the flag of England — the red St George's cross on a pure white ground", "red and white"),
    "germany": ("GERMANY", "the flag of Germany — horizontal black, red and gold bands", "black and gold"),
    "canada": ("CANADA", "the flag of Canada — two red vertical side bands flanking a white square bearing the eleven-pointed red maple leaf exactly as drawn", "red and white"),
    "brazil": ("BRAZIL", "the flag of Brazil — green field, large golden diamond reaching close to the edges, deep blue globe with its thin white curved band and small white stars, exactly as drawn", "green and gold"),
    "mexico": ("MEXICO", "the flag of Mexico — vertical green, white and red bands with the brown eagle on its cactus holding a snake, framed by the small green laurel wreath", "green and red"),
    "argentina": ("ARGENTINA", "the flag of Argentina — horizontal sky blue, white and sky blue bands with the golden Sun of May at the center", "sky blue and gold"),
    "spain": ("SPAIN", "the flag of Spain — horizontal red, wide golden yellow and red bands with the small coat-of-arms toward the hoist side", "red and gold"),
    "netherlands": ("NETHERLANDS", "the flag of the Netherlands — horizontal red, white and cobalt blue bands", "orange and navy"),
    "portugal": ("PORTUGAL", "the flag of Portugal — vertical green and red fields with the small armillary sphere emblem at their boundary", "green and red"),
    "japan": ("JAPAN", "the flag of Japan — a single crimson red disc centered on a pure white ground", "red and white"),
    # … compléter pays par pays au fil des lots (peintre exact requis dans
    # render_telstar_seed.py avant tout lancement)
}


def main() -> int:
    serie, sha = sys.argv[1], sys.argv[2]
    countries = sys.argv[3:]
    briefs = []
    for cid in countries:
        label, desc, border = COUNTRY_META[cid]
        briefs.append({
            "name": f"{cid} — Telstar Flag Ball final",
            "_style_id": "embroidery_patch",
            "_expression_id": f"{cid}_telstar_{serie}",
            "_idiom": label,
            "_canva_text": label,
            "ai_generation": {
                "positive_prompt": BASE.format(flag_desc=desc, border=border),
                "negative_prompt": "",
                "cfg_scale": 4.5,
                "tiling": False,
                "reference_image_url": (
                    f"https://raw.githubusercontent.com/hugokeirsse-byte/Moneymaker/"
                    f"{sha}/data/seeds/{cid}_telstar_seed.png"
                ),
            },
        })
    now = datetime.now(timezone.utc)
    doc = {
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "series": f"worldcup2026_ball_final_{serie}",
        "styles": ["embroidery_patch"],
        "description": f"Ballons Telstar finals — {', '.join(countries)} (prompt durci, seeds exacts épinglés).",
        "platform": "redbubble",
        "total_briefs": len(briefs),
        "generation": {"model": "runware:400@1", "width": 2048, "height": 2048,
                        "steps": 40, "upscale_factor": 2, "target_px": 4000,
                        "require_ai_upscale": True},
        "briefs": briefs,
    }
    p = f"reports/redbubble/cahiers_des_charges_worldcup2026_zball_final_{serie}_{now.strftime('%Y%m%d_%H%M')}.json"
    json.dump(doc, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print(f"{p} : {len(briefs)} briefs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
