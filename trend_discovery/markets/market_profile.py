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


# ── Registre des profils ──────────────────────────────────────────────────────

PROFILES: Dict[str, MarketProfile] = {
    SPOONFLOWER.key: SPOONFLOWER,
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
