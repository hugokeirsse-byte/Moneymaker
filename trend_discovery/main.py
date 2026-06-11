"""
Moneymaker — Module 01 : Moteur de Détection de Tendances et d'Opportunités

Pipeline en 7 phases :
    Phase 1 — Collecte          : tous les scrapers actifs
    Phase 2 — Normalisation     : clustering et fusion des synonymes
    Phase 3 — Arbre de Niches   : décomposition hiérarchique
    Phase 4 — Hybridation       : combinaisons à fort potentiel
    Phase 5 — Scoring           : formule multi-critères
    Phase 6 — Classement        : base d'opportunités SQLite
    Phase 7 — Mémoire           : historique et évolution des scores

Usage :
    python -m trend_discovery.main
    python -m trend_discovery.main --fast
    python -m trend_discovery.main --keywords "botanical,medieval" --depth 2
"""
import argparse
import logging
import os
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("moneymaker.pipeline")

try:
    from trend_discovery.generators.approval_gate import DEFAULT_IMAGES_PER_BRIEF
except Exception:
    DEFAULT_IMAGES_PER_BRIEF = 5

from trend_discovery.config import NICHE_CATEGORIES, OUTPUT_DIR, KEYWORDS_SEED
from trend_discovery.normalizer.concept_merger import ConceptMerger
from trend_discovery.normalizer.niche_tree_builder import NicheTree
from trend_discovery.analyzers.trend_scorer import TrendScorer
from trend_discovery.analyzers.hybrid_scorer import HybridScorer
from trend_discovery.analyzers.feasibility_scorer import FeasibilityScorer
from trend_discovery.analyzers.opportunity_scorer import OpportunityScorer
from trend_discovery.database.opportunity_store import OpportunityStore
from trend_discovery.database.history_tracker import HistoryTracker
from trend_discovery.reporters.report_generator import NicheReport, ReportGenerator


def run_pipeline(
    extra_keywords: Optional[List[str]] = None,
    focus_categories: Optional[List[str]] = None,
    fast_mode: bool = False,
    tree_depth: int = 2,
    db_path: str = "./data/opportunities.db",
) -> NicheReport:
    """
    Execute the full 7-phase Moneymaker detection pipeline.
    """
    t0 = time.time()
    logger.info("=" * 60)
    logger.info("MONEYMAKER — Module 01 : Détection de Tendances")
    logger.info("Mode: %s | Profondeur arbre: %d", "rapide" if fast_mode else "complet", tree_depth)
    logger.info("=" * 60)

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 3 — Arbre de Niches (fait en premier : base de travail statique)
    # ══════════════════════════════════════════════════════════════════════════
    logger.info("[Phase 3] Construction de l'arbre de niches…")
    tree = NicheTree()
    merger = ConceptMerger()

    # Extract all niches at target depth from tree
    target_niches = []
    for level in range(1, tree_depth + 1):
        nodes = tree.niches_at_level(level)
        target_niches.extend(n.name for n in nodes)

    # Add config-based niches
    for cat, terms in NICHE_CATEGORIES.items():
        if focus_categories is None or cat in focus_categories:
            target_niches.extend(terms)

    # Add extra keywords, canonicalized
    if extra_keywords:
        for kw in extra_keywords:
            canonical = merger.normalize(kw) or kw
            target_niches.append(canonical)

    # Deduplicate
    target_niches = list(dict.fromkeys(target_niches))
    logger.info("[Phase 3] %d niches dans l'arbre de travail", len(target_niches))

    # Build tree path map for all niches
    tree_paths: Dict[str, str] = {}
    canonical_names: Dict[str, str] = {}
    for niche in target_niches:
        node = tree.get(niche)
        if node:
            tree_paths[niche] = tree.path_to(niche)
        canon = merger.normalize(niche)
        if canon and canon != niche:
            canonical_names[niche] = canon

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 1 — Collecte de Données
    # ══════════════════════════════════════════════════════════════════════════
    logger.info("[Phase 1] Collecte des signaux de marché…")
    sources_consulted = []
    google_data: Dict = {}
    reddit_data: Dict = {}
    autocomplete_data: Dict = {}
    competition_data: Dict = {}
    raw_signals: Dict = {}
    tiktok_niche_scores: Dict = {}

    # Use full registry for non-fast mode, limited set for fast mode
    scrapers_to_run = (
        ["google_trends", "google_autocomplete", "reddit"]
        if fast_mode
        else None  # None = all registered scrapers
    )

    try:
        from trend_discovery.scrapers.scraper_registry import ScraperOrchestrator
        orch = ScraperOrchestrator(enabled_only=True)

        if fast_mode:
            # Manually run only the three fast scrapers
            _run_fast_scrapers(
                target_niches, google_data, reddit_data,
                autocomplete_data, sources_consulted
            )
        else:
            # Run full scraper suite
            _run_full_scrapers(
                target_niches, google_data, reddit_data,
                autocomplete_data, competition_data,
                tiktok_niche_scores, sources_consulted
            )
    except Exception as exc:
        logger.warning("[Phase 1] Scraper orchestrator error: %s — continuing", exc)

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 2 — Normalisation
    # ══════════════════════════════════════════════════════════════════════════
    logger.info("[Phase 2] Normalisation et fusion des concepts…")
    # Merge raw signals into canonical niches
    all_raw_keywords = list(google_data.keys()) + list(reddit_data.keys())
    for kw in all_raw_keywords:
        canon = merger.normalize(kw)
        if canon and canon not in target_niches:
            target_niches.append(canon)
            logger.debug("[Phase 2] Nouveau terme canonique découvert: %s → %s", kw, canon)

    # Final dedup after normalization
    target_niches = list(dict.fromkeys(target_niches))
    logger.info("[Phase 2] %d niches après normalisation", len(target_niches))

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 1bis — Collecte de DONNÉES RÉELLES (providers / APIs officielles)
    # ══════════════════════════════════════════════════════════════════════════
    logger.info("[Phase 1bis] Collecte de vraies données via les providers…")
    real_data_map: Dict = {}
    gemini_trend_cache: Dict = {}  # {niche_name: metadata} pour le prompt builder
    try:
        from trend_discovery.providers.real_data_collector import RealDataCollector
        from trend_discovery.providers.provider_registry import ProviderRegistry
        registry = ProviderRegistry()
        avail = registry.available()
        if avail:
            logger.info(
                "[Phase 1bis] Sources réelles disponibles : %s",
                [p.key for p in avail],
            )
            # Injection des tendances Gemini (web search temps réel)
            gemini_provider = registry.get("gemini")
            if gemini_provider and gemini_provider.is_available():
                logger.info("[Phase 1bis] Gemini : recherche des tendances mondiales…")
                global_trends = gemini_provider.fetch_global_pod_trends()
                if global_trends:
                    # Ajouter les niches Gemini au pipeline
                    gemini_niches = gemini_provider.get_enriched_niche_names()
                    for n in gemini_niches:
                        if n not in target_niches:
                            target_niches.append(n)
                    # Cache pour enrichir les prompts de génération
                    for t in global_trends:
                        gemini_trend_cache[t.get("name", "")] = t
                        for sub in t.get("sub_niches", []):
                            gemini_trend_cache[sub] = t
                    logger.info(
                        "[Phase 1bis] Gemini : %d tendances + %d sous-niches injectées",
                        len(global_trends),
                        len([s for t in global_trends for s in t.get("sub_niches", [])]),
                    )
                    sources_consulted.append("gemini")

            collector = RealDataCollector(registry)
            real_data_map = collector.collect_batch(target_niches[:60])
            sources_consulted.extend([p.key for p in avail if p.key != "gemini"])
        else:
            logger.warning(
                "[Phase 1bis] ⚠️  AUCUNE source réelle disponible (clés API manquantes). "
                "Les scores seront marqués comme NON FIABLES. "
                "Configure GEMINI_API_KEY pour les tendances mondiales en temps réel."
            )
    except Exception as exc:
        logger.warning("[Phase 1bis] Collecte réelle échouée: %s", exc)

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 4 — Hybridation
    # ══════════════════════════════════════════════════════════════════════════
    logger.info("[Phase 4] Calcul des niches hybrides…")
    trend_scorer = TrendScorer()
    trend_scores_list = trend_scorer.score_keywords(
        keywords=target_niches,
        google_data=google_data,
        reddit_data=reddit_data,
        autocomplete_data=autocomplete_data,
    )
    trend_scores_map = {ts.keyword: ts for ts in trend_scores_list}

    hybrid_scorer = HybridScorer()
    hybrid_scores = hybrid_scorer.generate_hybrid_niches(
        scored_niches=trend_scores_list,
        competition_data=competition_data,
        top_n_source=20,
        max_hybrids=30,
    )
    logger.info("[Phase 4] %d combinaisons hybrides générées", len(hybrid_scores))

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 5 — Scoring
    # ══════════════════════════════════════════════════════════════════════════
    logger.info("[Phase 5] Calcul des scores d'opportunité…")
    feas_scorer = FeasibilityScorer()
    feasibility_scores_list = feas_scorer.score_niches(target_niches)
    feasibility_scores_map = {fs.niche: fs for fs in feasibility_scores_list}

    opp_scorer = OpportunityScorer()
    opportunity_scores = opp_scorer.score_all(
        niches=target_niches,
        trend_scores_map=trend_scores_map,
        feasibility_scores_map=feasibility_scores_map,
        hybrid_scores=hybrid_scores,
        competition_data=competition_data,
        tree_paths=tree_paths,
        canonical_names=canonical_names,
        real_data_map=real_data_map,
    )
    logger.info("[Phase 5] %d opportunités scorées", len(opportunity_scores))
    # Bilan de fiabilité global
    reliable = [o for o in opportunity_scores if o.reliability >= 45]
    logger.info(
        "[Phase 5] Fiabilité : %d/%d opportunités basées sur de vraies données",
        len(reliable), len(opportunity_scores),
    )

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 6 — Classement (Base de données)
    # ══════════════════════════════════════════════════════════════════════════
    logger.info("[Phase 6] Mise à jour de la base d'opportunités…")
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    store = OpportunityStore(db_path=db_path)
    store.upsert_many(opportunity_scores)
    for hybrid in hybrid_scores[:20]:
        store.upsert_hybrid(hybrid)
    top_from_db = store.get_top_opportunities(limit=20)
    logger.info("[Phase 6] Base de données : %d opportunités totales", store.count())

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 7 — Mémoire Historique
    # ══════════════════════════════════════════════════════════════════════════
    logger.info("[Phase 7] Enregistrement de l'historique…")
    tracker = HistoryTracker(db_path=db_path)
    tracker.record_batch(opportunity_scores)
    rising = tracker.get_all_rising_niches(min_delta=3.0, min_history=2)
    if rising:
        logger.info(
            "[Phase 7] %d niches en progression détectées: %s",
            len(rising),
            [r["niche"] for r in rising[:5]],
        )

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 8 — Allocation Multi-Plateformes (Module 02)
    # ══════════════════════════════════════════════════════════════════════════
    logger.info("[Phase 8] Allocation stratégique multi-plateformes…")
    try:
        from trend_discovery.platform_router.allocator import OpportunityAllocator
        from trend_discovery.platform_router.strategy_reporter import StrategyReporter
        allocator = OpportunityAllocator()
        # On alloue les meilleures opportunités (les plus fiables d'abord)
        recommendations = allocator.allocate_batch(opportunity_scores[:20])
        strat_reporter = StrategyReporter()
        strat_paths = strat_reporter.save_report(recommendations, output_dir=OUTPUT_DIR)
        logger.info(
            "[Phase 8] %d recommandations stratégiques générées : %s",
            len(recommendations), strat_paths.get("markdown", ""),
        )
    except Exception as exc:
        logger.warning("[Phase 8] Allocation multi-plateformes échouée: %s", exc)
        strat_paths = {}

    # ══════════════════════════════════════════════════════════════════════════
    # PHASE 9 — Génération d'Images Spoonflower (Module 03)
    # Génère les 5 meilleures niches → PNG 300 DPI prêts à uploader
    # ══════════════════════════════════════════════════════════════════════════
    generated_files: List[str] = []
    try:
        from trend_discovery.generators.generation_pipeline import GenerationPipeline
        gen_pipeline = GenerationPipeline(
            output_dir="./output/spoonflower",
            upscale_factor=4,
        )
        if gen_pipeline._runware.is_available():
            logger.info("[Phase 9] Génération d'images Spoonflower (top 5 niches)…")
            gen_results = gen_pipeline.run(
                opportunity_scores=opportunity_scores,
                max_images=5,
                gemini_cache=gemini_trend_cache,
            )
            generated_files = [r.filepath for r in gen_results if r.success and r.filepath]
            logger.info(
                "[Phase 9] %d/%d images générées → ./output/spoonflower/",
                len(generated_files), len(gen_results),
            )
        else:
            logger.info(
                "[Phase 9] Génération désactivée (RUNWARE_API_KEY absente). "
                "Ajoute la clé pour générer automatiquement les images Spoonflower."
            )
    except Exception as exc:
        logger.warning("[Phase 9] Génération d'images échouée: %s", exc)

    # ══════════════════════════════════════════════════════════════════════════
    # Génération du Rapport Final
    # ══════════════════════════════════════════════════════════════════════════
    elapsed = round(time.time() - t0, 1)
    logger.info("Pipeline complet en %.1fs — génération du rapport…", elapsed)

    report = NicheReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        sources_consulted=sorted(set(sources_consulted)),
        keywords_analyzed=len(target_niches),
        top_niches=trend_scores_list[:20],
        top_hybrids=hybrid_scores[:15],
        feasibility_scores=feasibility_scores_list,
        competition_data=competition_data,
        execution_time_seconds=elapsed,
    )

    reporter = ReportGenerator()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    paths = reporter.save_report(report, output_dir=OUTPUT_DIR)

    logger.info("=" * 60)
    logger.info("✅ MONEYMAKER PIPELINE TERMINÉ")
    logger.info("   Rapport  : %s", paths["markdown"])
    logger.info("   JSON     : %s", paths["json"])
    logger.info("   Database : %s", db_path)
    logger.info("=" * 60)

    store.close()
    tracker.close()
    return report


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers for scraper runs
# ─────────────────────────────────────────────────────────────────────────────

