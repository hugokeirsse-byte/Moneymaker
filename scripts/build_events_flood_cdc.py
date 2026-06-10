#!/usr/bin/env python3
"""
build_events_flood_cdc.py — génère 3 CDCs :
  A. Flood événements juin : 6 événements x 3 concepts x 20 styles = 360 briefs
  B. Coupe du Monde vague 2a : 16 pays x 20 styles = 320 briefs
  C. Coupe du Monde vague 2b : 16 pays x 20 styles = 320 briefs
Chaque scène lisible sans texte. Aucun logo officiel.
"""
import json
from datetime import datetime, timezone

STYLES = {
    "risograph": "Illustrated in risograph print style: visible riso grain texture across the whole image, strictly limited 3-color palette of cobalt blue, warm coral orange and cream white, flat simplified shapes, slight intentional color misregistration, lo-fi zine aesthetic.",
    "flat_vector": "Illustrated in bold flat vector style: thick black outlines, solid vivid color fills with zero gradients, bright primary colors, clean geometric simplicity, modern graphic design, no shading.",
    "ukiyo_e": "Illustrated in Japanese ukiyo-e woodblock print style: flat color areas of indigo blue, vermillion red, cream and forest green, bold carved outlines, decorative stylized clouds, traditional Edo-period aesthetic, woodblock print texture.",
    "retro_neon_80s": "Illustrated in 1980s retro synthwave neon style: hot pink, electric blue and laser yellow against a deep purple background, neon glow outlines, halftone dots, Miami Vice aesthetic.",
    "cut_paper_collage": "Illustrated in cut paper collage style: layered torn-edge paper shapes, mixed paper textures of newsprint, kraft brown and origami colored papers, visible layered drop shadows, handmade craft aesthetic, bright bold colors.",
    "vintage_watercolor": "Illustrated in vintage watercolor style: delicate washes of muted dusty blue, warm taupe, soft gold and sage green, fine ink pen linework over the washes, aged parchment texture background, Victorian natural-history aesthetic.",
    "cartoon_network": "Illustrated in Adventure Time cartoon network style: thick bold black cartoon outlines, flat vivid color fills, simple round pudgy characters with big expressive faces, 2D cel animation aesthetic, white background.",
    "victorian_engraving": "Illustrated in Victorian engraving style: fine crosshatching and stippling throughout, monochromatic sepia-brown on aged cream parchment, ornate engraved decorative border, 1860s natural history atlas aesthetic.",
    "memphis_design": "Illustrated in Memphis postmodern 1980s design style: bold geometric shapes, triangles, squiggles, polka dots and zigzag lines, vibrant palette of tomato red, sunshine yellow, cobalt blue, seafoam green and hot pink, flat playful composition.",
    "ghibli_painted": "Illustrated in Studio Ghibli hand-painted style: warm earthy palette of dusty periwinkle, warm ochre, sage green and soft coral, painterly atmospheric light, expressive cute characters with big curious eyes, dreamy whimsical storybook mood.",
    "pixel_art": "Illustrated in retro 16-bit pixel art style: pixelated characters at large visible pixel scale, limited 8-color retro console palette, crisp hard pixel edges, video game sprite aesthetic.",
    "minimalist_line": "Illustrated in minimalist continuous line style: one unbroken black ink line on pure white background, elegant zen aesthetic, generous negative space, no color fills, thin precise even line weight.",
    "gothic_dark": "Illustrated in gothic dark whimsical style: stark black and white with blood red accent color, ornate Victorian gothic decorative frame, spooky-cute aesthetic, high contrast dramatic composition.",
    "psychedelic_60s": "Illustrated in 1960s psychedelic poster style: swirling kaleidoscopic shapes, concentric rainbow rings of turquoise, magenta, yellow, orange and lime green, groovy wavy lines, Peter Max concert poster aesthetic.",
    "kawaii_chibi": "Illustrated in kawaii Japanese chibi style: adorable tiny chubby characters with oversized round heads and huge dot eyes, baby pastel palette of blush pink, lavender, baby blue, lemon yellow and mint green, sparkle and star accents, tiny blush cheeks.",
    "woodcut_linocut": "Illustrated in woodcut linocut print style: bold raw carved texture marks, high contrast two-tone palette of black and cobalt blue on cream background, rough gouge lines visible throughout, handmade reduction print aesthetic.",
    "tattoo_flash": "Illustrated in traditional American tattoo flash style: bold thick black outlines, classic Sailor Jerry color fills of red, cobalt blue, forest green and yellow, small heart and star accents, aged cream background, vintage tattoo parlor aesthetic.",
    "art_nouveau": "Illustrated in Art Nouveau style: flowing organic sinuous linework, muted jewel tones of jade green, burgundy, antique gold and dusty violet, circular ornamental frame with intricate botanical border, Alphonse Mucha inspired elegance.",
    "swiss_constructivist": "Illustrated in Swiss constructivist poster style: stark geometric composition, bold circles and parallel lines, strictly two-color palette of pure black and a single saturated red, grid-based negative space, Bauhaus functional aesthetic.",
    "pop_art": "Illustrated in Pop Art comic book style: Ben-Day halftone dot patterns, bold primary colors of red, yellow and cobalt blue, thick black outlines, high contrast dramatic comic panel composition, Roy Lichtenstein aesthetic.",
}

