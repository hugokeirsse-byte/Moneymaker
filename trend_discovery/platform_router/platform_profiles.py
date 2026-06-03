"""
Module 02 — Profils de Plateformes.

Ce fichier définit la connaissance STRUCTURELLE des plateformes de monétisation
(POD, produits numériques, édition, B2B).

⚠️ HONNÊTETÉ DES DONNÉES :
Les profils ci-dessous décrivent les CARACTÉRISTIQUES STRUCTURELLES connues de
chaque plateforme (quels produits elle vend, quel public elle attire, quels
styles y fonctionnent, son niveau de prix et de saturation généralement observé).

Ce ne sont PAS des mesures de marché en temps réel. Les scores de compatibilité
calculés à partir de ces profils sont des "scores de compatibilité structurelle".
Ils doivent ensuite être PONDÉRÉS par les vraies données de demande et de
compétition fournies par le Module 01 (OpportunityScore).
"""
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class PlatformProfile:
    """
    Profil structurel d'une plateforme de monétisation.

    Tous les attributs décrivent des connaissances structurelles stables
    (le type de produits vendus, le public, les styles qui fonctionnent),
    pas des métriques de marché live.
    """

    key: str                              # identifiant interne (snake_case)
    name: str                             # nom lisible
    category: str                         # "pod" / "digital" / "publishing" / "b2b"
    products: List[str] = field(default_factory=list)
    audience: List[str] = field(default_factory=list)
    best_for_styles: List[str] = field(default_factory=list)
    weak_for_styles: List[str] = field(default_factory=list)
    preferred_content_types: List[str] = field(default_factory=list)
    avg_price_point: str = "medium"       # "low" / "medium" / "high"
    competition_level: str = "medium"     # "low" / "medium" / "high" / "very_high"
    reusability_factor: float = 0.5       # 0-1 : déclinabilité d'un même design
    monetization_model: str = "royalty"   # "royalty" / "direct_sale" / "subscription" / "license"
    effort_to_publish: str = "medium"     # "low" / "medium" / "high"

    def summary(self) -> str:
        """Résumé lisible d'une ligne du profil."""
        return (
            f"{self.name} [{self.category}] — prix={self.avg_price_point}, "
            f"concurrence={self.competition_level}, "
            f"réutilisabilité={self.reusability_factor:.2f}, "
            f"modèle={self.monetization_model}"
        )


# ─────────────────────────────────────────────────────────────────────────────
# DICTIONNAIRE DES PROFILS DE PLATEFORMES
# Connaissance structurelle uniquement (cf. avertissement en tête de fichier).
# ─────────────────────────────────────────────────────────────────────────────