def _run_fast_scrapers(niches, google_data, reddit_data, autocomplete_data, sources):
    """Quick run: only Google Trends, Autocomplete, Reddit."""
    try:
        from trend_discovery.scrapers.google_trends_scraper import GoogleTrendsScraper
        gt = GoogleTrendsScraper()
        data = gt.get_interest_over_time(niches[:15])
        google_data.update(data)
        sources.append("google_trends")
        logger.info("[Phase 1] Google Trends: %d niches", len(data))
    except Exception as exc:
        logger.warning("[Phase 1] Google Trends failed: %s", exc)

    try:
        from trend_discovery.scrapers.google_autocomplete_scraper import GoogleAutocompleteScraper
        gac = GoogleAutocompleteScraper()
        data = gac.get_trending_pod_keywords()
        autocomplete_data.update(data)
        sources.append("google_autocomplete")
    except Exception as exc:
        logger.warning("[Phase 1] Autocomplete failed: %s", exc)

    try:
        from trend_discovery.scrapers.reddit_scraper import RedditScraper
        rs = RedditScraper()
        data = rs.get_trending_keywords_from_reddit()
        reddit_data.update(data)
        sources.append("reddit")
    except Exception as exc:
        logger.warning("[Phase 1] Reddit failed: %s", exc)


def _run_full_scrapers(
    niches, google_data, reddit_data, autocomplete_data,
    competition_data, tiktok_scores, sources
):
    """Full run: all scrapers."""
    # Google Trends
    try:
        from trend_discovery.scrapers.google_trends_scraper import GoogleTrendsScraper
        gt = GoogleTrendsScraper()
        data = gt.get_interest_over_time(niches[:20])
        google_data.update(data)
        sources.append("google_trends")
    except Exception as exc:
        logger.warning("[Phase 1] Google Trends: %s", exc)

    # Google Autocomplete
    try:
        from trend_discovery.scrapers.google_autocomplete_scraper import GoogleAutocompleteScraper
        gac = GoogleAutocompleteScraper()
        ac_data = gac.get_trending_pod_keywords()
        niche_ac = gac.analyze_pattern_niches(seed_keywords=niches[:15])
        autocomplete_data.update(ac_data)
        autocomplete_data.update(niche_ac)
        sources.append("google_autocomplete")
    except Exception as exc:
        logger.warning("[Phase 1] Autocomplete: %s", exc)

    # Bing Autosuggest
    try:
        from trend_discovery.scrapers.bing_trends_scraper import BingTrendsScraper
        bing = BingTrendsScraper()
        bing_data = bing.get_pod_suggestions(niches[:10])
        autocomplete_data.update(bing_data)
        sources.append("bing_autosuggest")
    except Exception as exc:
        logger.warning("[Phase 1] Bing: %s", exc)

    # Reddit
    try:
        from trend_discovery.scrapers.reddit_scraper import RedditScraper
        rs = RedditScraper()
        reddit_data.update(rs.get_trending_keywords_from_reddit())
        sources.append("reddit")
    except Exception as exc:
        logger.warning("[Phase 1] Reddit: %s", exc)

    # TikTok
    try:
        from trend_discovery.scrapers.tiktok_scraper import TikTokScraper
        tt = TikTokScraper()
        hashtags = tt.get_aesthetic_hashtags()
        tt_scores = tt.map_hashtags_to_niches(hashtags)
        tiktok_scores.update(tt_scores)
        sources.append("tiktok")
    except Exception as exc:
        logger.warning("[Phase 1] TikTok: %s", exc)

    # Pinterest
    try:
        from trend_discovery.scrapers.pinterest_scraper import PinterestScraper
        pin = PinterestScraper()
        pin_data = pin.analyze_pod_trends(seed_keywords=niches[:10])
        autocomplete_data.update(pin_data)
        sources.append("pinterest")
    except Exception as exc:
        logger.warning("[Phase 1] Pinterest: %s", exc)

    # Etsy
    try:
        from trend_discovery.scrapers.etsy_scraper import EtsyScraper
        etsy = EtsyScraper()
        for kw in niches[:15]:
            result = etsy.analyze_competition(kw)
            competition_data[kw] = result
        sources.append("etsy")
    except Exception as exc:
        logger.warning("[Phase 1] Etsy: %s", exc)

    # RedBubble (competition)
    try:
        from trend_discovery.scrapers.redbubble_scraper import RedbubbleScraper
        rb = RedbubbleScraper()
        rb_results = rb.batch_analyze_competition(niches[:20])
        for r in rb_results:
            kw = r["keyword"]
            if kw in competition_data:
                # Merge: average competition scores
                competition_data[kw]["competition_score"] = (
                    competition_data[kw]["competition_score"] + r["competition_score"]
                ) / 2
            else:
                competition_data[kw] = r
        sources.append("redbubble")
    except Exception as exc:
        logger.warning("[Phase 1] RedBubble: %s", exc)

    # Spoonflower (tags → new niches discovery)
    try:
        from trend_discovery.scrapers.spoonflower_scraper import SpoonflowerScraper
        sf = SpoonflowerScraper()
        top_tags = sf.get_top_tags(top_n=30)
        if top_tags:
            for tag in list(top_tags.keys())[:10]:
                if tag not in niches:
                    niches.append(tag)
        sources.append("spoonflower")
    except Exception as exc:
        logger.warning("[Phase 1] Spoonflower: %s", exc)

    # Society6 (trending tags)
    try:
        from trend_discovery.scrapers.society6_scraper import Society6Scraper
        s6 = Society6Scraper()
        tags = s6.get_trending_tags()
        for tag in tags[:10]:
            if tag not in niches:
                niches.append(tag)
        sources.append("society6")
    except Exception as exc:
        logger.warning("[Phase 1] Society6: %s", exc)

    # Creative Market
    try:
        from trend_discovery.scrapers.creative_market_scraper import CreativeMarketScraper
        cm = CreativeMarketScraper()
        cm_tags = cm.get_popular_tags()
        autocomplete_data["creative_market_tags"] = cm_tags
        sources.append("creative_market")
    except Exception as exc:
        logger.warning("[Phase 1] Creative Market: %s", exc)

    # DeviantArt
    try:
        from trend_discovery.scrapers.deviantart_scraper import DeviantArtScraper
        da = DeviantArtScraper()
        da_tags = da.get_trending_tags()
        autocomplete_data["deviantart_tags"] = da_tags
        sources.append("deviantart")
    except Exception as exc:
        logger.warning("[Phase 1] DeviantArt: %s", exc)

    # YouTube (autocomplete — no key needed)
    try:
        from trend_discovery.scrapers.youtube_trends_scraper import YouTubeTrendsScraper
        yt = YouTubeTrendsScraper()
        yt_data = yt.get_design_tutorial_demand(niches[:8])
        autocomplete_data.update(yt_data)
        sources.append("youtube")
    except Exception as exc:
        logger.warning("[Phase 1] YouTube: %s", exc)

    # Amazon Merch autocomplete
    try:
        from trend_discovery.scrapers.amazon_merch_scraper import AmazonMerchScraper
        amz = AmazonMerchScraper()
        amz_data = amz.get_pod_demand_signals(niches[:10])
        autocomplete_data.update(amz_data)
        sources.append("amazon")
    except Exception as exc:
        logger.warning("[Phase 1] Amazon: %s", exc)


# ─────────────────────────────────────────────────────────────────────────────
# Mode preview : vérifie Gemini + prompts SANS générer d'images
# ─────────────────────────────────────────────────────────────────────────────

