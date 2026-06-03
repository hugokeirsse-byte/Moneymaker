"""
Module 02 — Moteur d'Allocation d'Opportunités Multi-Plateformes.

Ce module orchestre l'ensemble du Module 02. À partir d'une opportunité détectée
(OpportunityScore du Module 01), il produit une RECOMMANDATION STRATÉGIQUE
complète :
    "Quelle niche, sur quelle plateforme, pour quel produit, avec quelle priorité ?"

⚠️ HONNÊTETÉ DES DONNÉES :
La recommandation combine :
  - les DONNÉES RÉELLES de marché du Module 01 (demande, croissance, concurrence) ;
  - les SCORES DE COMPATIBILITÉ STRUCTURELLE du Module 02 (basés sur les profils
    de plateformes — connaissance structurelle, pas du marché live).
La priorité de publication est donc une recommandation stratégique, pas une
garantie de revenu.
"""
import logging
from dataclasses import dataclass, field
from typing import Dict, List

from trend_discovery.platform_router.compatibility_matrix import CompatibilityMatrix
from trend_discovery.platform_router.economic_estimator import (
    EconomicEstimator,
    EconomicPotential,
)
from trend_discovery.platform_router.platform_profiles import (
    PLATFORM_PROFILES,
    get_profile,
)
from trend_discovery.platform_router.product_recommender import ProductRecommender

logger = logging.getLogger(__name__)


@dataclass
class StrategicRecommendation:
    """
    Recommandation stratégique complète pour une opportunité.

    Sortie principale du Module 02.
    """

    niche: str = ""
    global_score: float = 0.0                                   # score_final du M01
    platform_scores: Dict[str, float] = field(default_factory=dict)  # toutes, triées desc
    top_platforms: List[str] = field(default_factory=list)      # 3-5 meilleures
    recommended_products: Dict[str, List[str]] = field(default_factory=dict)
    discouraged_products: Dict[str, List[str]] = field(default_factory=dict)
    content_formats_to_produce: List[str] = field(default_factory=list)
    economic_potential: EconomicPotential = field(default_factory=EconomicPotential)
    publication_priority: str = "basse"                          # immédiate/haute/moyenne/basse
    priority_score: float = 0.0                                  # 0-100
    strategy_summary: str = ""

    def short_line(self) -> str:
        """Résumé d'une ligne pour le tri/log."""
        return (
            f"{self.niche} | priorité={self.publication_priority} "
            f"({self.priority_score:.0f}) | top={', '.join(self.top_platforms[:3])}"
        )