SUFFIX = " Absolutely no text anywhere, no letters, no words, no writing, no numbers, no signature. Square sticker art, centered composition, clean background."
NEG = "text, letters, words, watermark, extra limbs, deformed anatomy, nudity, photorealistic"

# 6 événements x 3 concepts — images parlantes sans texte
EVENTS = {
    "fathersday": ("FATHER'S DAY", [
        ("pier", "EXACTLY ONE dad and EXACTLY ONE small child seen from behind, sitting side by side on the edge of a wooden pier, fishing together at sunset, the child's head leaning against the dad's arm, EXACTLY TWO fishing rods, calm water, large warm sun low on the horizon."),
        ("superteam", "EXACTLY ONE dad with EXACTLY ONE small child sitting on his shoulders, both wearing matching superhero capes and masks, both raising one fist triumphantly toward the sky, both with enormous matching grins."),
        ("trophy_hug", "EXACTLY ONE proud dad holding EXACTLY ONE giant gleaming golden trophy above his head while EXACTLY TWO small children hug his legs tightly looking up at him with adoring eyes, rays of light behind."),
    ]),
    "pride": ("PRIDE", [
        ("heart_flag", "EXACTLY ONE cute round heart character with little arms and legs proudly marching forward while waving EXACTLY ONE huge rainbow striped flag twice its size, determined joyful face, EXACTLY THREE small stars floating around."),
        ("hands_heart", "EXACTLY TWO hands of different skin tones reaching toward each other and together forming a heart shape with their fingers, a bold radiating sunburst of rainbow colored rays filling the background."),
        ("unicorn", "EXACTLY ONE chubby round unicorn bursting joyfully through a fluffy white cloud, leaving a wide rainbow arc trail behind it across the sky, sparkles everywhere, enormous delighted grin."),
    ]),
    "juneteenth": ("JUNETEENTH", [
        ("chains_birds", "EXACTLY ONE broken chain at the center, its links opening and transforming into EXACTLY THREE birds flying upward toward EXACTLY ONE large radiant five-pointed star at the top, rays of light around the star."),
        ("star_sunrise", "EXACTLY ONE raised open hand releasing EXACTLY ONE large five-pointed star into the sky above a rising sun on the horizon with bold radiating rays filling the background."),
        ("celebration", "EXACTLY THREE joyful people with brown skin dancing together in celebration under EXACTLY ONE big bursting golden star, confetti falling around them, arms raised in happiness."),
    ]),
    "midsommar": ("MIDSOMMAR", [
        ("frog_crown", "EXACTLY ONE happy round green frog wearing EXACTLY ONE delicate flower crown of daisies, sitting contentedly in tall grass beside EXACTLY ONE small maypole decorated with ribbons and leafy garlands."),
        ("maypole_dance", "EXACTLY ONE tall maypole decorated with leafy garlands and ribbons, EXACTLY TWO figures holding hands dancing around its base, a large midnight sun low on the horizon, a meadow of wildflowers."),
        ("flower_twirl", "EXACTLY ONE cheerful girl wearing an enormous oversized flower crown almost bigger than her head, twirling joyfully with her dress spinning, EXACTLY FIVE flower petals flying off around her, eyes closed in bliss."),
    ]),
    "musicday": ("MUSIC DAY", [
        ("accordion_cat", "EXACTLY ONE chubby cat standing upright playing EXACTLY ONE accordion with its eyes closed in blissful concentration, head tilted back in passionate performance, EXACTLY THREE musical notes floating above."),
        ("guitar_birds", "EXACTLY ONE acoustic guitar standing upright, with a flock of EXACTLY FIVE birds and several musical notes bursting out of its round sound hole and flying upward in a swirling stream."),
        ("animal_band", "EXACTLY THREE animals performing as a band: EXACTLY ONE dog playing drums, EXACTLY ONE cat playing electric guitar with eyes closed, EXACTLY ONE small bird singing into a microphone, musical notes bouncing around."),
    ]),
    "dragonboat": ("DRAGON BOAT", [
        ("race", "EXACTLY ONE long dragon boat with an ornate carved dragon head at its bow, EXACTLY THREE paddlers rowing in perfect synchronization, riding on stylized curling waves, small splashes around the paddles."),
        ("waves_drummer", "EXACTLY ONE powerful dragon boat slicing through EXACTLY TWO big dramatic stylized waves, EXACTLY ONE drummer at the front beating a large drum, paddlers leaning into their strokes behind."),
        ("living_dragon", "EXACTLY ONE happy living green dragon swimming like a boat with a huge grin, EXACTLY THREE tiny rowers sitting in a line on its long back paddling with small oars, small waves around."),
    ]),
}