def preview_trends(
    output_dir: str = "./reports",
    market: str = "spoonflower",
    niche_count: Optional[int] = None,
    extra_constraints: str = "",
) -> None:
    """
    Mode de vérification : interroge Gemini + Wikimedia, valide les opportunités,
    génère les cahiers des charges complets (direction visuelle, palette hex,
    images de référence, prompts IA prêts) avec score transparent et fiabilité.

    Args:
        output_dir: dossier de sortie des rapports.
        market: clé du marché ciblé (ex: "spoonflower").
        niche_count: si fourni, surcharge le nombre de niches du profil.
        extra_constraints: contraintes opérateur injectées dans le prompt Gemini.

    Sortie : console + reports/cahiers_des_charges_YYYYMMDD_HHMM.md + .json
    """
    from trend_discovery.generators.production_brief import BriefGenerator
    from trend_discovery.markets.market_profile import get_profile

    logger.info("=" * 60)
    logger.info("PREVIEW — Cahiers des Charges (validation d'opportunités, sans génération)")
    logger.info("=" * 60)

    profile = get_profile(market)
    if niche_count:
        profile.niche_count = int(niche_count)

    gen = BriefGenerator(profile)
    if gen._gemini.is_available():
        logger.info("Interrogation Gemini + Google Search + Wikimedia Commons…")
    else:
        logger.info(
            "Gemini indisponible — génération via arbre de niches + Wikipedia + Wikimedia (0 coût)."
        )
    briefs = gen.generate_all(extra_constraints)

    if not briefs:
        logger.error("Aucune tendance trouvée.")
        return

    # Affichage résumé console
    print("\n" + "=" * 60)
    print(f"  {len(briefs)} CAHIERS DES CHARGES GÉNÉRÉS — marché : {profile.key}")
    print("=" * 60)

    for i, b in enumerate(briefs, 1):
        sat_level = (b.saturation or {}).get("level", "?")
        print(
            f"\n{b.opportunity_emoji()} #{i} {b.name} "
            f"— opportunité {b.opportunity_score}/100 "
            f"| fiabilité {b.confidence}% "
            f"| saturation {sat_level}"
        )
        if b.demand_evidence:
            print(f"   Demande: {b.demand_evidence[:90]}")
        if b.color_primary:
            print(f"   Couleurs: {', '.join(b.color_primary[:2])}")
        if b.reference_images:
            print(f"   Références: {len(b.reference_images)} image(s) Wikimedia")

    print("\n" + "=" * 60)
    print("  VÉRIFICATION TERMINÉE — aucune image générée, aucun coût")
    print("=" * 60 + "\n")

    # Sauvegarde rapport complet
    path = gen.save_report(briefs, output_dir)
    logger.info("Cahiers des charges complets sauvegardés: %s", path)


# ─────────────────────────────────────────────────────────────────────────────
# Mode generate : génère les images des CdCs approuvées
# ─────────────────────────────────────────────────────────────────────────────

def generate_approved(
    manifest_path: Optional[str] = None,
    approve: Optional[str] = None,
    images: int = DEFAULT_IMAGES_PER_BRIEF,
    yes: bool = False,
    output_dir: str = "./output/spoonflower",
    market: str = "spoonflower",
) -> None:
    """
    Génère les images Runware pour les CdCs approuvées dans un manifest.

    Si --approve est fourni (liste de noms), crée un manifest temporaire
    avec ces niches approuvées (les autres ignorées).
    """
    from trend_discovery.generators.approval_gate import ApprovalGate

    gate = ApprovalGate()

    # ── Résolution du manifest ─────────────────────────────────────────────────
    if approve:
        # Inline approval: build a minimal manifest from brief data
        approved_names = [n.strip() for n in approve.split(",") if n.strip()]
        logger.info("[generate] approbation inline: %s", approved_names)
        from trend_discovery.generators.approval_gate import BriefApproval
        approvals = [
            BriefApproval(niche_name=n, opportunity_score=0.0, approved=True, images_count=images)
            for n in approved_names
        ]
    else:
        resolved = manifest_path or gate.find_latest_manifest()
        if not resolved:
            print(
                "ERROR: Aucun manifest d'approbation trouvé. "
                "Lancez 'preview' d'abord, puis approuvez les CdCs."
            )
            import sys
            sys.exit(1)
        logger.info("[generate] manifest: %s", resolved)
        approvals = gate.load_approved(resolved)

    cost = gate.estimate_cost(approvals)
    print(
        f"Approuvé: {len(approvals)} CdC(s) → {cost['n_images']} images → "
        f"~{cost['cost_eur']:.3f}€"
    )

    if not yes:
        answer = input("Proceed? [yes/no] ").strip().lower()
        if answer not in ("yes", "y"):
            print("Annulé.")
            return

    # ── Chargement des briefs persistés (evite de relancer Gemini) ───────────
    brief_map: Dict = {}
    if not approve:
        # Essaie de charger depuis le fichier briefs_RUNID.json du même run
        run_id = gate.get_run_id_from_manifest(manifest_path or gate.find_latest_manifest() or "")
        if run_id:
            brief_map = gate.load_brief_data(run_id)
            if brief_map:
                logger.info("[generate] %d briefs chargés depuis briefs_%s.json", len(brief_map), run_id)
            else:
                logger.warning("[generate] briefs_%s.json introuvable — relance Gemini", run_id)

    # Fallback : re-générer les briefs via Gemini si introuvables
    if not brief_map:
        logger.info("[generate] génération des briefs via Gemini (fallback)…")
        from trend_discovery.generators.production_brief import BriefGenerator
        from trend_discovery.markets.market_profile import get_profile
        profile = get_profile(market)
        gen = BriefGenerator(profile)
        briefs = gen.generate_all()
        brief_map = {b.name.lower(): b for b in briefs}

    # ── Pipeline de génération ────────────────────────────────────────────────
    generated = 0
    try:
        from trend_discovery.generators.generation_pipeline import GenerationPipeline
        from trend_discovery.generators.quality_auditor import QualityAuditor
        gen_pipeline = GenerationPipeline(output_dir=output_dir, upscale_factor=4)
        auditor = QualityAuditor()
        if not gen_pipeline._runware.is_available():
            logger.error("[generate] RUNWARE_API_KEY absente — impossible de générer des images.")
            return
    except Exception as exc:
        logger.error("[generate] GenerationPipeline indisponible: %s", exc)
        return

    for approval in approvals:
        brief_data = brief_map.get(approval.niche_name.lower())
        if brief_data is None:
            logger.warning("[generate] CdC '%s' introuvable.", approval.niche_name)
            continue
        try:
            # brief_data peut être un ProductionBrief (fallback Gemini) ou un dict (chargé JSON)
            if isinstance(brief_data, dict):
                from trend_discovery.generators.production_brief import ProductionBrief
                brief = ProductionBrief(
                    name=brief_data["name"],
                    trending_score=0,
                    market_opportunity="",
                    why_trending="",
                    target_audience="",
                    sub_niches=[],
                    positive_prompt=brief_data.get("positive_prompt", ""),
                    negative_prompt=brief_data.get("negative_prompt", ""),
                    cfg_scale=float(brief_data.get("cfg_scale", 7.5)),
                )
            else:
                brief = brief_data

            results = gen_pipeline.run_brief(brief, n_images=approval.images_count, auditor=auditor)
            ok = sum(1 for r in results if getattr(r, "success", False))
            generated += ok
            logger.info("[generate] '%s' → %d/%d images générées", approval.niche_name, ok, approval.images_count)
        except Exception as exc:
            logger.warning("[generate] '%s' génération échouée: %s", approval.niche_name, exc)

    print(f"\n{generated} image(s) générée(s) → {output_dir}")


# ─────────────────────────────────────────────────────────────────────────────
# Mode archive : CdC accompli → archivé + remplacé par un CdC frais
# ─────────────────────────────────────────────────────────────────────────────

ARCHIVE_PATH = "./reports/accomplished_cdcs.json"


def archive_cdcs(
    niche_names: List[str],
    report_path: Optional[str] = None,
    replace: bool = True,
    market: str = "spoonflower",
) -> None:
    """
    Archive un ou plusieurs CdC « accomplis » (image validée commercialement) et,
    si replace=True, demande à Gemini autant de CdC frais pour les remplacer —
    en excluant tous les thèmes déjà faits (archivés + actifs restants).

    Args:
        niche_names: noms des CdC validés à archiver.
        report_path: rapport actif. Défaut : dernier rapport.
        replace: si True, régénère N nouveaux CdC à la place (1 appel Gemini, 0 image).
        market: profil marché pour la régénération.
    """
    import json
    import glob as _glob

    if not report_path:
        reports = sorted(_glob.glob("./reports/cahiers_des_charges_*.json"))
        if not reports:
            print("ERROR : Aucun rapport trouvé.")
            return
        report_path = reports[-1]

    with open(report_path, encoding="utf-8") as fh:
        data = json.load(fh)

    briefs_key = "cahiers_des_charges" if "cahiers_des_charges" in data else "briefs"
    all_briefs = data.get(briefs_key, [])
    if not all_briefs:
        print("ERROR : Aucun CdC dans le rapport.")
        return

    # ── Résolution des CdC à archiver (match exact puis partiel) ───────────────
    to_archive = []
    remaining = list(all_briefs)
    for needle_raw in niche_names:
        needle = needle_raw.strip().lower()
        match = next((b for b in remaining if b.get("name", "").lower() == needle), None)
        if not match:
            match = next((b for b in remaining if needle in b.get("name", "").lower()), None)
        if not match:
            print(f"⚠️  CdC '{needle_raw}' introuvable — ignoré.")
            continue
        to_archive.append(match)
        remaining = [b for b in remaining if b.get("name") != match.get("name")]

    if not to_archive:
        print("Aucun CdC à archiver. Disponibles : " + ", ".join(b.get("name", "") for b in all_briefs))
        return

    # ── Archivage (append au fichier d'archive) ────────────────────────────────
    archive_data = {"accomplished": []}
    if os.path.exists(ARCHIVE_PATH):
        with open(ARCHIVE_PATH, encoding="utf-8") as fh:
            archive_data = json.load(fh)
    archive_data.setdefault("accomplished", [])

    now = datetime.now(timezone.utc).isoformat()
    for b in to_archive:
        b["_archived_at"] = now
        b["_source_report"] = os.path.basename(report_path)
        archive_data["accomplished"].append(b)
        print(f"📦 Archivé : {b.get('name')}")

    with open(ARCHIVE_PATH, "w", encoding="utf-8") as fh:
        json.dump(archive_data, fh, indent=2, ensure_ascii=False)
    print(f"   → {ARCHIVE_PATH} ({len(archive_data['accomplished'])} CdC accomplis au total)")

    # ── Régénération des remplaçants ──────────────────────────────────────────
    new_briefs = []
    if replace:
        n_needed = len(to_archive)
        # Tous les thèmes à exclure : actifs restants + tout l'historique accompli
        done_names = (
            [b.get("name", "") for b in remaining]
            + [b.get("name", "") for b in archive_data["accomplished"]]
        )
        done_names = [n for n in done_names if n]

        print(f"\n🔄 Régénération de {n_needed} CdC frais (exclusion de {len(done_names)} thèmes déjà faits)…")

        from trend_discovery.generators.production_brief import BriefGenerator
        from trend_discovery.markets.market_profile import get_profile

        profile = get_profile(market)
        profile.niche_count = n_needed
        gen = BriefGenerator(profile)

        if not gen._gemini.is_available():
            print("⚠️  GEMINI_API_KEY absente — impossible de régénérer. CdC archivés sans remplacement.")
        else:
            constraints = (
                "These themes are ALREADY DONE or in production — do NOT propose them or anything "
                "visually similar; find genuinely different fresh niches: " + ", ".join(done_names)
            )
            fresh = gen.generate_all(constraints)
            new_briefs = [b.to_dict() for b in fresh][:n_needed]
            for nb in new_briefs:
                print(f"✨ Nouveau CdC : {nb.get('name')} (score {nb.get('opportunity_score', nb.get('trending_score', '?'))})")

    # ── Réécriture du rapport actif : remaining + nouveaux ─────────────────────
    data[briefs_key] = remaining + new_briefs
    data["total_briefs"] = len(data[briefs_key])
    data["_last_archive_at"] = now
    with open(report_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, ensure_ascii=False)

    print(f"\n✅ Rapport actif mis à jour : {report_path}")
    print(f"   {len(remaining)} CdC conservés + {len(new_briefs)} nouveaux = {len(data[briefs_key])} actifs")
    if new_briefs:
        print("→ Lancez 'generate-all' ou 'generate-best' pour générer les images des nouveaux CdC.")