class OpportunityAllocator:
    """
    Orchestre la chaîne complète du Module 02 :
        CompatibilityMatrix → ProductRecommender → EconomicEstimator
        → calcul de priorité → résumé stratégique.
    """

    # Nombre de plateformes "top" retenues.
    _TOP_N = 5
    # Seuil de compatibilité pour qu'une plateforme soit "top".
    _TOP_THRESHOLD = 55.0

    def __init__(
        self,
        compatibility: CompatibilityMatrix = None,
        recommender: ProductRecommender = None,
        estimator: EconomicEstimator = None,
    ) -> None:
        self._compat = compatibility or CompatibilityMatrix()
        self._recommender = recommender or ProductRecommender()
        self._estimator = estimator or EconomicEstimator()

    # Traduction FR → EN des termes fréquents dans les niches normalisées.
    # Permet à _KEYWORD_AFFINITIES (en anglais) de matcher des niches en français.
    _FR_TO_EN: Dict[str, List[str]] = {
        # Botanique / Nature
        "botanique": ["botanical", "floral"],
        "botaniques": ["botanical", "floral"],
        "florale": ["floral"],
        "floraux": ["floral"],
        "florales": ["floral"],
        "herboristerie": ["herbal", "botanical"],
        "plantes": ["botanical"],
        "champignons": ["botanical"],
        "forêt": ["botanical", "wallpaper"],
        "océan": ["nautical"],
        "marin": ["nautical"],
        "tropical": ["tropical", "botanical"],
        "nature": ["botanical", "floral"],
        "aquarelle": ["botanical", "art print"],
        # Motifs / Textile
        "motif": ["pattern", "seamless"],
        "motifs": ["pattern", "seamless"],
        "répété": ["repeat", "seamless"],
        "répétés": ["repeat", "seamless"],
        "textile": ["textile", "fabric"],
        "tissu": ["fabric", "textile"],
        "papier": ["wallpaper"],
        "peint": ["wallpaper"],
        "surface": ["surface design"],
        # Humour
        "humour": ["humor", "funny"],
        "drôle": ["funny"],
        "mème": ["meme"],
        "mèmes": ["meme"],
        "blague": ["humor"],
        "citation": ["quote"],
        # Pop culture / Geek
        "geek": ["geek"],
        "jeux": ["gaming"],
        "gaming": ["gaming"],
        "fandom": ["fandom"],
        # Art mural / Déco
        "mural": ["wall art"],
        "affiche": ["poster"],
        "minimaliste": ["minimalist"],
        "abstrait": ["abstract"],
        "abstraits": ["abstract"],
        "boho": ["boho"],
        "esthétique": ["aesthetic"],
        "intérieur": ["interior"],
        "décoration": ["interior", "wall art"],
        "géométrique": ["abstract", "seamless"],
        "géométriques": ["abstract", "seamless"],
        "mandala": ["abstract"],
        # Événementiel
        "mariage": ["wedding"],
        "événement": ["event"],
        "invitation": ["invitation"],
        "invitations": ["invitation"],
        "papeterie": ["stationery"],
        "monogramme": ["monogram"],
        "personnalisation": ["personalization"],
        "personnalisé": ["personalization"],
        # Craft / Numérique
        "coloriage": ["coloring"],
        "colorier": ["coloring"],
        "découpe": ["cut file", "svg"],
        "sublimation": ["sublimation"],
        "imprimable": ["printable"],
        "modèle": ["template"],
        "police": ["font"],
        "illustration": ["illustration set"],
        "illustrations": ["illustration set"],
        "livre": ["book"],
        "guide": ["guide"],
        "éducatif": ["educational"],
        "activités": ["activity book"],
        "trait": ["line art"],
        # B2B
        "collection": ["collection"],
        "collections": ["collection"],
        "bibliothèque": ["library"],
        "licence": ["license"],
        "licences": ["license"],
        "commercial": ["commercial"],
        "premium": ["premium"],
        "professionnel": ["professional"],
        # Styles visuels communs dans les chemins d'arbre
        "celtique": ["illustration set"],
        "médiéval": ["illustration set"],
        "japonais": ["illustration set"],
        "zen": ["abstract", "minimalist"],
        "vintage": ["illustration set"],
        "cosmique": ["abstract"],
        "céleste": ["abstract"],
        "espace": ["abstract"],
        "sticker": ["sticker"],
        "stickers": ["sticker"],
        "noël": ["seasonal", "pattern"],
        "halloween": ["seasonal", "pattern"],
    }

    # ── Extraction des mots-clés de la niche ─────────────────────────────────
    def _extract_keywords(self, opportunity_score) -> List[str]:
        """
        Construit la liste de mots-clés décrivant la niche à partir des champs
        de l'OpportunityScore (niche, canonical_name, path).
        Traduit les termes français en équivalents anglais pour que
        _KEYWORD_AFFINITIES (en anglais) puisse les matcher.
        """
        kws: List[str] = []
        niche = getattr(opportunity_score, "niche", "") or ""
        canonical = getattr(opportunity_score, "canonical_name", "") or ""
        path = getattr(opportunity_score, "path", "") or ""

        for raw in (niche, canonical):
            if raw:
                kws.extend(str(raw).lower().replace("/", " ").split())
        if path:
            kws.extend(p.strip().lower() for p in str(path).replace(">", " ").split())
        # Conserver aussi les expressions complètes (pour matcher "pop culture" etc.)
        if niche:
            kws.append(str(niche).lower())
        if path:
            kws.append(str(path).lower())

        # Expansion FR → EN : pour chaque token français, ajouter les équivalents anglais
        expanded: List[str] = list(kws)
        for token in kws:
            en_equivalents = self._FR_TO_EN.get(token)
            if en_equivalents:
                expanded.extend(en_equivalents)

        return list(dict.fromkeys([k for k in expanded if k]))

    # ── Sélection des plateformes top ─────────────────────────────────────────
    def _select_top_platforms(self, platform_scores: Dict[str, float]) -> List[str]:
        """Retient les meilleures plateformes (>= seuil), 3 à 5 max."""
        ranked = [k for k, v in platform_scores.items() if v >= self._TOP_THRESHOLD]
        if len(ranked) < 3:
            # garantir au moins 3 propositions même si sous le seuil
            ranked = list(platform_scores.keys())[:3]
        return ranked[: self._TOP_N]

    # ── Calcul de la priorité de publication ──────────────────────────────────
    def _compute_priority(
        self,
        global_score: float,
        economic: EconomicPotential,
        best_platform_score: float,
    ) -> (float, str):
        """
        Combine le score global (M01), le potentiel économique (M02) et la
        meilleure compatibilité plateforme pour produire un priority_score 0-100
        et un label de priorité.

        Hypothèse de pondération :
            priority = global_score×0.40
                     + sales_potential×0.20
                     + best_platform_compat×0.20
                     + reusability×0.10
                     + bonus_faible_concurrence×0.10
        La faible concurrence est un bonus (100 − pression concurrentielle).
        """
        low_competition_bonus = 100.0 - economic.competition_pressure
        priority = (
            global_score * 0.40
            + economic.sales_potential * 0.20
            + best_platform_score * 0.20
            + economic.reusability_score * 0.10
            + low_competition_bonus * 0.10
        )
        priority = round(min(100.0, max(0.0, priority)), 1)

        if priority >= 75:
            label = "immédiate"
        elif priority >= 60:
            label = "haute"
        elif priority >= 40:
            label = "moyenne"
        else:
            label = "basse"
        return priority, label

    # ── Génération du résumé stratégique ──────────────────────────────────────
    def _build_summary(
        self,
        niche: str,
        top_platforms: List[str],
        economic: EconomicPotential,
        priority_label: str,
        recommended_products: Dict[str, List[str]],
        content_formats: List[str],
    ) -> str:
        """Construit un résumé actionnable en français."""
        top_names = []
        for key in top_platforms:
            try:
                top_names.append(get_profile(key).name)
            except Exception:
                top_names.append(key)

        first_platform = top_platforms[0] if top_platforms else None
        first_products = recommended_products.get(first_platform, []) if first_platform else []
        prod_txt = ", ".join(first_products[:3]) if first_products else "produits génériques"
        fmt_txt = "; ".join(content_formats[:2]) if content_formats else "PNG HD"

        return (
            f"Niche « {niche} » : priorité de publication {priority_label.upper()}. "
            f"Cibler en priorité {', '.join(top_names[:3]) or 'aucune plateforme adaptée'}. "
            f"Sur {top_names[0] if top_names else 'la plateforme principale'}, produire : {prod_txt}. "
            f"Formats à produire : {fmt_txt}. "
            f"Potentiel économique : tier {economic.estimated_revenue_tier}, "
            f"{economic.exploitable_markets_count} marché(s) exploitable(s), "
            f"réutilisabilité {economic.reusability_score:.0f}/100. "
            f"(Scores de compatibilité = structurels ; demande/concurrence = données réelles M01.)"
        )

    # ── Méthode principale ────────────────────────────────────────────────────
    def allocate(self, opportunity_score) -> StrategicRecommendation:
        """
        Transforme une opportunité (OpportunityScore) en recommandation
        stratégique multi-plateformes complète.

        Ne lève jamais d'exception : retombe sur une recommandation minimale
        en cas d'erreur.
        """
        try:
            niche = getattr(opportunity_score, "niche", "") or "(niche inconnue)"
            global_score = float(getattr(opportunity_score, "score_final", 0.0) or 0.0)
            path = getattr(opportunity_score, "path", "") or ""
            keywords = self._extract_keywords(opportunity_score)

            # 1) Compatibilité structurelle de toutes les plateformes
            platform_scores = self._compat.score_all_platforms(keywords, path)

            # 2) Sélection des top plateformes
            top_platforms = self._select_top_platforms(platform_scores)

            # 3) Recommandations produits par plateforme top
            recommended_products: Dict[str, List[str]] = {}
            discouraged_products: Dict[str, List[str]] = {}
            for pkey in top_platforms:
                rec = self._recommender.recommend_products(keywords, pkey)
                recommended_products[pkey] = rec.get("recommended", [])
                discouraged_products[pkey] = rec.get("discouraged", [])

            # 4) Formats de contenu à produire
            content_formats = self._recommender.recommend_content_formats(keywords)

            # 5) Potentiel économique
            economic = self._estimator.estimate(opportunity_score, platform_scores)

            # 6) Priorité de publication
            best_platform_score = (
                max(platform_scores.values()) if platform_scores else 0.0
            )
            priority_score, priority_label = self._compute_priority(
                global_score, economic, best_platform_score
            )

            # 7) Résumé stratégique
            summary = self._build_summary(
                niche, top_platforms, economic, priority_label,
                recommended_products, content_formats,
            )

            return StrategicRecommendation(
                niche=niche,
                global_score=round(global_score, 2),
                platform_scores=platform_scores,
                top_platforms=top_platforms,
                recommended_products=recommended_products,
                discouraged_products=discouraged_products,
                content_formats_to_produce=content_formats,
                economic_potential=economic,
                publication_priority=priority_label,
                priority_score=priority_score,
                strategy_summary=summary,
            )

        except Exception as exc:  # robustesse globale
            logger.error("Erreur OpportunityAllocator.allocate: %s", exc)
            niche = getattr(opportunity_score, "niche", "(niche inconnue)")
            return StrategicRecommendation(
                niche=niche,
                strategy_summary="Recommandation indisponible suite à une erreur interne.",
            )

    def allocate_batch(self, opportunity_scores: List) -> List[StrategicRecommendation]:
        """
        Alloue une liste d'opportunités et retourne les recommandations triées
        par priority_score décroissant.
        """
        recommendations: List[StrategicRecommendation] = []
        for opp in (opportunity_scores or []):
            recommendations.append(self.allocate(opp))
        recommendations.sort(key=lambda r: r.priority_score, reverse=True)
        return recommendations