# Coupe du Monde vague 2 — les 32 autres nations qualifiées
WC2A = {
    "morocco": ("MOROCCO", "EXACTLY ONE man in a red fez hat and djellaba pouring mint tea from a silver teapot in a high graceful arc with one hand while balancing EXACTLY ONE classic football on his other foot, zellige mosaic tiles beneath, the Moroccan red flag with green star as the full background."),
    "senegal": ("SENEGAL", "EXACTLY ONE powerful traditional laamb wrestler in ritual dress balancing EXACTLY ONE classic football on his shoulder in a proud stance, EXACTLY ONE giant baobab tree beside him, the Senegalese green-yellow-red flag with green star as the full background."),
    "egypt": ("EGYPT", "EXACTLY ONE pharaoh figure in golden headdress performing an elegant kick on EXACTLY ONE classic football, EXACTLY TWO pyramids and EXACTLY ONE sphinx watching curiously in the background, the Egyptian red-white-black flag as the full background."),
    "algeria": ("ALGERIA", "EXACTLY ONE man in a white burnous cloak juggling EXACTLY ONE classic football on his knee while EXACTLY ONE small fennec fox with huge ears watches excitedly beside him, desert dunes behind, the Algerian green and white flag with red crescent and star as the full background."),
    "tunisia": ("TUNISIA", "EXACTLY ONE cheerful man holding a bouquet of white jasmine flowers behind his ear doing a heel trick with EXACTLY ONE classic football in front of EXACTLY ONE blue ornate studded door of Sidi Bou Said, the Tunisian red flag with crescent and star as the full background."),
    "ivory_coast": ("IVORY COAST", "EXACTLY ONE energetic djembe drummer drumming with both hands while heading EXACTLY ONE classic football, EXACTLY ONE friendly elephant raising its trunk beside him, the Ivorian orange-white-green flag as the full background."),
    "ghana": ("GHANA", "EXACTLY ONE proud drummer wearing brilliant kente cloth of gold, green and red patterns playing a tall talking drum while balancing EXACTLY ONE classic football on his head, the Ghanaian red-yellow-green flag with black star as the full background."),
    "south_africa": ("SOUTH AFRICA", "EXACTLY ONE joyful supporter blowing EXACTLY ONE long colorful vuvuzela horn while bouncing EXACTLY ONE classic football on his knee, EXACTLY ONE protea flower blooming beside him, the South African multicolored flag as the full background."),
    "cape_verde": ("CAPE VERDE", "EXACTLY ONE smiling musician playing a small guitar with EXACTLY ONE classic football resting at his feet on a beach, EXACTLY TWO volcanic islands rising from the ocean behind, the Cape Verdean blue flag with circle of yellow stars as the full background."),
    "congo_dr": ("DR CONGO", "EXACTLY ONE elegant sapeur gentleman in a perfectly tailored bright suit, bow tie and hat doing a stylish dance step over EXACTLY ONE classic football with a cane in hand, the DR Congo sky-blue flag with yellow star and red diagonal stripe as the full background."),
    "colombia": ("COLOMBIA", "EXACTLY ONE cheerful coffee farmer with a woven basket of red coffee cherries on his back juggling EXACTLY ONE classic football, lush green coffee plants around him, the Colombian yellow-blue-red flag as the full background."),
    "ecuador": ("ECUADOR", "EXACTLY ONE smiling man wearing a genuine woven panama hat juggling EXACTLY ONE classic football high in the Andes mountains, EXACTLY ONE llama watching with curiosity beside him, the Ecuadorian yellow-blue-red flag as the full background."),
    "uruguay": ("URUGUAY", "EXACTLY ONE relaxed man sipping mate from a gourd with a thermos tucked under his arm while expertly balancing EXACTLY ONE classic football on his foot, EXACTLY ONE smoking asado grill beside him, the Uruguayan blue and white striped flag with golden sun as the full background."),
    "paraguay": ("PARAGUAY", "EXACTLY ONE musician gracefully playing a tall Paraguayan harp while EXACTLY ONE classic football balances on top of the harp, delicate white lace patterns floating in the air around, the Paraguayan red-white-blue flag as the full background."),
    "haiti": ("HAITI", "EXACTLY ONE vibrant carnival drummer in bright costume kicking EXACTLY ONE classic football joyfully, EXACTLY TWO hibiscus flowers blooming beside him, colorful houses on a hillside behind, the Haitian blue and red flag as the full background."),
    "panama": ("PANAMA", "EXACTLY ONE dancer in a magnificent white pollera dress with embroidered flowers gracefully balancing EXACTLY ONE classic football on her foot mid-dance, EXACTLY ONE tiny golden frog watching from a leaf, the Panamanian red-white-blue flag with stars as the full background."),
}