# ─────────────────────────────────────────────────────────────────────────────
# Mode audit : note /100 chaque image via Gemini Vision
# ─────────────────────────────────────────────────────────────────────────────

def run_audit(
    image_dir: str = "./output/spoonflower",
    report_path: Optional[str] = None,
    output_dir: str = "./reports",
) -> None:
    """
    Audit visuel de toutes les images générées via Gemini Vision.

    Pour chaque PNG dans image_dir :
      - Envoie à Gemini Vision + test 2×2 de tuilage
      - Score /100 + liste précise de problèmes (anatomie, style, texte, layout, tuilage)
      - Verdict : pass / fix / reject

    Génère un rapport MD + JSON dans output_dir.
    """
    import json
    import glob as _glob
    from trend_discovery.generators.visual_auditor import VisualAuditor, _safe_name

    auditor = VisualAuditor()
    if not auditor.is_available():
        logger.error("[audit] GEMINI_API_KEY absente — impossible d'auditer.")
        return

    # Charge la map CdC pour le contexte
    if not report_path:
        reports = sorted(_glob.glob("./reports/cahiers_des_charges_*.json"))
        report_path = reports[-1] if reports else None

    cdc_map: Dict = {}
    if report_path and os.path.exists(report_path):
        with open(report_path, encoding="utf-8") as fh:
            data = json.load(fh)
        for b in data.get("cahiers_des_charges", data.get("briefs", [])):
            cdc_map[_safe_name(b.get("name", ""))] = b

    md_path, json_path = auditor.audit_directory(image_dir, cdc_map, output_dir)
    if md_path:
        print(f"\n✅ Rapport d'audit : {md_path}")
        print(f"   JSON          : {json_path}")
    else:
        print("❌ Audit échoué — vérifiez GEMINI_API_KEY et les images dans " + image_dir)


# ─────────────────────────────────────────────────────────────────────────────
# Mode generate-best : variantes du meilleur CdC du dernier rapport
# ─────────────────────────────────────────────────────────────────────────────

def generate_all_base(
    report_path: Optional[str] = None,
    yes: bool = False,
    output_dir: str = "./output/spoonflower",
    limit: Optional[int] = None,
    niche_names: Optional[List[str]] = None,
) -> None:
    """
    Génère 1 image de base (prompt original) pour CHAQUE CdC du rapport.
    Idéal pour calibration : ~0.006 € × N CdCs.

    Args:
        limit: si fourni, ne génère que les N premiers CdC (test rapide).
        niche_names: si fourni, ne génère que ces CdC précis (match partiel).
    """
    import json
    import glob as _glob

    if not report_path:
        reports = sorted(_glob.glob("./reports/cahiers_des_charges_*.json"))
        if not reports:
            print("ERROR : Aucun rapport trouvé. Lancez 'preview' d'abord.")
            return
        report_path = reports[-1]

    logger.info("[generate-all] rapport : %s", report_path)

    with open(report_path, encoding="utf-8") as fh:
        data = json.load(fh)

    all_briefs = data.get("cahiers_des_charges", data.get("briefs", []))
    if not all_briefs:
        print("ERROR : Aucun CdC dans le rapport.")
        return

    # Filtrage : niches ciblées prioritaires, sinon limite sur les N premiers
    if niche_names:
        selected = []
        for needle_raw in niche_names:
            needle = needle_raw.strip().lower()
            m = next((b for b in all_briefs if b.get("name", "").lower() == needle), None)
            if not m:
                m = next((b for b in all_briefs if needle in b.get("name", "").lower()), None)
            if m and m not in selected:
                selected.append(m)
            elif not m:
                print(f"⚠️  CdC '{needle_raw}' introuvable — ignoré.")
        all_briefs = selected
    elif limit and limit > 0:
        all_briefs = all_briefs[:limit]

    if not all_briefs:
        print("ERROR : Aucun CdC sélectionné.")
        return

    n = len(all_briefs)
    cost_est = n * 0.006
    print("\n" + "=" * 60)
    print(f"  {n} CdCs → 1 image de base chacun")
    print(f"  Coût estimé : ~{cost_est:.3f} € ({n} images × ~0.006 €)")
    print("  Rapport : " + report_path)
    print("=" * 60)
    for i, b in enumerate(all_briefs, 1):
        print(f"  {i:2d}. {b.get('name')}")
    print()

    if not yes:
        answer = input("Proceed? [yes/no] ").strip().lower()
        if answer not in ("yes", "y"):
            print("Annulé.")
            return

    try:
        from trend_discovery.generators.generation_pipeline import GenerationPipeline
        from trend_discovery.generators.quality_auditor import QualityAuditor
        # tiling=False for standalone illustration platforms (not seamless repeat)
        _standalone_platforms = ("redbubble",)
        tiling = not any(p in output_dir.lower() for p in _standalone_platforms)
        # Bloc "generation" optionnel à la racine du rapport : permet à un CdC
        # d'imposer modèle/résolution/upscale (ex. FLUX.2 Dev 2048px + ×2 → 4096).
        gen_cfg = data.get("generation", {}) or {}
        if gen_cfg:
            logger.info("[generate-all] overrides generation du CdC : %s", gen_cfg)
        pipeline = GenerationPipeline(
            output_dir=output_dir,
            upscale_factor=int(gen_cfg.get("upscale_factor", 4)),
            tiling=tiling,
            model=gen_cfg.get("model"),
            gen_width=gen_cfg.get("width"),
            gen_height=gen_cfg.get("height"),
            steps=gen_cfg.get("steps"),
            min_px=gen_cfg.get("target_px"),
        )
        auditor = QualityAuditor()
    except Exception as exc:
        logger.error("[generate-all] GenerationPipeline indisponible : %s", exc)
        return

    if not pipeline._runware.is_available():
        logger.error("[generate-all] RUNWARE_API_KEY absente — impossible de générer.")
        return

    from trend_discovery.generators.variant_engine import VariantEngine
    engine = VariantEngine()

    total_ok = 0
    for brief in all_briefs:
        name = brief.get("name", "?")
        logger.info("[generate-all] '%s'…", name)
        variants = engine.generate_variants(brief, all_briefs=[], n_fusions=0)
        if not variants:
            logger.warning("[generate-all] Aucune variante pour '%s' — ignoré", name)
            continue
        base_variant = variants[:1]  # Base uniquement
        results = pipeline.run_variants(brief, base_variant, auditor=auditor)
        ok = sum(1 for r in results if r.success)
        total_ok += ok
        status = "✅" if ok else "❌"
        print(f"  {status} {name}")

    print(f"\n{total_ok}/{n} image(s) générée(s) → {output_dir}")

    # Update niche archive so future preview runs don't repeat these
    try:
        import json as _json
        _archive_path = "data/niche_archive.json"
        _archive: dict = {"niches": []}
        if os.path.exists(_archive_path):
            with open(_archive_path) as _fh:
                _archive = _json.load(_fh)
        _existing = {n["name"].lower() for n in _archive.get("niches", [])}
        from datetime import datetime as _dt
        _now = _dt.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")
        for brief in all_briefs:
            _name = brief.get("name", "")
            if _name and _name.lower() not in _existing:
                _archive.setdefault("niches", []).append({"name": _name, "generated_at": _now})
                _existing.add(_name.lower())
        with open(_archive_path, "w") as _fh:
            _json.dump(_archive, _fh, indent=2, ensure_ascii=False)
        logger.info("[generate-all] archive niches mis à jour (%d total)", len(_archive["niches"]))
    except Exception as _exc:
        logger.warning("[generate-all] archive niches non mis à jour : %s", _exc)


def generate_best_variants(
    report_path: Optional[str] = None,
    n_fusions: int = 2,
    yes: bool = False,
    output_dir: str = "./output/spoonflower",
    niche_name: Optional[str] = None,
    max_variants: Optional[int] = None,
) -> None:
    """
    Auto-sélectionne le meilleur CdC du dernier rapport et génère toutes ses variantes.
    Si niche_name est fourni, cible ce CdC précis plutôt que le meilleur score.
    Si max_variants est fourni, seules les N premières variantes sont générées.

    Variantes produites (1 image chacune) :
      • Base           — le prompt original du CdC
      • Sub-niches     — 1 image par sous-niche (jusqu'à 4)
      • Style: Dark    — palette sombre dramatique
      • Style: Minimal — line art monochrome
      • Fusions        — croisement avec 2 autres CdCs du même rapport

    Total typique : 9 images distinctes pour ~0.05 €.
    """
    import json
    import glob as _glob

    # Résolution du rapport
    if not report_path:
        reports = sorted(_glob.glob("./reports/cahiers_des_charges_*.json"))
        if not reports:
            print("ERROR : Aucun rapport trouvé. Lancez 'preview' d'abord.")
            return
        report_path = reports[-1]

    logger.info("[generate-best] rapport : %s", report_path)

    with open(report_path, encoding="utf-8") as fh:
        data = json.load(fh)

    all_briefs = data.get("cahiers_des_charges", data.get("briefs", []))
    if not all_briefs:
        print("ERROR : Aucun CdC dans le rapport.")
        return

    def _score(b: dict) -> float:
        return float(b.get("opportunity_score", b.get("trending_score", 0)))

    if niche_name:
        # Cible un CdC précis par nom (insensible à la casse)
        needle = niche_name.strip().lower()
        match = next((b for b in all_briefs if b.get("name", "").lower() == needle), None)
        if not match:
            # Recherche partielle si pas de correspondance exacte
            match = next((b for b in all_briefs if needle in b.get("name", "").lower()), None)
        if not match:
            available = [b.get("name") for b in all_briefs]
            print(f"ERROR : CdC '{niche_name}' introuvable. Disponibles : {available}")
            return
        best = match
        others = [b for b in all_briefs if b.get("name") != best.get("name")]
    else:
        # Meilleur CdC = score le plus élevé
        sorted_briefs = sorted(all_briefs, key=_score, reverse=True)
        best = sorted_briefs[0]
        others = sorted_briefs[1:]

    from trend_discovery.generators.variant_engine import VariantEngine
    engine = VariantEngine()
    variants = engine.generate_variants(best, all_briefs=others, n_fusions=n_fusions)

    if max_variants and max_variants > 0:
        variants = variants[:max_variants]

    print("\n" + "=" * 60)
    print(f"  MEILLEUR CdC : {best.get('name')} (score {best.get('trending_score')}/100)")
    print(f"  {len(variants)} variante(s) à générer :")
    for i, v in enumerate(variants, 1):
        print(f"    {i:2d}. {v}")
    cost_est = len(variants) * 0.006
    print(f"\n  Coût estimé : ~{cost_est:.3f} € ({len(variants)} images × ~0.006 €)")
    print("=" * 60)

    if not yes:
        answer = input("\nProceed? [yes/no] ").strip().lower()
        if answer not in ("yes", "y"):
            print("Annulé.")
            return

    try:
        from trend_discovery.generators.generation_pipeline import GenerationPipeline
        from trend_discovery.generators.quality_auditor import QualityAuditor
        pipeline = GenerationPipeline(output_dir=output_dir, upscale_factor=4)
        auditor = QualityAuditor()
    except Exception as exc:
        logger.error("[generate-best] GenerationPipeline indisponible : %s", exc)
        return

    if not pipeline._runware.is_available():
        logger.error("[generate-best] RUNWARE_API_KEY absente — impossible de générer.")
        return

    results = pipeline.run_variants(best, variants, auditor=auditor)
    ok = sum(1 for r in results if r.success)

    print(f"\n{ok}/{len(results)} image(s) générée(s) → {output_dir}")
    for r in results:
        print(f"  {r}")


