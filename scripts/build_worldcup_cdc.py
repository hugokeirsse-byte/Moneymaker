#!/usr/bin/env python3
"""
build_worldcup_cdc.py — génère le CDC Coupe du Monde 2026.
Chaque pays = 1 scène "tradition × football" (drapeau en fond), croisée avec
les 20 styles de base. Vague 1 : 16 nations à fort marché POD.
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

# Scènes "tradition × football" — lisibles sans texte, drapeau en fond
COUNTRIES = {
    "france": ("FRANCE", "EXACTLY ONE tall cheerful man wearing a black beret and a striped sailor shirt, kicking EXACTLY ONE classic football in mid-air while holding EXACTLY ONE long baguette of bread like a sword in his other hand, the French blue-white-red tricolor flag waving as the full background."),
    "england": ("ENGLAND", "EXACTLY ONE royal guard in a tall black bearskin hat and red uniform performing a dramatic overhead bicycle kick on EXACTLY ONE classic football while still holding EXACTLY ONE delicate cup of tea perfectly level in one hand, the English white flag with red Saint George cross as the full background."),
    "scotland": ("SCOTLAND", "EXACTLY ONE proud bagpiper in a tartan kilt heading EXACTLY ONE classic football with his forehead while still playing the bagpipes, EXACTLY TWO thistle flowers at his feet, the blue and white diagonal cross Scottish saltire flag as the full background."),
    "germany": ("GERMANY", "EXACTLY ONE jolly man in Bavarian lederhosen and alpine hat balancing EXACTLY ONE classic football on his head while raising EXACTLY ONE giant beer stein in one hand and holding EXACTLY ONE giant pretzel in the other, the German black-red-gold flag as the full background."),
    "spain": ("SPAIN", "EXACTLY ONE matador in an ornate embroidered jacket gracefully swirling his red cape while EXACTLY ONE classic football charges toward the cape like a little bull with motion lines, dramatic pose, the Spanish red-yellow-red flag as the full background."),
    "portugal": ("PORTUGAL", "EXACTLY ONE proud rooster of Barcelos with colorful decorated feathers doing a powerful kick on EXACTLY ONE classic football, standing on a pavement of blue and white azulejo tiles, the Portuguese green and red flag as the full background."),
    "netherlands": ("NETHERLANDS", "EXACTLY ONE cheerful person wearing wooden clogs riding a bicycle while dribbling EXACTLY ONE classic football alongside, passing EXACTLY ONE windmill and EXACTLY THREE tulips, the Dutch red-white-blue flag as the full background."),
    "belgium": ("BELGIUM", "EXACTLY ONE happy person juggling EXACTLY ONE classic football on one knee while holding EXACTLY ONE paper cone overflowing with golden fries in one hand and EXACTLY ONE waffle in the other, the Belgian black-yellow-red flag as the full background."),
    "switzerland": ("SWITZERLAND", "EXACTLY ONE alpine man in traditional dress playing a long alphorn on a mountain meadow while EXACTLY ONE classic football rolls into EXACTLY ONE giant wheel of Swiss cheese with holes like a goal, snowy peaks behind, the red Swiss flag with white cross as the full background."),
    "croatia": ("CROATIA", "EXACTLY ONE proud player wearing the iconic red and white checkerboard pattern jersey juggling EXACTLY ONE football also painted in red-white checkerboard pattern, sparkling blue Adriatic sea coastline behind him, the Croatian checkered flag as the full background."),
    "brazil": ("BRAZIL", "EXACTLY ONE joyful samba dancer in a feathered carnival costume doing skillful keepie-uppies with EXACTLY ONE classic football on a beach, EXACTLY ONE colorful toucan watching from a palm tree, the Brazilian green and yellow flag as the full background."),
    "argentina": ("ARGENTINA", "EXACTLY ONE gaucho in a wide-brimmed hat and poncho skillfully balancing EXACTLY ONE classic football on his boot while sipping EXACTLY ONE mate gourd with a metal straw, golden pampas grass around, the Argentine sky-blue and white flag with golden sun as the full background."),
    "mexico": ("MEXICO", "EXACTLY ONE mariachi musician in an embroidered charro suit and wide sombrero doing an elegant backheel kick on EXACTLY ONE classic football while playing the guitar, EXACTLY TWO cacti beside him, the Mexican green-white-red flag with eagle emblem as the full background."),
    "usa": ("USA", "EXACTLY ONE cowboy in a stetson hat and boots spinning a lasso above his head that catches EXACTLY ONE classic football in mid-flight, EXACTLY ONE bald eagle soaring overhead, the American stars and stripes flag as the full background."),
    "canada": ("CANADA", "EXACTLY ONE burly lumberjack in a red plaid shirt and knit cap balancing EXACTLY ONE classic football on the blade of a hockey stick, EXACTLY ONE moose watching curiously beside him, EXACTLY THREE maple leaves falling, the Canadian red and white maple leaf flag as the full background."),
    "japan": ("JAPAN", "EXACTLY ONE mighty sumo wrestler in a traditional mawashi gently heading EXACTLY ONE classic football with perfect concentration under EXACTLY ONE blooming cherry blossom tree, Mount Fuji silhouette behind, the Japanese white flag with red sun circle as the full background."),
}

SUFFIX = " Absolutely no text anywhere, no letters, no words, no writing, no numbers, no signature. Square sticker art, centered composition, clean background."
NEG = "text, letters, words, watermark, extra limbs, deformed anatomy, nudity, photorealistic, real flag photo"

briefs = []
for cid, (label, scene) in COUNTRIES.items():
    for sid, style in STYLES.items():
        briefs.append({
            "name": f"{cid} — {sid}",
            "_style_id": sid,
            "_expression_id": f"wc_{cid}",
            "_idiom": f"WORLD CUP 2026 — {label}",
            "_canva_text": label,
            "ai_generation": {
                "positive_prompt": scene + " " + style + SUFFIX,
                "negative_prompt": NEG,
                "cfg_scale": 4.0,
                "tiling": False,
                "seed_image_url": None,
            },
        })

cdc = {
    "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "series": "zzz_zz_worldcup2026_wave1",
    "styles": list(STYLES.keys()),
    "description": "Coupe du Monde 2026 (11 juin–19 juillet, USA/Canada/Mexique) — vague 1 : 16 nations à fort marché POD, scène tradition × football par pays, croisée avec les 20 styles de base. Aucun logo officiel, aucun texte.",
    "platform": "redbubble",
    "total_briefs": len(briefs),
    "briefs": briefs,
}

out = "reports/redbubble/cahiers_des_charges_zzz_zz_worldcup2026_wave1_20260610_1700.json"
with open(out, "w") as f:
    json.dump(cdc, f, ensure_ascii=False, indent=2)
print(f"{out} : {len(briefs)} briefs ({len(COUNTRIES)} pays x {len(STYLES)} styles)")