WC2B = {
    "czechia": ("CZECHIA", "EXACTLY ONE charming wooden marionette puppet of a footballer dangling from visible strings, caught mid-kick on EXACTLY ONE classic football, EXACTLY ONE ornate astronomical clock face behind, the Czech white-red-blue flag as the full background."),
    "austria": ("AUSTRIA", "EXACTLY ONE classical composer figure in a powdered wig and elegant coat conducting with a baton while EXACTLY ONE classic football bounces in rhythm on his shoe, musical notes swirling around, the Austrian red-white-red flag as the full background."),
    "sweden": ("SWEDEN", "EXACTLY ONE cheerful person in traditional folk dress kicking EXACTLY ONE classic football painted with red dala horse patterns, EXACTLY ONE big wooden red dala horse standing beside them, the Swedish blue flag with yellow cross as the full background."),
    "norway": ("NORWAY", "EXACTLY ONE hearty viking with a braided beard kicking EXACTLY ONE classic football from the bow of EXACTLY ONE wooden longship sailing through a narrow fjord with steep cliffs, the Norwegian red flag with blue and white cross as the full background."),
    "bosnia": ("BOSNIA", "EXACTLY ONE welcoming man pouring traditional coffee from a copper dzezva pot into a tiny cup with one hand while balancing EXACTLY ONE classic football on his knee, EXACTLY ONE stone arch bridge behind, the Bosnian blue and yellow flag with stars as the full background."),
    "turkiye": ("TURKIYE", "EXACTLY ONE whirling dervish in a flowing white robe and tall hat spinning gracefully while EXACTLY ONE classic football orbits around him in the air, ornate lanterns hanging above, the Turkish red flag with white crescent and star as the full background."),
    "qatar": ("QATAR", "EXACTLY ONE falconer in a flowing white thobe balancing EXACTLY ONE classic football on his foot while EXACTLY ONE majestic falcon perches on his gloved arm, golden desert dunes behind, the Qatari maroon and white serrated flag as the full background."),
    "saudi_arabia": ("SAUDI ARABIA", "EXACTLY ONE man in a white thobe and red-checkered shemagh performing a skillful juggle with EXACTLY ONE classic football while EXACTLY ONE camel watches with amusement beside him, desert dunes behind, the Saudi green flag as the full background."),
    "jordan": ("JORDAN", "EXACTLY ONE bedouin in a red-checkered keffiyeh kicking EXACTLY ONE classic football in front of the magnificent carved rose-stone facade of Petra, the Jordanian black-white-green flag with red triangle and star as the full background."),
    "iraq": ("IRAQ", "EXACTLY ONE musician playing an oud under EXACTLY TWO tall date palm trees while EXACTLY ONE classic football rests beside him, EXACTLY ONE ancient stepped ziggurat behind, the Iraqi red-white-black flag as the full background."),
    "iran": ("IRAN", "EXACTLY ONE joyful player doing a bicycle kick on EXACTLY ONE classic football while flying on EXACTLY ONE ornate Persian carpet with intricate patterns high above a mosque with turquoise dome, the Iranian green-white-red flag as the full background."),
    "uzbekistan": ("UZBEKISTAN", "EXACTLY ONE smiling man in a striped chapan robe and embroidered doppa cap balancing EXACTLY ONE classic football on his head while holding a steaming plate of plov, grand turquoise-tiled arches behind, the Uzbek blue-white-green flag as the full background."),
    "south_korea": ("SOUTH KOREA", "EXACTLY ONE taekwondo master in a white dobok with black belt performing a spectacular flying high kick on EXACTLY ONE classic football, EXACTLY TWO paper lanterns floating above, the South Korean white flag with red and blue taegeuk circle as the full background."),
    "australia": ("AUSTRALIA", "EXACTLY ONE athletic kangaroo bouncing high with EXACTLY ONE classic football tucked safely in its pouch, EXACTLY ONE koala cheering from a eucalyptus tree, red outback earth below, the Australian blue flag with stars as the full background."),
    "new_zealand": ("NEW ZEALAND", "EXACTLY ONE determined kiwi bird in a fierce haka stance with tiny wings raised in front of EXACTLY ONE classic football, EXACTLY ONE large silver fern leaf arching above it, the New Zealand blue flag with red stars as the full background."),
    "curacao": ("CURACAO", "EXACTLY ONE joyful dancer in bright carnival dress balancing EXACTLY ONE classic football on her head in front of a row of colorful dutch-colonial waterfront houses in pink, yellow and blue, the Curacao blue flag with yellow stripe and two stars as the full background."),
}