# ─────────────────────────────────────────────────────────────────────────────
# Mode colorize : variantes de coloris sur images existantes (0 Runware)
# ─────────────────────────────────────────────────────────────────────────────

def colorize_images(
    input_dir: str = "./output/spoonflower",
    output_dir: str = "./output/colorways",
    palettes: Optional[List[str]] = None,
    glob_pattern: str = "*.png",
    yes: bool = False,
    smart: bool = False,
    reports_dir: str = "./reports",
) -> None:
    """
    Génère des variantes de coloris pour tous les PNGs d'un dossier.

    Principe : rotation HSV (hue_shift + sat_mult + val_mult).
    Aucun appel Runware — 100% gratuit. Détail préservé intégralement.

    Si smart=True : lit les CDCs pour choisir les 4 palettes les plus adaptées
    à chaque design plutôt que les 4 génériques.

    Palettes disponibles : cool_ocean, forest_dusk, rose_gold, midnight,
                           lavender_mist, earth_autumn, sage_morning, deep_ruby
    (Alias legacy : dark_moody, pastel_soft, earth_tones, navy_mono, etc.)
    """
    import glob as _glob
    from trend_discovery.generators.color_rewriter import ColorRewriter, PALETTES

    files = sorted(_glob.glob(os.path.join(input_dir, glob_pattern)))
    # Exclure les colorways déjà générés (pas de récursion)
    files = [f for f in files if "__" not in os.path.basename(f)]

    if not files:
        print(f"ERROR : Aucun PNG trouvé dans {input_dir} (pattern: {glob_pattern})")
        return

    pal_names = palettes or list(PALETTES.keys())
    mode_label = "SMART (palettes CDC)" if smart else "standard"
    n_out = len(files) * (4 if smart else len(pal_names))

    print("\n" + "=" * 60)
    print(f"  COLORIZE — variantes de palette {mode_label} (Pillow, 0 coût Runware)")
    if not smart:
        print(f"  {len(files)} image(s) source × {len(pal_names)} palette(s) = {n_out} colorways")
        print(f"  Palettes : {', '.join(pal_names)}")
    else:
        print(f"  {len(files)} image(s) source × 4 palettes CDC-adaptées ≈ {n_out} colorways")
    print(f"  Sortie   : {output_dir}/")
    print("=" * 60)
    for i, f in enumerate(files, 1):
        print(f"  {i:2d}. {os.path.basename(f)}")
    print()

    if not yes:
        answer = input("Proceed? [yes/no] ").strip().lower()
        if answer not in ("yes", "y"):
            print("Annulé.")
            return

    rewriter = ColorRewriter()
    if smart:
        results = rewriter.batch_recolor_smart(
            input_dir=input_dir,
            reports_dir=reports_dir,
            output_dir=output_dir,
            glob_pattern=glob_pattern,
            fallback_palettes=pal_names or None,
        )
    else:
        results = rewriter.batch_recolor(
            input_dir=input_dir,
            palette_names=pal_names,
            output_dir=output_dir,
            glob_pattern=glob_pattern,
        )

    total_ok = sum(len(v) for v in results.values())
    print(f"\n✅ {total_ok} colorways générés → {output_dir}/")


# ─────────────────────────────────────────────────────────────────────────────
# Mode bg-remove : suppression fond blanc pour stickers Redbubble
# ─────────────────────────────────────────────────────────────────────────────

def remove_backgrounds(
    input_dir: str = "./output/redbubble",
    output_dir: str = "./output/redbubble",
    tolerance: int = 28,
    yes: bool = False,
) -> None:
    """
    Supprime le fond blanc de tous les PNGs d'un dossier (flood-fill BFS depuis les 4 coins).
    Génère des PNG RGBA transparents prêts pour die-cut sticker sur Redbubble.
    """
    import glob as _glob
    from trend_discovery.generators.bg_remover import batch_remove_background

    files = sorted(_glob.glob(os.path.join(input_dir, "*.png")))
    files = [f for f in files if "_transparent" not in os.path.basename(f)]

    if not files:
        print(f"ERROR : Aucun PNG trouvé dans {input_dir}")
        return

    print("\n" + "=" * 60)
    print(f"  BG-REMOVE — suppression fond blanc (flood-fill BFS)")
    print(f"  {len(files)} image(s) | tolérance {tolerance} | sortie RGBA transparent")
    print(f"  Source  : {input_dir}/")
    print(f"  Sortie  : {output_dir}/")
    print("=" * 60)
    for i, f in enumerate(files, 1):
        print(f"  {i:2d}. {os.path.basename(f)}")
    print()

    if not yes:
        answer = input("Proceed? [yes/no] ").strip().lower()
        if answer not in ("yes", "y"):
            print("Annulé.")
            return

    generated = batch_remove_background(
        input_dir=input_dir,
        output_dir=output_dir,
        tolerance=tolerance,
        skip_existing=True,
    )
    print(f"\n✅ {len(generated)} PNG transparents → {output_dir}/")


# ─────────────────────────────────────────────────────────────────────────────
# Mode seamless-audit : vérification + correction automatique des tuiles
# ─────────────────────────────────────────────────────────────────────────────

def seamless_audit(
    input_dir: str = "./output/spoonflower",
    output_dir: Optional[str] = None,
    fix: bool = True,
    overwrite: bool = False,
    threshold: float = 12.0,
    yes: bool = False,
) -> None:
    """
    Audite tous les PNGs d'un dossier et corrige les tuiles non-seamless.

    Méthode : mirror quad 2×2 (orig | flip_H / flip_V | rot180).
    La symétrie garantit ZÉRO couture visible.
    L'image corrigée est redimensionnée à 4500×4500 px 300 DPI.

    Si overwrite=False : les images corrigées sont sauvegardées avec le suffixe
    __seamless.png ; l'original est préservé.
    """
    import glob as _glob
    from trend_discovery.generators.seamless_auditor import SeamlessAuditor

    files = sorted(_glob.glob(os.path.join(input_dir, "*.png")))
    files = [f for f in files if "__seamless" not in os.path.basename(f)]

    if not files:
        print(f"Aucun PNG trouvé dans {input_dir}")
        return

    auditor = SeamlessAuditor(threshold=threshold)

    print("\n" + "=" * 60)
    print(f"  SEAMLESS AUDIT — vérification + correction")
    print(f"  {len(files)} image(s) | seuil MAD={threshold} | fix={fix}")
    print(f"  Dossier : {input_dir}/")
    print("=" * 60)

    if not yes:
        answer = input("Proceed? [yes/no] ").strip().lower()
        if answer not in ("yes", "y"):
            print("Annulé.")
            return

    report = auditor.audit_and_fix_dir(
        input_dir=input_dir,
        output_dir=output_dir,
        fix=fix,
        overwrite=overwrite,
    )

    n_ok  = sum(1 for e in report.values() if e.get("is_seamless"))
    n_fix = sum(1 for e in report.values() if e.get("was_fixed"))
    print(f"\n✅ Audit terminé : {n_ok}/{len(report)} déjà seamless | {n_fix} corrigées")

    report_path = auditor.save_report(report)
    print(f"   Rapport → {report_path}")


# ─────────────────────────────────────────────────────────────────────────────
# Mode thumbnails : vignettes + planches-contact navigables dans GitHub
# ─────────────────────────────────────────────────────────────────────────────