PLATFORM_PROFILES: Dict[str, PlatformProfile] = {
    # ── PRINT-ON-DEMAND ──────────────────────────────────────────────────────
    "redbubble": PlatformProfile(
        key="redbubble",
        name="Redbubble",
        category="pod",
        products=["t-shirts", "stickers", "posters", "mugs", "accessoires"],
        audience=["grand public", "humour", "pop culture", "illustrations"],
        best_for_styles=[
            "humor text", "pop culture", "single illustration", "funny",
            "meme", "fandom", "trendy slogan", "bold graphic",
        ],
        weak_for_styles=["seamless", "repeat pattern", "surface design", "subtle pattern"],
        preferred_content_types=["single_illustration", "text_design", "sticker", "png"],
        avg_price_point="low",
        competition_level="very_high",
        reusability_factor=0.55,
        monetization_model="royalty",
        effort_to_publish="low",
    ),
    "teepublic": PlatformProfile(
        key="teepublic",
        name="TeePublic",
        category="pod",
        products=["t-shirts", "stickers", "accessoires"],
        audience=["geek", "humour", "culture internet"],
        best_for_styles=[
            "humor text", "pop culture", "meme", "geek", "gaming",
            "funny", "fandom", "internet culture",
        ],
        weak_for_styles=["seamless", "repeat pattern", "surface design", "botanical"],
        preferred_content_types=["single_illustration", "text_design", "sticker", "png"],
        avg_price_point="low",
        competition_level="high",
        reusability_factor=0.5,
        monetization_model="royalty",
        effort_to_publish="low",
    ),
    "zazzle": PlatformProfile(
        key="zazzle",
        name="Zazzle",
        category="pod",
        products=["papeterie", "décoration", "cadeaux"],
        audience=["personnalisation", "événementiel"],
        best_for_styles=[
            "personalization", "wedding", "event", "stationery",
            "elegant", "celebration", "monogram", "invitation",
        ],
        weak_for_styles=["meme", "edgy humor", "complex illustration"],
        preferred_content_types=["template", "single_illustration", "pattern", "png"],
        avg_price_point="medium",
        competition_level="high",
        reusability_factor=0.6,
        monetization_model="royalty",
        effort_to_publish="medium",
    ),
    "society6": PlatformProfile(
        key="society6",
        name="Society6",
        category="pod",
        products=["décoration", "posters", "art mural"],
        audience=["design", "décoration intérieure"],
        best_for_styles=[
            "art print", "wall art", "aesthetic", "minimalist", "abstract",
            "botanical", "boho", "interior design", "fine art",
        ],
        weak_for_styles=["humor text", "meme", "low-res graphic"],
        preferred_content_types=["art_print", "single_illustration", "pattern", "png"],
        avg_price_point="medium",
        competition_level="high",
        reusability_factor=0.6,
        monetization_model="royalty",
        effort_to_publish="medium",
    ),
    "spoonflower": PlatformProfile(
        key="spoonflower",
        name="Spoonflower",
        category="pod",
        products=["tissus", "papier peint", "décoration textile"],
        audience=["couture", "créateurs", "décoration"],
        best_for_styles=[
            "seamless", "repeat pattern", "surface design", "botanical",
            "floral", "textile", "fabric", "wallpaper",
        ],
        weak_for_styles=["humor text", "pop culture", "single illustration", "meme"],
        preferred_content_types=["seamless_pattern", "repeat_pattern", "surface_design"],
        avg_price_point="high",
        competition_level="medium",
        reusability_factor=0.9,
        monetization_model="royalty",
        effort_to_publish="medium",
    ),

    # ── PRODUITS NUMÉRIQUES ──────────────────────────────────────────────────
    "etsy": PlatformProfile(
        key="etsy",
        name="Etsy",
        category="digital",
        products=["PNG", "SVG", "cliparts", "motifs", "templates", "packs numériques"],
        audience=["créateurs", "artisans", "PME"],
        best_for_styles=[
            "clipart", "svg", "png pack", "bundle", "digital download",
            "craft", "cricut", "sublimation", "printable",
        ],
        weak_for_styles=["single low-value graphic"],
        preferred_content_types=["png_pack", "svg", "clipart_set", "template", "digital_bundle"],
        avg_price_point="medium",
        competition_level="very_high",
        reusability_factor=0.85,
        monetization_model="direct_sale",
        effort_to_publish="medium",
    ),
    "creative_market": PlatformProfile(
        key="creative_market",
        name="Creative Market",
        category="digital",
        products=["ressources graphiques", "polices", "illustrations", "motifs"],
        audience=["designers", "agences", "pros"],
        best_for_styles=[
            "graphic resource", "font", "professional illustration", "pattern",
            "surface design", "premium bundle", "texture", "mockup",
        ],
        weak_for_styles=["meme", "low-effort clipart"],
        preferred_content_types=["graphic_resource", "font", "pattern", "illustration_set", "png_pack"],
        avg_price_point="high",
        competition_level="medium",
        reusability_factor=0.8,
        monetization_model="direct_sale",
        effort_to_publish="high",
    ),
    "design_bundles": PlatformProfile(
        key="design_bundles",
        name="Design Bundles",
        category="digital",
        products=["SVG", "PNG", "bundles"],
        audience=["créateurs Cricut", "makers"],
        best_for_styles=[
            "svg", "cricut", "cut file", "bundle", "craft",
            "sublimation", "png pack", "maker",
        ],
        weak_for_styles=["fine art", "complex painterly illustration"],
        preferred_content_types=["svg", "png_pack", "digital_bundle", "cut_file"],
        avg_price_point="medium",
        competition_level="high",
        reusability_factor=0.85,
        monetization_model="direct_sale",
        effort_to_publish="medium",
    ),
    "creative_fabrica": PlatformProfile(
        key="creative_fabrica",
        name="Creative Fabrica",
        category="digital",
        products=["SVG", "cliparts", "ressources", "polices"],
        audience=["POD", "créateurs numériques"],
        best_for_styles=[
            "svg", "clipart", "font", "cut file", "craft",
            "cricut", "embroidery", "png pack",
        ],
        weak_for_styles=["fine art print"],
        preferred_content_types=["svg", "clipart_set", "font", "png_pack", "digital_bundle"],
        avg_price_point="medium",
        competition_level="high",
        reusability_factor=0.85,
        monetization_model="subscription",
        effort_to_publish="medium",
    ),
    "gumroad": PlatformProfile(
        key="gumroad",
        name="Gumroad",
        category="digital",
        products=["packs numériques", "ressources", "formations"],
        audience=["créateurs indépendants"],
        best_for_styles=[
            "digital bundle", "resource pack", "course", "asset pack",
            "premium pack", "indie", "niche audience",
        ],
        weak_for_styles=["single low-value item"],
        preferred_content_types=["digital_bundle", "png_pack", "resource_pack", "course"],
        avg_price_point="medium",
        competition_level="low",
        reusability_factor=0.75,
        monetization_model="direct_sale",
        effort_to_publish="low",
    ),
    "payhip": PlatformProfile(
        key="payhip",
        name="Payhip",
        category="digital",
        products=["produits numériques", "téléchargements"],
        audience=["créateurs", "indépendants"],
        best_for_styles=[
            "digital download", "resource pack", "ebook", "asset pack",
            "indie", "bundle",
        ],
        weak_for_styles=["single low-value item"],
        preferred_content_types=["digital_bundle", "png_pack", "resource_pack", "ebook"],
        avg_price_point="medium",
        competition_level="low",
        reusability_factor=0.75,
        monetization_model="direct_sale",
        effort_to_publish="low",
    ),

    # ── ÉDITION ──────────────────────────────────────────────────────────────
    "amazon_kdp": PlatformProfile(
        key="amazon_kdp",
        name="Amazon KDP",
        category="publishing",
        products=["livres illustrés", "livres de coloriage", "guides visuels", "ouvrages spécialisés"],
        audience=["lecteurs", "collectionneurs", "passionnés"],
        best_for_styles=[
            "coloring", "illustration set", "line art", "activity book",
            "guide", "educational", "themed collection", "book interior",
        ],
        weak_for_styles=["single sticker", "seamless pattern", "meme"],
        preferred_content_types=["coloring_page", "line_art", "illustration_set", "book_interior"],
        avg_price_point="medium",
        competition_level="high",
        reusability_factor=0.3,
        monetization_model="royalty",
        effort_to_publish="high",
    ),

    # ── B2B ──────────────────────────────────────────────────────────────────
    "b2b_direct": PlatformProfile(
        key="b2b_direct",
        name="Vente B2B Directe",
        category="b2b",
        products=[
            "bibliothèques d'illustrations", "collections de motifs",
            "packs pro", "licences commerciales",
        ],
        audience=["marques", "éditeurs", "agences", "fabricants"],
        best_for_styles=[
            "illustration library", "pattern collection", "professional pack",
            "licensable", "cohesive collection", "surface design", "premium",
        ],
        weak_for_styles=["single low-value graphic", "meme"],
        preferred_content_types=["illustration_set", "pattern", "surface_design", "licensable_collection"],
        avg_price_point="high",
        competition_level="low",
        reusability_factor=0.95,
        monetization_model="license",
        effort_to_publish="high",
    ),
}


def get_profile(platform_key: str) -> PlatformProfile:
    """
    Retourne le profil d'une plateforme.

    Lève KeyError si la plateforme est inconnue ; les appelants doivent
    soit valider la clé via `all_platform_keys()`, soit gérer l'exception.
    """
    return PLATFORM_PROFILES[platform_key]


def all_platform_keys() -> List[str]:
    """Liste de toutes les clés de plateformes disponibles."""
    return list(PLATFORM_PROFILES.keys())
