"""
MarketProfile — description déclarative d'un marché POD.

C'est la pièce maîtresse de la scalabilité : tout le savoir spécifique à une
plateforme (produits, acheteurs, signaux de recherche, contraintes d'export)
est encapsulé ici. Le moteur (prompt Gemini, validation d'opportunité, briefs)
lit ce profil au lieu de coder en dur les connaissances Spoonflower.

Ajouter un nouveau marché = ajouter un MarketProfile dans PROFILES.
Aucun autre fichier du moteur n'a besoin d'être modifié.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Dict, List

logger = logging.getLogger(__name__)


@dataclass
class MarketProfile:
    """
    Décrit un marché POD (place de marché) de façon agnostique.

    Champs :
        key                : identifiant court (ex: "spoonflower")
        display_name       : nom affiché et injecté dans les prompts Gemini
        platform_description : phrase décrivant la plateforme pour le prompt Gemini
        product_types      : produits vendus (ex: tissu, papier peint)
        buyer_segments     : segments d'acheteurs réels (ex: quilteurs, couturiers)
        research_signals   : signaux SPÉCIFIQUES à rechercher (ex: Design Challenges)
        excluded_generic   : catégories saturées/génériques à éviter
        output_format      : contraintes d'export {file, dpi, min_px, color_profile, max_mb}
        repeat_required    : True si un motif seamless (tuile parfaite) est requis
        niche_count        : nombre de niches à découvrir par défaut
    """

    key: str
    display_name: str
    platform_description: str
    product_types: List[str] = field(default_factory=list)
    buyer_segments: List[str] = field(default_factory=list)
    research_signals: List[str] = field(default_factory=list)
    excluded_generic: List[str] = field(default_factory=list)
    output_format: dict = field(default_factory=dict)
    repeat_required: bool = True
    niche_count: int = 12
    crossover_count: int = 4  # niches "crossover gap" ultra-nichées en plus des niche_count


# ── Profil Spoonflower (savoir actuellement codé en dur, désormais déclaratif) ─

SPOONFLOWER = MarketProfile(
    key="spoonflower",
    display_name="Spoonflower fabric design",
    platform_description=(
        "Spoonflower, the print-on-demand surface design marketplace where "
        "independent designers sell seamless repeating patterns printed on "
        "fabric, wallpaper, gift wrap and home decor"
    ),
    product_types=[
        "quilting cotton",
        "apparel fabric",
        "wallpaper",
        "gift wrap",
        "home decor (curtains, table linens, bedding)",
        "baby / nursery fabric",
    ],
    buyer_segments=[
        "quilters making baby blankets and quilts",
        "apparel sewists making dresses and clothing",
        "wallpaper home decorators",
        "nursery and baby room decorators",
    ],
    research_signals=[
        "recent Spoonflower Design Challenge themes and winners (they reveal what the marketplace is pushing right now)",
        "Spoonflower trending tags, bestselling fabric collections, 'popular' and 'newest' sorts",
        "what Spoonflower buyers actually make: quilting cotton, apparel, baby/nursery, home decor, wallpaper, table linens",
        "Pinterest / TikTok / interior-design trend reports cross-referenced with what is still UNDERSERVED on Spoonflower",
    ],
    excluded_generic=[
        "plain generic florals",
        "generic cute cats/animals",
        "basic rainbows",
        "plain boho",
        "generic Christmas",
    ],
    output_format={
        "file": "PNG",
        "dpi": 300,
        "min_px": 4500,        # 4500x4500 px = 15" x 15" à 300 DPI
        "color_profile": "sRGB",
        "max_mb": 40,
    },
    repeat_required=True,
    niche_count=12,
)


# ── Profil Redbubble ─────────────────────────────────────────────────────────

REDBUBBLE = MarketProfile(
    key="redbubble",
    display_name="Redbubble print-on-demand",
    platform_description=(
        "Redbubble, the global print-on-demand marketplace where independent artists "
        "sell standalone graphic designs printed on t-shirts, stickers, phone cases, "
        "mugs, tote bags, art prints, throw pillows and more"
    ),
    product_types=[
        "t-shirts and hoodies",
        "stickers (die-cut, transparent, holographic)",
        "phone cases",
        "mugs and travel mugs",
        "tote bags",
        "art prints and posters",
        "throw pillows",
        "notebooks and journals",
    ],
    buyer_segments=[
        "hobbyist communities with strong identity (mycologists, birders, ham radio operators, mechanical keyboard builders, sourdough bakers, fountain pen collectors, cichlid keepers, film photographers)",
        "skilled trade professionals proud of craft identity (electricians, welders, machinists, arborists, farriers, glassblowers)",
        "niche fandom and gaming communities (specific game/anime that have <5k Redbubble designs)",
        "academic and research communities (PhD culture, specific scientific disciplines, field researchers)",
        "alternative sports and outdoor communities (ultralight backpacking, open-water swimming, trail running, competitive archery, roller derby)",
        "indie art and maker culture (risograph printers, zine makers, letterpress, bookbinders, natural dyers)",
        "crossover buyers who combine two identities and can't find merch that speaks to both",
    ],
    research_signals=[
        # CHECK A — Redbubble competition mapping
        "Search Redbubble for the community's core keyword — record result count and assess quality (are results generic or community-authentic?)",
        # CHECK B — Reddit purchase intent
        "Search Reddit in the community's primary subreddit for posts mentioning 'merch', 'sticker', 'shirt', 'I wish someone made' — record subreddit size and any direct merch request threads",
        # CHECK C — Etsy demand crossover
        "Search Etsy for '[community keyword] sticker' and '[community keyword] shirt' — record listing count and check for recent sales evidence ('X sold in last 24h')",
        # CHECK D — TikTok / social trend velocity
        "Search TikTok for the community's main hashtag(s) — record view counts; check for viral community content posted in the last 30 days",
        # CHECK E — Pinterest visual identity
        "Search Pinterest for '[community] aesthetic' or '[community] art' — confirm the community has a distinct visual language that would translate to sticker/shirt design",
        # Bonus signals
        "Check r/redbubble and r/printondemand for buyer requests and underserved niche discussions from the last 3 months",
        "Search Google Trends for the community keyword in the last 12 months — check if interest is rising, stable, or declining",
    ],
    excluded_generic=[
        "generic inspirational quotes",
        "plain gradient backgrounds",
        "stock photo style",
        "corporate clipart",
        "generic 'live laugh love' style",
        "basic rainbow pride (oversaturated, >100k results on Redbubble)",
        "generic cat/dog without community-specific context",
        "anxiety / mental health without specific community hook (>200k results)",
        "axolotl / capybara / frog / void cat (market exhausted)",
        "skeleton / skull without specific niche context (>300k results)",
        "cottagecore (saturated), dark academia (saturated), witchy (saturated)",
    ],
    output_format={
        "file": "PNG",
        "dpi": 300,
        "min_px": 4500,
        "color_profile": "sRGB",
        "max_mb": 40,
        "background": "white",  # white bg for most products; transparent option for stickers
    },
    repeat_required=False,
    niche_count=14,
    crossover_count=2,
)


# ── Profil Adobe Stock ───────────────────────────────────────────────────────

ADOBE_STOCK = MarketProfile(
    key="adobe_stock",
    display_name="Adobe Stock digital assets",
    platform_description=(
        "Adobe Stock, the subscription stock asset marketplace used by designers, "
        "agencies, and marketers worldwide for commercially licensable photos, "
        "vectors, illustrations, patterns, and templates"
    ),
    product_types=[
        "seamless vector patterns",
        "PNG texture tiles",
        "surface design patterns",
        "botanical illustration sets",
        "geometric pattern collections",
        "nature-inspired texture bundles",
        "decorative background patterns",
    ],
    buyer_segments=[
        "graphic designers and art directors buying for client projects",
        "interior design studios sourcing patterns for wallpaper and fabric concepts",
        "product packagers sourcing wrapping and label designs",
        "self-publishing authors and Etsy sellers making digital products",
        "small business owners creating merchandise and branded materials",
    ],
    research_signals=[
        "Adobe Stock 'Trending' and 'Popular' collections in patterns and illustrations right now",
        "Shutterstock and iStock trending searches — strong proxy for commercial Adobe buyer demand",
        "Creative Market bestselling pattern packs and asset bundles",
        "Freepik premium trending resources (fast leading indicator of commercial demand)",
        "Google Trends for '[theme] pattern vector', '[theme] seamless texture', '[theme] background tile'",
        "Canva trending templates and design element requests — shows what marketers need",
    ],
    excluded_generic=[
        "generic rainbow gradients",
        "basic polka dots or stripes without distinct theme",
        "overused chevron or herringbone",
        "plain watercolor wash without identity",
        "generic geometric without a specific visual theme",
    ],
    output_format={
        "file": "PNG",
        "dpi": 300,
        "min_px": 4500,
        "color_profile": "sRGB",
        "max_mb": 40,
    },
    repeat_required=True,
    niche_count=12,
    crossover_count=2,
)


# ── Profil Etsy Digital Downloads ────────────────────────────────────────────

ETSY = MarketProfile(
    key="etsy",
    display_name="Etsy digital download bundles",
    platform_description=(
        "Etsy, the handmade and digital goods marketplace where sellers offer "
        "instant-download digital files: seamless pattern bundles, clipart packs, "
        "digital paper, Cricut-ready SVG files, and surface design asset bundles"
    ),
    product_types=[
        "seamless pattern PNG bundle (10-20 coordinating files per pack)",
        "digital paper pack for scrapbooking and junk journaling",
        "printable wall art set (A4/Letter/square)",
        "fabric pattern bundle (ready to upload to Spoonflower/Printify)",
        "Cricut and Silhouette SVG clipart cut file bundle",
        "digital planner and journal insert pages",
    ],
    buyer_segments=[
        "Cricut and Silhouette craft machine owners making cards, shirts, decals, mugs",
        "Etsy small business owners sourcing patterns for their own print-on-demand products",
        "scrapbookers and junk journalists looking for coordinating digital paper packs",
        "sewing and fabric creators sourcing pattern bundles",
        "teachers and activity makers creating printable classroom and party materials",
    ],
    research_signals=[
        "Etsy search autocomplete for 'seamless pattern bundle', 'digital paper pack', 'clipart bundle PNG'",
        "Etsy Digital Downloads bestsellers by category: craft supplies > patterns > digital",
        "Pinterest boards for 'digital download Etsy', 'scrapbook digital paper', 'Cricut SVG bundle 2025'",
        "Creative Fabrica, Design Bundles, Momeant trending product categories",
        "TikTok #cricut and #digitaldownload — what Cricut crafters are making and searching for",
        "Spoonflower Design Challenge themes — these buyers often want matching digital packs",
    ],
    excluded_generic=[
        "basic polka dots and stripes (extremely crowded, zero differentiation)",
        "generic watercolor florals (millions of listings, race to zero price)",
        "plain nursery animals without strong aesthetic identity",
        "generic chevrons and herringbone",
        "basic 'rustic' burlap or wood texture",
    ],
    output_format={
        "file": "PNG",
        "dpi": 300,
        "min_px": 4500,
        "color_profile": "sRGB",
        "max_mb": 40,
    },
    repeat_required=True,
    niche_count=12,
    crossover_count=2,
)


# ── Registre des profils ──────────────────────────────────────────────────────

PROFILES: Dict[str, MarketProfile] = {
    SPOONFLOWER.key: SPOONFLOWER,
    REDBUBBLE.key: REDBUBBLE,
    ADOBE_STOCK.key: ADOBE_STOCK,
    ETSY.key: ETSY,
}


def get_profile(key: str) -> MarketProfile:
    """
    Retourne le MarketProfile pour la clé donnée.

    Par défaut (clé vide/inconnue), retourne SPOONFLOWER en journalisant
    clairement le repli — le moteur ne doit jamais planter sur un marché inconnu.
    """
    if not key:
        return SPOONFLOWER
    profile = PROFILES.get(key.lower().strip())
    if profile is None:
        logger.warning(
            "[markets] marché '%s' inconnu — repli sur '%s'. Marchés connus : %s",
            key, SPOONFLOWER.key, ", ".join(PROFILES.keys()),
        )
        return SPOONFLOWER
    return profile