def generate_thumbnails(
    pipeline_dir: str = "./output/spoonflower",
    colorways_dir: str = "./output/colorways",
    uploads_dir: str = "./output/uploads/base",
    uploads_colorways_dir: str = "./output/uploads/colorways",
    output_root: str = "./output/thumbnails",
    contact_sheets: bool = True,
) -> None:
    """
    Génère des miniatures JPEG (600×600) + planches-contact pour tous les dossiers.

    Sortie : output/thumbnails/
      pipeline/        — 1 JPG par image pipeline
      colorways/       — 1 JPG par colorway
      uploads/         — 1 JPG par upload utilisateur
      uploads_colorways/
      contact_pipeline.jpg
      contact_colorways.jpg
      contact_uploads.jpg

    Taille typique : ~50-100 KB/vignette → git-safe.
    """
    from trend_discovery.generators.thumbnail_generator import ThumbnailGenerator

    gen = ThumbnailGenerator()
    gen.generate_all(
        pipeline_dir=pipeline_dir,
        colorways_dir=colorways_dir,
        uploads_dir=uploads_dir,
        uploads_colorways_dir=uploads_colorways_dir,
        output_root=output_root,
        make_contact_sheets=contact_sheets,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Mode generate-elements : 10 éléments isolés + assemblage Pillow
# ─────────────────────────────────────────────────────────────────────────────

def generate_elements(
    report_path: Optional[str] = None,
    niche_name: Optional[str] = None,
    yes: bool = False,
    output_dir: str = "./output/spoonflower",
) -> None:
    """
    Génère 10 éléments isolés via Runware puis les assemble en pattern seamless
    avec PatternAssembler (Pillow, gratuit).

    Pipeline :
      1. Charge le dernier rapport CdC
      2. Sélectionne le brief par niche_name ou meilleur opportunity_score
      3. ElementGenerator → 10 appels Runware (un par élément)
      4. PatternAssembler → canvas 2048×2048 seamless
      5. SpoonflowerPackager → PNG 4500×4500 300 DPI prêt à uploader
    """
    import json
    import glob as _glob

    # Résolution du rapport
    if not report_path:
        reports = sorted(_glob.glob("./reports/cahiers_des_charges_*.json"))
        if not reports:
            print("ERROR : Aucun rapport trouvé. Lancez 'preview' d'abord.")
            return
        report_path = reports[-1]

    logger.info("[generate-elements] rapport : %s", report_path)

    with open(report_path, encoding="utf-8") as fh:
        data = json.load(fh)

    all_briefs = data.get("cahiers_des_charges", data.get("briefs", []))
    if not all_briefs:
        print("ERROR : Aucun CdC dans le rapport.")
        return

    def _score(b: dict) -> float:
        return float(b.get("opportunity_score", b.get("trending_score", 0)))

    if niche_name:
        needle = niche_name.strip().lower()
        brief = next((b for b in all_briefs if b.get("name", "").lower() == needle), None)
        if not brief:
            brief = next((b for b in all_briefs if needle in b.get("name", "").lower()), None)
        if not brief:
            available = [b.get("name") for b in all_briefs]
            print(f"ERROR : CdC '{niche_name}' introuvable. Disponibles : {available}")
            return
    else:
        brief = sorted(all_briefs, key=_score, reverse=True)[0]

    elements = brief.get("elements", [])
    n_elements = len(elements[:10])
    cost_est = n_elements * 0.006

    print("\n" + "=" * 60)
    print(f"  CdC : {brief.get('name')} (score {brief.get('trending_score')}/100)")
    print(f"  {n_elements} éléments à générer (max 10 appels Runware)")
    print(f"  Coût estimé : ~{cost_est:.3f} € ({n_elements} images × ~0.006 €)")
    print("=" * 60)

    if not yes:
        answer = input("\nProceed? [yes/no] ").strip().lower()
        if answer not in ("yes", "y"):
            print("Annulé.")
            return

    from trend_discovery.generators.element_generator import ElementGenerator
    gen = ElementGenerator()

    if not gen.is_available():
        logger.error("[generate-elements] RUNWARE_API_KEY absente — impossible de générer.")
        return

    # Génération des éléments
    generated = gen.generate_all(brief)
    if not generated:
        logger.error("[generate-elements] Aucun élément généré.")
        return

    # Sauvegarde des éléments individuels (PNG transparent) + manifest
    elements_dir = gen.save_elements(generated, brief, output_dir="./output/elements")
    import os as _os
    manifest_path = _os.path.join(elements_dir, "manifest.json")
    print(f"\nÉléments sauvegardés : {elements_dir}")
    print(f"Manifest : {manifest_path}")
    print("→ Réassemblage futur : python -m trend_discovery.main assemble --manifest <path>")

    # Assemblage par défaut (tous les éléments, assembly_guide du CdC)
    from trend_discovery.generators.pattern_assembler import PatternAssembler
    assembler = PatternAssembler()
    assembly_guide = brief.get("assembly_guide", {})
    pattern_bytes = assembler.assemble(generated, assembly_guide)

    if not pattern_bytes:
        logger.error("[generate-elements] Assemblage échoué.")
        return

    # Packaging Spoonflower
    from trend_discovery.generators.spoonflower_packager import SpoonflowerPackager
    packager = SpoonflowerPackager(output_dir=output_dir)
    filepath = packager.package(pattern_bytes, brief.get("name", "elements_pattern"))

    if filepath:
        print(f"Pattern assemblé : {filepath}")
    else:
        logger.error("[generate-elements] Packaging échoué.")


# ─────────────────────────────────────────────────────────────────────────────
# Mode listings : génère les fiches produit CSV + Markdown par plateforme
# ─────────────────────────────────────────────────────────────────────────────

def generate_listings(
    reports_dir: str = "./reports",
    output_dir: str = "./reports/listings",
) -> None:
    """
    Génère les fiches produit prêtes-à-publier (titre, description, tags, catégorie)
    pour chaque CdC × chaque plateforme configurée.

    Lit le dernier rapport CdC JSON et produit :
      - listings_YYYYMMDD.json  — toutes les fiches
      - listings_YYYYMMDD.md    — format copier-coller par plateforme
    """
    import glob as _glob
    from trend_discovery.generators.listing_exporter import ListingExporter

    # Trouve le dernier rapport CdC JSON dans reports_dir
    pattern = os.path.join(reports_dir, "cahiers_des_charges_*.json")
    reports = sorted(_glob.glob(pattern))
    if not reports:
        # Essai dans le répertoire principal
        reports = sorted(_glob.glob("./reports/cahiers_des_charges_*.json"))
    if not reports:
        print(f"ERROR : Aucun rapport CdC trouvé dans {reports_dir}")
        return

    latest = reports[-1]
    logger.info("[listings] rapport : %s", latest)

    exporter = ListingExporter()
    out_path = exporter.export_all(latest, output_dir)
    print(f"✅ Listings exportés → {output_dir}/")
    return out_path


# ─────────────────────────────────────────────────────────────────────────────
# Mode text-apply : applique la typographie CDC sur les images générées
# ─────────────────────────────────────────────────────────────────────────────

def apply_text(
    images_dir: str = "./output/redbubble",
    reports_dir: str = "./reports/redbubble",
    output_dir: Optional[str] = None,
    overwrite: bool = False,
) -> None:
    """
    Applique la typographie définie dans le CDC sur chaque image générée.

    Lit le dernier CDC Redbubble JSON, fait correspondre chaque PNG à son
    brief via le slug du nom de niche, puis applique les couches de texte
    définies dans `typography.layers` avec PIL (polices système, précision
    300 DPI).

    Args:
        images_dir:  Dossier contenant les PNG Redbubble générés.
        reports_dir: Dossier contenant les CDC JSON Redbubble.
        output_dir:  Dossier de sortie (None = écrase les originaux).
        overwrite:   Re-applique même si le fichier de sortie existe déjà.
    """
    import glob as _glob
    from trend_discovery.generators.text_applicator import batch_apply_typography

    pattern = os.path.join(reports_dir, "cahiers_des_charges_*.json")
    cdcs = sorted(_glob.glob(pattern))
    if not cdcs:
        print(f"ERROR : Aucun CDC trouvé dans {reports_dir}")
        return

    latest_cdc = cdcs[-1]
    logger.info("[text-apply] CDC : %s", latest_cdc)
    logger.info("[text-apply] images : %s", images_dir)

    processed = batch_apply_typography(
        cdc_json_path=latest_cdc,
        images_dir=images_dir,
        output_dir=output_dir,
        overwrite=overwrite,
    )
    print(f"✅ Typographie appliquée sur {len(processed)} image(s)")
    if output_dir:
        print(f"   → {output_dir}/")


# ─────────────────────────────────────────────────────────────────────────────
# Mode assemble : illustrations individuelles → seamless tile Spoonflower
# ─────────────────────────────────────────────────────────────────────────────

def assemble_specimens(
    input_dir: str = "./output/redbubble",
    output_dir: str = "./output/spoonflower",
    background: str = "navy",
    n_specimens: int = 9,
    scale_min: float = 0.14,
    scale_max: float = 0.30,
    rotation_range: float = 18.0,
    tile_size: int = 4500,
    seed: int = 42,
    variants: int = 3,
    yes: bool = False,
) -> None:
    """
    Assemble des illustrations individuelles (PNGs standalone) en seamless tile
    pour Spoonflower — aucun appel Runware, 100% Pillow.

    Les illustrations sources sont placées en scatter tossed sur un fond uni
    avec wrapping seamless (éléments dupliqués sur les bords opposés).
    Le tile résultant est 4500×4500px 300 DPI, prêt pour Spoonflower.

    Args:
        input_dir:       Dossier des PNGs sources (illustrations individuelles).
        output_dir:      Dossier de sortie des tiles seamless.
        background:      Fond : 'navy', 'charcoal', 'forest', 'ivory', 'cream',
                         'white', 'slate', ou un code #HEX direct.
        n_specimens:     Nombre d'illustrations à placer par tile.
        scale_min/max:   Plage de taille relative des illustrations (fraction du tile).
        rotation_range:  Rotation max en degrés (±).
        tile_size:       Taille du tile en pixels (défaut: 4500).
        seed:            Graine aléatoire pour reproductibilité.
        variants:        Nombre de compositions différentes à générer.
        yes:             Auto-confirmer (mode CI).
    """
    import glob as _glob
    from trend_discovery.generators.specimen_assembler import batch_assemble, BACKGROUNDS

    files = sorted(_glob.glob(os.path.join(input_dir, "*.png")))
    files = [f for f in files if "_seamless" not in os.path.basename(f)
             and "thumbnail" not in os.path.basename(f).lower()]

    if not files:
        print(f"ERROR : Aucun PNG trouvé dans {input_dir}")
        return

    bg_hex = BACKGROUNDS.get(background, background)

    print("\n" + "=" * 60)
    print("  ASSEMBLE — illustrations → seamless tile Spoonflower (Pillow, 0 coût)")
    print(f"  {len(files)} illustration(s) source")
    print(f"  {n_specimens} specimens par tile | {variants} variante(s)")
    print(f"  Fond : {background} ({bg_hex}) | tile {tile_size}×{tile_size}px 300 DPI")
    print(f"  Source  : {input_dir}/")
    print(f"  Sortie  : {output_dir}/")
    print("=" * 60)
    for i, f in enumerate(files, 1):
        print(f"  {i:2d}. {os.path.basename(f)}")
    print()

    if not yes:
        answer = input("Proceed? [yes/no] ").strip().lower()
        if answer not in ("yes", "y"):
            print("Annulé.")
            return

    results = batch_assemble(
        input_dir=input_dir,
        output_dir=output_dir,
        background=background,
        n_specimens=n_specimens,
        scale_min=scale_min,
        scale_max=scale_max,
        rotation_range=rotation_range,
        tile_size=tile_size,
        seed=seed,
        variants=variants,
    )

    print(f"\n✅ {len(results)} tile(s) seamless → {output_dir}/")
    for r in results:
        print(f"   {os.path.basename(r)}")


# ─────────────────────────────────────────────────────────────────────────────
# Mode text-fix : érase texte FLUX + applique typo CDC propre
# ─────────────────────────────────────────────────────────────────────────────

def fix_text(
    images_dir: str = "./output/redbubble",
    reports_dir: str = "./reports/redbubble",
    output_dir: Optional[str] = None,
    overwrite: bool = False,
    erase_only: bool = False,
) -> None:
    """
    Corrige les images où FLUX a rendu du texte illisible ou déformé.

    Pipeline en 2 étapes :
      1. Gemini Vision détecte les régions de texte → PIL les remplace par
         la couleur de fond estimée (gratuit, 0 Runware).
      2. La typographie propre définie dans le CDC est appliquée via PIL.

    Args:
        images_dir:  Dossier contenant les PNG Redbubble à corriger.
        reports_dir: Dossier contenant les CDC JSON Redbubble.
        output_dir:  Dossier de sortie (None = écrase les originaux).
        overwrite:   Re-traite même si le fichier de sortie existe déjà.
        erase_only:  Si True, efface seulement le texte sans appliquer la typo.
    """
    import glob as _glob
    from trend_discovery.generators.text_applicator import batch_fix_text

    pattern = os.path.join(reports_dir, "cahiers_des_charges_*.json")
    cdcs = sorted(_glob.glob(pattern))
    if not cdcs:
        print(f"ERROR : Aucun CDC trouvé dans {reports_dir}")
        return

    latest_cdc = cdcs[-1]
    logger.info("[text-fix] CDC : %s", latest_cdc)
    logger.info("[text-fix] images : %s", images_dir)

    processed = batch_fix_text(
        cdc_json_path=latest_cdc,
        images_dir=images_dir,
        output_dir=output_dir,
        overwrite=overwrite,
        erase_only=erase_only,
    )
    print(f"✅ Texte corrigé sur {len(processed)} image(s)")
    if output_dir:
        print(f"   → {output_dir}/")


# ─────────────────────────────────────────────────────────────────────────────
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Moneymaker — Moteur de Détection de Tendances et d'Opportunités"
    )
    subparsers = parser.add_subparsers(dest="command")

    # ── Sous-commande : preview ────────────────────────────────────────────────
    preview_parser = subparsers.add_parser(
        "preview",
        help="Génère les CdCs + manifest d'approbation (0 image, 0 coût).",
    )
    preview_parser.add_argument("--market", type=str, default="spoonflower")
    preview_parser.add_argument("--niches", type=int, default=None)
    preview_parser.add_argument("--exclude", type=str, default="")
    preview_parser.add_argument("--focus", type=str, default="")
    preview_parser.add_argument("--output", type=str, default="./reports")

    # ── Sous-commande : generate ───────────────────────────────────────────────
    gen_parser = subparsers.add_parser(
        "generate",
        help="Génère les images Runware pour les CdCs approuvées.",
    )
    gen_parser.add_argument(
        "--manifest", type=str, default="",
        help="Chemin vers le manifest d'approbation (relatif à la racine du repo).",
    )
    gen_parser.add_argument(
        "--approve", type=str, default="",
        help="Liste de noms de niches séparés par des virgules (alternative au manifest).",
    )
    gen_parser.add_argument(
        "--images", type=int, default=DEFAULT_IMAGES_PER_BRIEF,
        help="Nombre d'images par CdC approuvé.",
    )
    gen_parser.add_argument(
        "--yes", action="store_true",
        help="Auto-confirmer (mode CI, pas de prompt interactif).",
    )
    gen_parser.add_argument("--market", type=str, default="spoonflower")
    gen_parser.add_argument("--output", type=str, default="./output/spoonflower")
    gen_parser.add_argument(
        "--best", action="store_true",
        help="Auto-sélectionne le meilleur CdC et génère toutes ses variantes (base + sous-niches + styles + fusions).",
    )
    gen_parser.add_argument(
        "--report", type=str, default="",
        help="Chemin vers le rapport JSON (pour --best). Défaut : dernier rapport.",
    )
    gen_parser.add_argument(
        "--fusions", type=int, default=2,
        help="Nombre de variantes fusion avec d'autres CdCs (pour --best).",
    )
    gen_parser.add_argument(
        "--niche", type=str, default="",
        help="Nom du CdC à générer (pour --best). Défaut : meilleur score.",
    )
    gen_parser.add_argument(
        "--limit", type=int, default=0,
        help="Nombre max de variantes à générer (pour --best). 0 = toutes. Ex: --limit 1 pour calibrer.",
    )

    # ── Sous-commande : archive ───────────────────────────────────────────────
    archive_parser = subparsers.add_parser(
        "archive",
        help="Archive un CdC accompli (image validée) + régénère un CdC frais à sa place.",
    )
    archive_parser.add_argument(
        "--niche", type=str, required=True,
        help="Nom(s) du/des CdC accompli(s) à archiver (séparés par des virgules).",
    )
    archive_parser.add_argument(
        "--no-replace", action="store_true",
        help="Archive seulement, sans régénérer de remplaçant via Gemini.",
    )
    archive_parser.add_argument(
        "--report", type=str, default="",
        help="Rapport actif à modifier. Défaut : dernier rapport.",
    )
    archive_parser.add_argument("--market", type=str, default="spoonflower")

    # ── Sous-commande : audit ─────────────────────────────────────────────────
    audit_parser = subparsers.add_parser(
        "audit",
        help="Audit Gemini Vision de toutes les images : note /100 + problèmes détaillés.",
    )
    audit_parser.add_argument(
        "--images", type=str, default="./output/spoonflower",
        help="Répertoire des images PNG à auditer.",
    )
    audit_parser.add_argument(
        "--report", type=str, default="",
        help="Rapport JSON des CdCs (pour le contexte). Défaut : dernier rapport.",
    )
    audit_parser.add_argument(
        "--output", type=str, default="./reports",
        help="Répertoire de sortie pour le rapport d'audit.",
    )

    # ── Sous-commande : generate-all ──────────────────────────────────────────
    gen_all_parser = subparsers.add_parser(
        "generate-all",
        help="1 image de base par CdC (calibration globale). Coût ≈ 0.006€ × nb CdCs.",
    )
    gen_all_parser.add_argument(
        "--report", type=str, default="",
        help="Chemin vers le rapport JSON. Défaut : dernier rapport.",
    )
    gen_all_parser.add_argument(
        "--yes", action="store_true",
        help="Auto-confirmer (mode CI).",
    )
    gen_all_parser.add_argument(
        "--output", type=str, default="./output/spoonflower",
        help="Répertoire de sortie.",
    )
    gen_all_parser.add_argument(
        "--limit", type=int, default=0,
        help="Ne générer que les N premiers CdC (test rapide). 0 = tous.",
    )
    gen_all_parser.add_argument(
        "--niche", type=str, default="",
        help="Cibler des CdC précis (noms séparés par virgules). Prioritaire sur --limit.",
    )

    # ── Sous-commande : colorize ──────────────────────────────────────────────
    colorize_parser = subparsers.add_parser(
        "colorize",
        help="Variantes de coloris sur images existantes — Pillow uniquement, 0 coût Runware.",
    )
    colorize_parser.add_argument(
        "--input", type=str, default="./output/spoonflower",
        help="Dossier contenant les PNGs source.",
    )
    colorize_parser.add_argument(
        "--output", type=str, default="./output/colorways",
        help="Dossier de sortie pour les colorways.",
    )
    colorize_parser.add_argument(
        "--palettes", type=str, default="",
        help="Palettes séparées par virgule (vide = toutes). Ex: dark_moody,pastel_soft",
    )
    colorize_parser.add_argument(
        "--pattern", type=str, default="*.png",
        help="Glob pattern pour filtrer les fichiers source.",
    )
    colorize_parser.add_argument(
        "--yes", action="store_true",
        help="Auto-confirmer (mode CI).",
    )
    colorize_parser.add_argument(
        "--smart", action="store_true",
        help="Sélection de palette intelligente basée sur les hex couleurs du CDC.",
    )
    colorize_parser.add_argument(
        "--reports", type=str, default="./reports",
        help="Dossier des rapports CDC (pour --smart).",
    )

    # ── Sous-commande : bg-remove ─────────────────────────────────────────────
    bg_parser = subparsers.add_parser(
        "bg-remove",
        help="Supprime le fond blanc des PNGs Redbubble → PNG RGBA transparent pour die-cut stickers.",
    )
    bg_parser.add_argument(
        "--input", type=str, default="./output/redbubble",
        help="Dossier source (PNG fond blanc).",
    )
    bg_parser.add_argument(
        "--output", type=str, default="./output/redbubble",
        help="Dossier de sortie (PNG transparent). Défaut = même dossier.",
    )
    bg_parser.add_argument(
        "--tolerance", type=int, default=28,
        help="Distance max du blanc pour être considéré fond [0-255] (défaut: 28).",
    )
    bg_parser.add_argument(
        "--yes", action="store_true",
        help="Auto-confirmer (mode CI).",
    )

    # ── Sous-commande : seamless-audit ───────────────────────────────────────
    sa_parser = subparsers.add_parser(
        "seamless-audit",
        help="Détecte et corrige automatiquement les tuiles non-seamless (mirror quad).",
    )
    sa_parser.add_argument(
        "--input", type=str, default="./output/spoonflower",
        help="Dossier des PNGs à auditer.",
    )
    sa_parser.add_argument(
        "--output", type=str, default="",
        help="Dossier de sortie (vide = même dossier que --input).",
    )
    sa_parser.add_argument(
        "--threshold", type=float, default=12.0,
        help="Seuil MAD [0-255] en dessous duquel une image est considérée seamless.",
    )
    sa_parser.add_argument(
        "--overwrite", action="store_true",
        help="Remplace les originaux (défaut : ajoute __seamless.png en parallèle).",
    )
    sa_parser.add_argument(
        "--no-fix", action="store_true",
        help="Rapport uniquement, sans correction.",
    )
    sa_parser.add_argument(
        "--yes", action="store_true",
        help="Auto-confirmer (mode CI).",
    )

    # ── Sous-commande : listings ──────────────────────────────────────────────
    ls_parser = subparsers.add_parser(
        "listings",
        help="Génère les CSVs de listing prêts à uploader (Spoonflower, Adobe Stock, Etsy, Redbubble).",
    )
    ls_parser.add_argument("--reports", type=str, default="./reports")
    ls_parser.add_argument("--spoonflower", type=str, default="./output/spoonflower")
    ls_parser.add_argument("--colorways", type=str, default="./output/colorways")
    ls_parser.add_argument("--uploads", type=str, default="./output/uploads/base")
    ls_parser.add_argument("--uploads-colorways", dest="uploads_colorways", type=str, default="./output/uploads/colorways")
    ls_parser.add_argument("--redbubble", type=str, default="./output/redbubble")
    ls_parser.add_argument("--redbubble-reports", dest="redbubble_reports", type=str, default="./reports/redbubble")
    ls_parser.add_argument("--output", type=str, default="./reports/listings")

    # ── Sous-commande : text-apply ────────────────────────────────────────────
    ta_parser = subparsers.add_parser(
        "text-apply",
        help="Applique la typographie CDC (via Python/PIL) sur les images Redbubble générées.",
    )
    ta_parser.add_argument(
        "--images", type=str, default="./output/redbubble",
        help="Dossier des PNG Redbubble générés.",
    )
    ta_parser.add_argument(
        "--reports", type=str, default="./reports/redbubble",
        help="Dossier contenant les CDC JSON Redbubble.",
    )
    ta_parser.add_argument(
        "--output", type=str, default=None,
        help="Dossier de sortie (vide = écrase les originaux).",
    )
    ta_parser.add_argument(
        "--overwrite", action="store_true",
        help="Re-applique même si le fichier de sortie existe déjà.",
    )

    # ── Sous-commande : assemble ──────────────────────────────────────────────
    asm_parser = subparsers.add_parser(
        "assemble",
        help="Assemble des illustrations individuelles en seamless tile Spoonflower (Pillow, 0 coût).",
    )
    asm_parser.add_argument(
        "--input", type=str, default="./output/redbubble",
        help="Dossier des PNGs sources (illustrations individuelles).",
    )
    asm_parser.add_argument(
        "--output", type=str, default="./output/spoonflower",
        help="Dossier de sortie des tiles seamless.",
    )
    asm_parser.add_argument(
        "--background", type=str, default="navy",
        help="Fond : navy, charcoal, forest, ivory, cream, white, slate, ou #HEX.",
    )
    asm_parser.add_argument(
        "--n-specimens", dest="n_specimens", type=int, default=9,
        help="Nombre d'illustrations à placer par tile.",
    )
    asm_parser.add_argument(
        "--scale-min", dest="scale_min", type=float, default=0.14,
        help="Taille minimale des specimens (fraction du tile).",
    )
    asm_parser.add_argument(
        "--scale-max", dest="scale_max", type=float, default=0.30,
        help="Taille maximale des specimens (fraction du tile).",
    )
    asm_parser.add_argument(
        "--rotation", type=float, default=18.0,
        help="Rotation max en degrés (±).",
    )
    asm_parser.add_argument(
        "--tile-size", dest="tile_size", type=int, default=4500,
        help="Taille du tile en pixels (défaut: 4500).",
    )
    asm_parser.add_argument(
        "--seed", type=int, default=42,
        help="Graine aléatoire pour la composition.",
    )
    asm_parser.add_argument(
        "--variants", type=int, default=3,
        help="Nombre de compositions différentes à générer.",
    )
    asm_parser.add_argument(
        "--yes", action="store_true",
        help="Auto-confirmer (mode CI).",
    )

    # ── Sous-commande : text-fix ──────────────────────────────────────────────
    tf_parser = subparsers.add_parser(
        "text-fix",
        help="Efface le texte FLUX déformé + applique la typographie CDC propre (Gemini Vision + PIL).",
    )
    tf_parser.add_argument(
        "--images", type=str, default="./output/redbubble",
        help="Dossier des PNG Redbubble à corriger.",
    )
    tf_parser.add_argument(
        "--reports", type=str, default="./reports/redbubble",
        help="Dossier contenant les CDC JSON Redbubble.",
    )
    tf_parser.add_argument(
        "--output", type=str, default=None,
        help="Dossier de sortie (vide = écrase les originaux).",
    )
    tf_parser.add_argument(
        "--overwrite", action="store_true",
        help="Re-traite même si le fichier de sortie existe déjà.",
    )
    tf_parser.add_argument(
        "--erase-only", dest="erase_only", action="store_true",
        help="Efface seulement le texte FLUX sans appliquer la typo CDC.",
    )

    # ── Sous-commande : thumbnails ────────────────────────────────────────────
    th_parser = subparsers.add_parser(
        "thumbnails",
        help="Génère des vignettes JPEG (600×600) navigables depuis GitHub.",
    )
    th_parser.add_argument(
        "--pipeline", type=str, default="./output/spoonflower",
        help="Dossier des images pipeline.",
    )
    th_parser.add_argument(
        "--colorways", type=str, default="./output/colorways",
        help="Dossier des colorways.",
    )
    th_parser.add_argument(
        "--uploads", type=str, default="./output/uploads/base",
        help="Dossier des uploads utilisateur.",
    )
    th_parser.add_argument(
        "--output", type=str, default="./output/thumbnails",
        help="Dossier de sortie des vignettes.",
    )
    th_parser.add_argument(
        "--no-contact", action="store_true",
        help="Ne pas générer les planches-contact.",
    )

    # ── Sous-commande : generate-elements ─────────────────────────────────────
    gen_elem_parser = subparsers.add_parser(
        "generate-elements",
        help="Génère 10 éléments isolés via Runware + assemble en pattern seamless (Pillow).",
    )
    gen_elem_parser.add_argument(
        "--niche", type=str, default="",
        help="Nom du CdC à générer (partiel OK). Défaut : meilleur score.",
    )
    gen_elem_parser.add_argument(
        "--yes", action="store_true",
        help="Auto-confirmer (mode CI, pas de prompt interactif).",
    )
    gen_elem_parser.add_argument(
        "--report", type=str, default="",
        help="Chemin vers le rapport JSON. Défaut : dernier rapport.",
    )
    gen_elem_parser.add_argument(
        "--output", type=str, default="./output/spoonflower",
        help="Répertoire de sortie pour le PNG Spoonflower.",
    )

    # ── Arguments legacy (compatibilité ascendante) ────────────────────────────
    parser.add_argument("--keywords", type=str, default="")
    parser.add_argument("--categories", type=str, default="")
    parser.add_argument("--fast", action="store_true")
    parser.add_argument("--depth", type=int, default=2)
    parser.add_argument("--db", type=str, default="./data/opportunities.db")
    parser.add_argument(
        "--preview-trends", action="store_true",
        help="[legacy] Mode vérification sans génération d'images.",
    )
    parser.add_argument("--market", type=str, default="spoonflower")
    parser.add_argument("--niches", type=int, default=None)
    parser.add_argument("--exclude", type=str, default="")
    parser.add_argument("--focus", type=str, default="")

    args = parser.parse_args()

    # ── Dispatch sur les sous-commandes ───────────────────────────────────────
    if args.command == "preview":
        constraints = []
        exclude = [e.strip() for e in args.exclude.split(",") if e.strip()]
        focus = [f.strip() for f in args.focus.split(",") if f.strip()]
        if exclude:
            constraints.append("Avoid these: " + ", ".join(exclude))
        if focus:
            constraints.append("Prioritize these angles: " + ", ".join(focus))

        from trend_discovery.generators.production_brief import BriefGenerator
        from trend_discovery.generators.approval_gate import ApprovalGate
        from trend_discovery.markets.market_profile import get_profile

        profile = get_profile(args.market)
        if args.niches:
            profile.niche_count = int(args.niches)

        gen = BriefGenerator(profile)
        briefs = gen.generate_all("\n".join(constraints))
        path = gen.save_report(briefs, args.output)
        logger.info("Rapport sauvegardé: %s", path)

        # Écrire le manifest d'approbation + persister les briefs complets
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        gate = ApprovalGate()
        manifest_path = gate.write_pending_manifest(briefs, run_id)
        gate.save_brief_data(briefs, run_id)
        print(f"\nManifest d'approbation : {manifest_path}")
        print("Éditez 'approved': true pour les niches choisies, puis lancez 'generate'.")
        return

    if args.command == "archive":
        niche_list = [n.strip() for n in args.niche.split(",") if n.strip()]
        archive_cdcs(
            niche_names=niche_list,
            report_path=args.report or None,
            replace=not args.no_replace,
            market=args.market,
        )
        return

    if args.command == "audit":
        run_audit(
            image_dir=args.images,
            report_path=args.report or None,
            output_dir=args.output,
        )
        return

    if args.command == "generate-all":
        niche_list = [n.strip() for n in args.niche.split(",") if n.strip()] if args.niche else None
        generate_all_base(
            report_path=args.report or None,
            yes=args.yes,
            output_dir=args.output,
            limit=args.limit or None,
            niche_names=niche_list,
        )
        return

    if args.command == "colorize":
        pal_list = [p.strip() for p in args.palettes.split(",") if p.strip()] or None
        colorize_images(
            input_dir=args.input,
            output_dir=args.output,
            palettes=pal_list,
            glob_pattern=args.pattern,
            yes=args.yes,
            smart=getattr(args, "smart", False),
            reports_dir=getattr(args, "reports", "./reports") or "./reports",
        )
        return

    if args.command == "bg-remove":
        remove_backgrounds(
            input_dir=args.input,
            output_dir=args.output,
            tolerance=args.tolerance,
            yes=args.yes,
        )
        return

    if args.command == "seamless-audit":
        seamless_audit(
            input_dir=args.input,
            output_dir=args.output or None,
            fix=not args.no_fix,
            overwrite=args.overwrite,
            threshold=args.threshold,
            yes=args.yes,
        )
        return

    if args.command == "thumbnails":
        generate_thumbnails(
            pipeline_dir=args.pipeline,
            colorways_dir=args.colorways,
            uploads_dir=args.uploads,
            uploads_colorways_dir=os.path.join(os.path.dirname(args.uploads.rstrip("/")), "colorways"),
            output_root=args.output,
            contact_sheets=not args.no_contact,
        )
        return

    if args.command == "listings":
        generate_listings(
            reports_dir=getattr(args, "reports", "./reports") or "./reports",
            output_dir=getattr(args, "output", "./reports/listings") or "./reports/listings",
        )
        return

    if args.command == "text-apply":
        apply_text(
            images_dir=getattr(args, "images", "./output/redbubble"),
            reports_dir=getattr(args, "reports", "./reports/redbubble"),
            output_dir=getattr(args, "output", None),
            overwrite=getattr(args, "overwrite", False),
        )
        return

    if args.command == "assemble":
        assemble_specimens(
            input_dir=args.input,
            output_dir=args.output,
            background=args.background,
            n_specimens=args.n_specimens,
            scale_min=args.scale_min,
            scale_max=args.scale_max,
            rotation_range=args.rotation,
            tile_size=args.tile_size,
            seed=args.seed,
            variants=args.variants,
            yes=args.yes,
        )
        return

    if args.command == "text-fix":
        fix_text(
            images_dir=getattr(args, "images", "./output/redbubble"),
            reports_dir=getattr(args, "reports", "./reports/redbubble"),
            output_dir=getattr(args, "output", None),
            overwrite=getattr(args, "overwrite", False),
            erase_only=getattr(args, "erase_only", False),
        )
        return

    if args.command == "generate-elements":
        generate_elements(
            report_path=args.report or None,
            niche_name=args.niche or None,
            yes=args.yes,
            output_dir=args.output,
        )
        return

    if args.command == "generate":
        if args.best:
            generate_best_variants(
                report_path=args.report or None,
                n_fusions=args.fusions,
                yes=args.yes,
                output_dir=args.output,
                niche_name=args.niche or None,
                max_variants=args.limit or None,
            )
        else:
            generate_approved(
                manifest_path=args.manifest or None,
                approve=args.approve or None,
                images=args.images,
                yes=args.yes,
                output_dir=args.output,
                market=args.market,
            )
        return

    # ── Legacy : --preview-trends ─────────────────────────────────────────────
    if args.preview_trends:
        constraints = []
        exclude = [e.strip() for e in args.exclude.split(",") if e.strip()]
        focus = [f.strip() for f in args.focus.split(",") if f.strip()]
        if exclude:
            constraints.append("Avoid these: " + ", ".join(exclude))
        if focus:
            constraints.append("Prioritize these angles: " + ", ".join(focus))
        preview_trends(
            market=args.market,
            niche_count=args.niches,
            extra_constraints="\n".join(constraints),
            output_dir=getattr(args, "output", "./reports") or "./reports",
        )
        return

    # ── Legacy : pipeline complet ─────────────────────────────────────────────
    extra_kws = [k.strip() for k in args.keywords.split(",") if k.strip()] if args.keywords else None
    cats = [c.strip() for c in args.categories.split(",") if c.strip()] if args.categories else None

    run_pipeline(
        extra_keywords=extra_kws,
        focus_categories=cats,
        fast_mode=args.fast,
        tree_depth=args.depth,
        db_path=args.db,
    )


if __name__ == "__main__":
    main()