# ─────────────────────────────────────────────────────────────────────────────
# Test d'intégration end-to-end.
# Lancer : python -m trend_discovery.platform_router.allocator
# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    from trend_discovery.analyzers.opportunity_scorer import OpportunityScore

    print("=" * 70)
    print("TEST D'INTÉGRATION — Module 02 (OpportunityAllocator)")
    print("=" * 70)

    # Opportunité factice 1 : motif botanique seamless (devrait pousser Spoonflower/B2B)
    opp_botanical = OpportunityScore(
        niche="botanical seamless pattern",
        canonical_name="motifs botaniques",
        path="Nature > Botanique > Motifs floraux",
        demande=78.0,
        croissance=62.0,
        potentiel_visuel=85.0,
        potentiel_commercial=70.0,
        potentiel_hybridation=55.0,
        concurrence=40.0,
        score_final=68.5,
        sources=["google_trends", "spoonflower"],
        confidence=72.0,
    )

    # Opportunité factice 2 : humour pop culture (devrait pousser RedBubble/TeePublic)
    opp_humor = OpportunityScore(
        niche="funny cat meme",
        canonical_name="humour chats",
        path="Humour > Memes > Animaux",
        demande=90.0,
        croissance=70.0,
        potentiel_visuel=60.0,
        potentiel_commercial=65.0,
        potentiel_hybridation=40.0,
        concurrence=85.0,
        score_final=54.0,
        sources=["reddit", "redbubble"],
        confidence=60.0,
    )

    # Opportunité factice 3 : SVG / Cricut (devrait pousser Design Bundles / Etsy)
    opp_svg = OpportunityScore(
        niche="cricut svg bundle",
        canonical_name="svg cricut",
        path="Craft > Découpe > SVG",
        demande=72.0,
        croissance=55.0,
        potentiel_visuel=70.0,
        potentiel_commercial=80.0,
        potentiel_hybridation=50.0,
        concurrence=60.0,
        score_final=61.0,
        sources=["etsy"],
        confidence=50.0,
    )

    allocator = OpportunityAllocator()
    recos = allocator.allocate_batch([opp_botanical, opp_humor, opp_svg])

    for reco in recos:
        print("\n" + "-" * 70)
        print(reco.short_line())
        print("-" * 70)
        print("Top plateformes :")
        for pkey in reco.top_platforms:
            score = reco.platform_scores.get(pkey, 0.0)
            prods = reco.recommended_products.get(pkey, [])
            print(f"  - {pkey:18s} compat={score:5.1f}  produits={prods}")
        print(f"Formats à produire : {reco.content_formats_to_produce}")
        print(f"Économie : {reco.economic_potential.summary()}")
        print(f"Résumé : {reco.strategy_summary}")

    # Vérifications de sanité basiques.
    assert len(recos) == 3, "doit retourner 3 recommandations"
    assert all(0 <= r.priority_score <= 100 for r in recos), "priority_score hors bornes"
    assert recos == sorted(recos, key=lambda r: r.priority_score, reverse=True), "non trié"
    # Le motif botanique doit favoriser Spoonflower dans son top.
    bot = next(r for r in recos if r.niche == "botanical seamless pattern")
    assert "spoonflower" in bot.top_platforms, "Spoonflower attendu pour le botanique seamless"
    # L'humour doit favoriser RedBubble ou TeePublic.
    hum = next(r for r in recos if r.niche == "funny cat meme")
    assert any(p in hum.top_platforms for p in ("redbubble", "teepublic")), \
        "RedBubble/TeePublic attendu pour l'humour"

    print("\n" + "=" * 70)
    print("OK — Test d'intégration réussi, toutes les assertions passent.")
    print("=" * 70)
