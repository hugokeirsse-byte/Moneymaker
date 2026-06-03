"""
Module 02 — Matrice de Compatibilité Niche × Plateforme.

⚠️ HONNÊTETÉ DES DONNÉES :
Le score renvoyé par `score_niche_platform` est un SCORE DE COMPATIBILITÉ
STRUCTURELLE (0-100). Il mesure à quel point les caractéristiques stylistiques
d'une niche correspondent au profil structurel d'une plateforme
(best_for_styles / weak_for_styles / preferred_content_types).

Ce N'EST PAS une mesure de marché en temps réel ni une prédiction de ventes.
Il doit être pondéré ensuite par les vraies données de demande / compétition
issues du Module 01 (OpportunityScore).
"""
import logging
from typing import Dict, List

from trend_discovery.platform_router.platform_profiles import (
    PLATFORM_PROFILES,
    PlatformProfile,
)

logger = logging.getLogger(__name__)


class CompatibilityMatrix:
    """
    Calcule un score de compatibilité structurelle entre une niche
    (décrite par des mots-clés + un chemin d'arbre) et une plateforme.

    La logique est entièrement basée sur la connaissance structurelle des
    profils de plateformes : ce sont des affinités stylistiques connues,
    pas des données de marché live.
    """

    # Matrice de mots-clés → affinités plateforme.
    # Chaque entrée associe un mot-clé caractéristique d'une niche à des
    # bonus/malus structurels par plateforme.
    # Les valeurs sont des ajustements (-/+) appliqués au score de base.
    _KEYWORD_AFFINITIES: Dict[str, Dict[str, float]] = {
        # Surface / motifs répétés → textile, surface design, B2B
        "seamless": {"spoonflower": 35, "creative_market": 20, "society6": 12,
                     "b2b_direct": 18, "redbubble": -20, "teepublic": -25, "amazon_kdp": -20},
        "pattern": {"spoonflower": 30, "creative_market": 18, "society6": 10,
                    "b2b_direct": 15, "zazzle": 8, "redbubble": -10, "teepublic": -15},
        "repeat": {"spoonflower": 28, "creative_market": 15, "b2b_direct": 12},
        "surface design": {"spoonflower": 32, "creative_market": 22, "b2b_direct": 20},
        "botanical": {"spoonflower": 28, "society6": 20, "creative_market": 12,
                      "b2b_direct": 12, "redbubble": -8},
        "floral": {"spoonflower": 28, "society6": 18, "creative_market": 12,
                   "zazzle": 10, "b2b_direct": 10},
        "textile": {"spoonflower": 30, "b2b_direct": 12},
        "fabric": {"spoonflower": 30, "b2b_direct": 12},
        "wallpaper": {"spoonflower": 28, "society6": 10, "b2b_direct": 10},

        # Humour / pop culture → POD t-shirts/stickers
        "humor": {"redbubble": 30, "teepublic": 32, "spoonflower": -25,
                  "society6": -20, "b2b_direct": -20, "creative_market": -15},
        "funny": {"redbubble": 28, "teepublic": 30, "spoonflower": -25, "society6": -18},
        "meme": {"teepublic": 32, "redbubble": 28, "spoonflower": -30,
                 "society6": -25, "b2b_direct": -25, "amazon_kdp": -20},
        "pop culture": {"redbubble": 30, "teepublic": 30, "spoonflower": -25,
                        "b2b_direct": -15},
        "geek": {"teepublic": 30, "redbubble": 22},
        "gaming": {"teepublic": 28, "redbubble": 22},
        "fandom": {"teepublic": 28, "redbubble": 26},
        "slogan": {"redbubble": 24, "teepublic": 24, "zazzle": 8},
        "quote": {"redbubble": 20, "teepublic": 20, "zazzle": 10, "amazon_kdp": 6},

        # Stickers
        "sticker": {"redbubble": 26, "teepublic": 26, "creative_fabrica": 8},

        # SVG / Cricut / makers
        "svg": {"design_bundles": 32, "creative_fabrica": 30, "etsy": 22,
                "creative_market": 12, "spoonflower": -15, "amazon_kdp": -10},
        "cricut": {"design_bundles": 34, "creative_fabrica": 30, "etsy": 22},
        "cut file": {"design_bundles": 32, "creative_fabrica": 30, "etsy": 18},
        "sublimation": {"etsy": 26, "design_bundles": 24, "creative_fabrica": 22},
        "clipart": {"etsy": 26, "creative_fabrica": 24, "creative_market": 16,
                    "design_bundles": 16},
        "png pack": {"etsy": 24, "creative_market": 20, "design_bundles": 18,
                     "creative_fabrica": 18, "gumroad": 16, "payhip": 14},
        "bundle": {"design_bundles": 24, "etsy": 20, "creative_market": 18,
                   "gumroad": 18, "creative_fabrica": 16},
        "printable": {"etsy": 24, "gumroad": 14, "payhip": 14},
        "template": {"etsy": 22, "creative_market": 16, "zazzle": 16},
        "font": {"creative_market": 28, "creative_fabrica": 24, "design_bundles": 14},

        # Édition / coloriage / livres
        "coloring": {"amazon_kdp": 38, "etsy": 14, "spoonflower": -20, "redbubble": -15},
        "coloring book": {"amazon_kdp": 40, "etsy": 12},
        "line art": {"amazon_kdp": 26, "etsy": 12, "creative_fabrica": 10},
        "illustration set": {"amazon_kdp": 22, "creative_market": 22,
                             "b2b_direct": 24, "etsy": 14},
        "activity book": {"amazon_kdp": 32},
        "guide": {"amazon_kdp": 24},
        "educational": {"amazon_kdp": 22, "etsy": 8},
        "book": {"amazon_kdp": 26},

        # Décoration / art mural
        "wall art": {"society6": 30, "etsy": 12, "creative_market": 8},
        "art print": {"society6": 28, "etsy": 10},
        "poster": {"society6": 22, "redbubble": 16},
        "minimalist": {"society6": 22, "creative_market": 12},
        "abstract": {"society6": 22, "spoonflower": 10, "creative_market": 12},
        "boho": {"society6": 20, "spoonflower": 16, "etsy": 12},
        "aesthetic": {"society6": 18, "redbubble": 12},
        "interior": {"society6": 22, "spoonflower": 18, "b2b_direct": 10},

        # Événementiel / personnalisation
        "wedding": {"zazzle": 34, "etsy": 16, "creative_market": 8},
        "event": {"zazzle": 28},
        "invitation": {"zazzle": 30, "etsy": 14},
        "personalization": {"zazzle": 30},
        "monogram": {"zazzle": 24, "creative_fabrica": 12},
        "stationery": {"zazzle": 26, "etsy": 12},

        # B2B / licences / collections pro
        "collection": {"b2b_direct": 22, "creative_market": 16, "spoonflower": 10},
        "library": {"b2b_direct": 28, "creative_market": 14},
        "license": {"b2b_direct": 30},
        "commercial": {"b2b_direct": 22},
        "premium": {"creative_market": 18, "b2b_direct": 18, "gumroad": 10},
        "professional": {"creative_market": 20, "b2b_direct": 22},

        # ── Équivalents français (niches normalisées en FR) ───────────────────
        "botanique": {"spoonflower": 28, "society6": 20, "creative_market": 12,
                      "b2b_direct": 12, "redbubble": -8},
        "florale": {"spoonflower": 28, "society6": 18, "creative_market": 12,
                    "zazzle": 10, "b2b_direct": 10},
        "floraux": {"spoonflower": 28, "society6": 18, "creative_market": 12,
                    "zazzle": 10, "b2b_direct": 10},
        "motif": {"spoonflower": 30, "creative_market": 18, "society6": 10,
                  "b2b_direct": 15, "zazzle": 8, "redbubble": -10, "teepublic": -15},
        "motifs": {"spoonflower": 30, "creative_market": 18, "society6": 10,
                   "b2b_direct": 15, "zazzle": 8, "redbubble": -10, "teepublic": -15},
        "herboristerie": {"spoonflower": 26, "society6": 18, "creative_market": 14,
                          "b2b_direct": 14, "redbubble": -8},
        "tissu": {"spoonflower": 30, "b2b_direct": 12},
        "textile": {"spoonflower": 30, "b2b_direct": 12},
        "humour": {"redbubble": 30, "teepublic": 32, "spoonflower": -25,
                   "society6": -20, "b2b_direct": -20, "creative_market": -15},
        "drôle": {"redbubble": 28, "teepublic": 30, "spoonflower": -25, "society6": -18},
        "mème": {"teepublic": 32, "redbubble": 28, "spoonflower": -30,
                 "society6": -25, "b2b_direct": -25, "amazon_kdp": -20},
        "mariage": {"zazzle": 34, "etsy": 16, "creative_market": 8},
        "invitation": {"zazzle": 30, "etsy": 14},
        "coloriage": {"amazon_kdp": 38, "etsy": 14, "spoonflower": -20, "redbubble": -15},
        "affiche": {"society6": 22, "redbubble": 16},
        "minimaliste": {"society6": 22, "creative_market": 12},
        "abstrait": {"society6": 22, "spoonflower": 10, "creative_market": 12},
        "géométrique": {"society6": 18, "spoonflower": 12, "creative_market": 10,
                        "b2b_direct": 8},
        "découpe": {"design_bundles": 32, "creative_fabrica": 30, "etsy": 18},
        "licence": {"b2b_direct": 30},
        "licences": {"b2b_direct": 28},
        "collections": {"b2b_direct": 22, "creative_market": 16, "spoonflower": 10},
        "bibliothèque": {"b2b_direct": 28, "creative_market": 14},
    }

    # Score de base structurel par catégorie de plateforme : reflète
    # l'accessibilité générale (un design "neutre" a une compatibilité moyenne).
    _BASE_SCORE = 45.0

    def __init__(self, profiles: Dict[str, PlatformProfile] = None) -> None:
        self._profiles = profiles or PLATFORM_PROFILES

    # ── Utilitaires internes ────────────────────────────────────────────────
    def _normalize_tokens(self, niche_keywords: List[str], niche_path: str) -> List[str]:
        """
        Construit une liste de tokens (en minuscules) à partir des mots-clés
        de la niche et de son chemin d'arbre.
        """
        tokens: List[str] = []
        for kw in (niche_keywords or []):
            if kw:
                tokens.append(str(kw).lower().strip())
        if niche_path:
            for part in str(niche_path).replace(">", " ").split():
                tokens.append(part.lower().strip())
        return [t for t in tokens if t]

    def _text_blob(self, tokens: List[str]) -> str:
        """Concatène les tokens en un seul texte pour la recherche de sous-chaînes."""
        return " ".join(tokens)

    def _style_overlap_bonus(
        self, blob: str, styles: List[str], per_match: float, cap: float
    ) -> float:
        """
        Bonus/malus selon le nombre de styles d'une liste présents dans le blob.
        """
        matches = sum(1 for s in styles if s.lower() in blob)
        return min(cap, matches * per_match)

    # ── Méthode principale ────────────────────────────────────────────────────
    def score_niche_platform(
        self,
        niche_keywords: List[str],
        niche_path: str,
        platform_key: str,
    ) -> float:
        """
        Calcule le SCORE DE COMPATIBILITÉ STRUCTURELLE (0-100) entre une niche
        et une plateforme.

        Args:
            niche_keywords: mots-clés décrivant la niche (ex: ["botanical", "seamless"]).
            niche_path:     chemin de la niche dans l'arbre (ex: "Nature > Botanique").
            platform_key:   clé de la plateforme (ex: "spoonflower").

        Returns:
            Score 0-100. Plus c'est élevé, plus la niche est structurellement
            adaptée à la plateforme. Renvoie 0.0 si la plateforme est inconnue.

        ⚠️ Score structurel uniquement — à pondérer par les données réelles
        de demande/compétition du Module 01.
        """
        try:
            profile = self._profiles.get(platform_key)
            if profile is None:
                logger.warning("Plateforme inconnue dans CompatibilityMatrix: %s", platform_key)
                return 0.0

            tokens = self._normalize_tokens(niche_keywords, niche_path)
            blob = self._text_blob(tokens)

            score = self._BASE_SCORE

            # 1) Affinités par mots-clés (matrice explicite)
            for keyword, affinities in self._KEYWORD_AFFINITIES.items():
                if keyword in blob:
                    score += affinities.get(platform_key, 0.0)

            # 2) Recouvrement avec best_for_styles (bonus) / weak_for_styles (malus)
            score += self._style_overlap_bonus(blob, profile.best_for_styles, per_match=8.0, cap=24.0)
            score -= self._style_overlap_bonus(blob, profile.weak_for_styles, per_match=10.0, cap=30.0)

            # 3) Léger ajustement structurel : forte saturation = compatibilité réduite
            #    (la plateforme reste viable mais structurellement plus difficile).
            competition_adjust = {
                "low": +4.0, "medium": 0.0, "high": -4.0, "very_high": -8.0,
            }
            score += competition_adjust.get(profile.competition_level, 0.0)

            return round(min(100.0, max(0.0, score)), 1)

        except Exception as exc:  # robustesse : jamais de crash
            logger.error("Erreur score_niche_platform(%s): %s", platform_key, exc)
            return 0.0

    def score_all_platforms(
        self,
        niche_keywords: List[str],
        niche_path: str,
    ) -> Dict[str, float]:
        """
        Score la niche contre TOUTES les plateformes connues.

        Returns:
            Dict {platform_key: score} trié par score décroissant.
        """
        scores = {
            key: self.score_niche_platform(niche_keywords, niche_path, key)
            for key in self._profiles
        }
        return dict(sorted(scores.items(), key=lambda kv: kv[1], reverse=True))
