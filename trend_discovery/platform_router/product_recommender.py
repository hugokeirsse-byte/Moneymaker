"""
Module 02 — Recommandation de Produits et Formats.

⚠️ HONNÊTETÉ DES DONNÉES :
Les recommandations produites ici reposent sur la connaissance STRUCTURELLE
des plateformes (quels produits portent bien quels styles). Ce ne sont pas des
prédictions de ventes en temps réel, mais des règles d'adéquation structurelle
produit ↔ style ↔ plateforme.
"""
import logging
from typing import Dict, List

from trend_discovery.platform_router.platform_profiles import (
    PLATFORM_PROFILES,
    PlatformProfile,
)

logger = logging.getLogger(__name__)


class ProductRecommender:
    """
    Détermine, pour une niche et une plateforme données, quels produits
    spécifiques sont structurellement adaptés ou à éviter, et quels formats
    de fichiers produire.
    """

    # Indices stylistiques déduits des mots-clés de la niche.
    # Chaque "trait" regroupe les mots-clés qui le déclenchent.
    _STYLE_TRAITS: Dict[str, List[str]] = {
        "seamless": ["seamless", "repeat", "pattern", "surface design", "textile", "fabric", "wallpaper",
                     "motif", "motifs", "répété", "tissu", "textile"],
        "botanical": ["botanical", "floral", "flower", "plant", "leaf", "nature",
                      "botanique", "florale", "floraux", "plantes", "herboristerie",
                      "champignons", "forêt", "tropical", "aquarelle", "nature"],
        "humor_text": ["humor", "funny", "meme", "slogan", "quote", "joke",
                       "humour", "drôle", "mème", "blague", "citation"],
        "pop_culture": ["pop culture", "fandom", "geek", "gaming", "trend",
                        "jeux", "geek", "fandom"],
        "svg_craft": ["svg", "cricut", "cut file", "sublimation", "craft", "maker",
                      "découpe", "sublimation"],
        "clipart": ["clipart", "png pack", "bundle", "illustration set",
                    "illustration", "illustrations"],
        "coloring": ["coloring", "line art", "coloring book", "activity book",
                     "coloriage", "colorier", "trait"],
        "wall_art": ["wall art", "art print", "poster", "minimalist", "abstract", "aesthetic",
                     "mural", "affiche", "minimaliste", "abstrait", "esthétique", "mandala",
                     "géométrique"],
        "event": ["wedding", "event", "invitation", "stationery", "monogram", "personalization",
                  "mariage", "événement", "papeterie", "monogramme", "personnalisation"],
    }

    # Produits recommandés / déconseillés par plateforme selon les traits détectés.
    # Format: platform_key -> trait -> {"recommended": [...], "discouraged": [...]}
    _PRODUCT_RULES: Dict[str, Dict[str, Dict[str, List[str]]]] = {
        "redbubble": {
            "seamless": {"recommended": ["tote bags", "leggings", "duvet covers", "scarves"],
                         "discouraged": ["t-shirts avec texte", "stickers"]},
            "botanical": {"recommended": ["tote bags", "posters", "duvet covers", "stickers"],
                          "discouraged": []},
            "humor_text": {"recommended": ["t-shirts", "stickers", "mugs"], "discouraged": []},
            "pop_culture": {"recommended": ["t-shirts", "stickers", "posters"], "discouraged": []},
        },
        "teepublic": {
            "humor_text": {"recommended": ["t-shirts", "stickers"], "discouraged": []},
            "pop_culture": {"recommended": ["t-shirts", "stickers", "accessoires"], "discouraged": []},
            "seamless": {"recommended": [], "discouraged": ["t-shirts", "stickers"]},
        },
        "zazzle": {
            "event": {"recommended": ["invitations", "papeterie", "cadeaux personnalisés"], "discouraged": []},
            "botanical": {"recommended": ["papeterie", "décoration", "cartes"], "discouraged": []},
            "humor_text": {"recommended": [], "discouraged": ["papeterie événementielle"]},
        },
        "society6": {
            "wall_art": {"recommended": ["art mural", "posters", "tapisseries"], "discouraged": []},
            "botanical": {"recommended": ["art mural", "posters", "coussins"], "discouraged": []},
            "humor_text": {"recommended": [], "discouraged": ["art mural"]},
        },
        "spoonflower": {
            "seamless": {"recommended": ["tissus", "papier peint"], "discouraged": []},
            "botanical": {"recommended": ["tissus", "papier peint", "serviettes"], "discouraged": []},
            "humor_text": {"recommended": [], "discouraged": ["tissus", "papier peint"]},
        },
        "etsy": {
            "svg_craft": {"recommended": ["fichiers SVG", "bundles SVG", "fichiers de découpe"], "discouraged": []},
            "clipart": {"recommended": ["packs PNG", "cliparts", "kits numériques"], "discouraged": []},
            "coloring": {"recommended": ["pages de coloriage imprimables"], "discouraged": []},
        },
        "creative_market": {
            "clipart": {"recommended": ["ressources graphiques", "packs d'illustrations"], "discouraged": []},
            "seamless": {"recommended": ["packs de motifs", "surface design"], "discouraged": []},
        },
        "design_bundles": {
            "svg_craft": {"recommended": ["bundles SVG", "fichiers de découpe"], "discouraged": []},
            "clipart": {"recommended": ["packs PNG", "bundles graphiques"], "discouraged": []},
        },
        "creative_fabrica": {
            "svg_craft": {"recommended": ["SVG", "fichiers de découpe", "polices"], "discouraged": []},
            "clipart": {"recommended": ["cliparts", "packs PNG"], "discouraged": []},
        },
        "gumroad": {
            "clipart": {"recommended": ["packs numériques premium", "asset packs"], "discouraged": []},
            "svg_craft": {"recommended": ["bundles de ressources"], "discouraged": []},
        },
        "payhip": {
            "clipart": {"recommended": ["téléchargements numériques", "packs de ressources"], "discouraged": []},
        },
        "amazon_kdp": {
            "coloring": {"recommended": ["livres de coloriage", "carnets d'activités"], "discouraged": []},
            "clipart": {"recommended": ["livres illustrés", "guides visuels"], "discouraged": []},
            "humor_text": {"recommended": [], "discouraged": ["livres de coloriage"]},
        },
        "b2b_direct": {
            "seamless": {"recommended": ["collections de motifs sous licence", "bibliothèques de surface design"],
                         "discouraged": []},
            "clipart": {"recommended": ["bibliothèques d'illustrations", "packs pro"], "discouraged": []},
            "botanical": {"recommended": ["collections de motifs", "licences commerciales"], "discouraged": []},
        },
    }

    def __init__(self, profiles: Dict[str, PlatformProfile] = None) -> None:
        self._profiles = profiles or PLATFORM_PROFILES

    # ── Détection des traits stylistiques ────────────────────────────────────
    def _detect_traits(self, niche_keywords: List[str]) -> List[str]:
        """
        Déduit les traits stylistiques d'une niche à partir de ses mots-clés.
        """
        blob = " ".join(str(k).lower() for k in (niche_keywords or []))
        traits: List[str] = []
        for trait, triggers in self._STYLE_TRAITS.items():
            if any(t in blob for t in triggers):
                traits.append(trait)
        return traits

    # ── Recommandation de produits ───────────────────────────────────────────
    def recommend_products(
        self,
        niche_keywords: List[str],
        platform_key: str,
    ) -> Dict[str, List[str]]:
        """
        Recommande des produits spécifiques pour une niche sur une plateforme.

        Returns:
            {"recommended": [...], "discouraged": [...]}
            En l'absence de règle spécifique, retombe sur la liste générique
            des produits du profil plateforme.
        """
        try:
            profile = self._profiles.get(platform_key)
            if profile is None:
                return {"recommended": [], "discouraged": []}

            traits = self._detect_traits(niche_keywords)
            recommended: List[str] = []
            discouraged: List[str] = []

            platform_rules = self._PRODUCT_RULES.get(platform_key, {})
            for trait in traits:
                rule = platform_rules.get(trait)
                if rule:
                    recommended.extend(rule.get("recommended", []))
                    discouraged.extend(rule.get("discouraged", []))

            # Fallback : aucun trait spécifique reconnu → produits génériques.
            if not recommended and not discouraged:
                recommended = list(profile.products)

            # Déduplication en préservant l'ordre.
            recommended = list(dict.fromkeys(recommended))
            discouraged = list(dict.fromkeys(discouraged))
            # Un produit ne peut pas être à la fois recommandé et déconseillé.
            recommended = [p for p in recommended if p not in discouraged]

            return {"recommended": recommended, "discouraged": discouraged}

        except Exception as exc:  # robustesse
            logger.error("Erreur recommend_products(%s): %s", platform_key, exc)
            return {"recommended": [], "discouraged": []}

    # ── Recommandation de formats de fichiers ────────────────────────────────
    def recommend_content_formats(self, niche_keywords: List[str]) -> List[str]:
        """
        Détermine les FORMATS DE FICHIERS à produire pour exploiter la niche
        sur l'ensemble des plateformes, avec leurs spécifications.

        Returns:
            Liste de chaînes décrivant chaque format + spécifications.
        """
        try:
            traits = self._detect_traits(niche_keywords)
            formats: List[str] = []

            if "seamless" in traits or "botanical" in traits:
                formats.append("Motif seamless PNG (300 DPI, ≥3600×3600 px, raccord parfait)")
            if "svg_craft" in traits:
                formats.append("SVG vectoriel (chemins propres, compatible Cricut/Silhouette)")
                formats.append("PNG transparent HD (300 DPI, ≥4000 px, pour sublimation)")
            if "clipart" in traits:
                formats.append("Pack PNG HD (300 DPI, fond transparent, 10-30 éléments)")
            if "coloring" in traits:
                formats.append("Pages de coloriage line art (PDF/PNG, noir & blanc, marges KDP)")
            if "wall_art" in traits:
                formats.append("Art print haute résolution (300 DPI, formats standards : A4/A3/18×24)")
            if "humor_text" in traits or "pop_culture" in traits:
                formats.append("Illustration/texte unique PNG transparent (300 DPI, ≥4500 px côté long)")
            if "event" in traits:
                formats.append("Template éditable (PNG/PDF) + version personnalisable")

            # Format de secours : toujours fournir un PNG HD exploitable.
            if not formats:
                formats.append("PNG HD transparent (300 DPI, ≥4000 px) — format polyvalent par défaut")

            return list(dict.fromkeys(formats))

        except Exception as exc:  # robustesse
            logger.error("Erreur recommend_content_formats: %s", exc)
            return ["PNG HD transparent (300 DPI) — format polyvalent par défaut"]