def build(series, desc, scenes):
    briefs = []
    for cid, (label, scene) in scenes.items():
        for sid, style in STYLES.items():
            briefs.append({
                "name": f"{cid} — {sid}",
                "_style_id": sid,
                "_expression_id": f"wc_{cid}" if series.startswith("zzz_zz") and "worldcup" in series else f"{cid}",
                "_idiom": label,
                "_canva_text": label,
                "ai_generation": {
                    "positive_prompt": scene + " " + style + SUFFIX,
                    "negative_prompt": NEG,
                    "cfg_scale": 4.0,
                    "tiling": False,
                    "seed_image_url": None,
                },
            })
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "series": series,
        "styles": list(STYLES.keys()),
        "description": desc,
        "platform": "redbubble",
        "total_briefs": len(briefs),
        "briefs": briefs,
    }

# A. Flood événements : id = event_concept
flood_scenes = {}
for eid, (label, concepts) in EVENTS.items():
    for cname, scene in concepts:
        flood_scenes[f"{eid}_{cname}"] = (label, scene)

files = [
    ("reports/redbubble/cahiers_des_charges_zzz_zza_events_flood_20260610_1800.json",
     build("zzz_zza_events_flood_v1",
           "Flood événements juin — 6 événements x 3 concepts x 20 styles. Images parlantes sans texte.",
           flood_scenes)),
    ("reports/redbubble/cahiers_des_charges_zzz_zzb_worldcup2026_wave2a_20260610_1801.json",
     build("zzz_zzb_worldcup2026_wave2a",
           "Coupe du Monde 2026 vague 2a — Afrique + Amériques : 16 nations x 20 styles, tradition x football.",
           WC2A)),
    ("reports/redbubble/cahiers_des_charges_zzz_zzc_worldcup2026_wave2b_20260610_1802.json",
     build("zzz_zzc_worldcup2026_wave2b",
           "Coupe du Monde 2026 vague 2b — Europe + Asie + Océanie : 16 nations x 20 styles, tradition x football.",
           WC2B)),
]

for path, cdc in files:
    with open(path, "w") as f:
        json.dump(cdc, f, ensure_ascii=False, indent=2)
    print(f"{path} : {cdc['total_briefs']} briefs")
