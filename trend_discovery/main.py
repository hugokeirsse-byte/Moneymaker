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
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

# Constante partagée pour approval_gate (évite l'import circulaire au toplevel)
try:
    from trend_discovery.generators.approval_gate import DEFAULT_IMAGES_PER_BRIEF
except Exception:
    DEFAULT_IMAGES_PER_BRIEF = 5


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

    if args.command == "generate":
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
