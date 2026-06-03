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
    )
    logger.info("[Phase 5] %d opportunités scorées", len(opportunity_scores))

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
# CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Moneymaker — Moteur de Détection de Tendances et d'Opportunités"
    )
    parser.add_argument(
        "--keywords", type=str, default="",
        help="Mots-clés supplémentaires (séparés par des virgules)"
    )
    parser.add_argument(
        "--categories", type=str, default="",
        help="Catégories de niches à analyser (séparées par des virgules)"
    )
    parser.add_argument(
        "--fast", action="store_true",
        help="Mode rapide : utilise uniquement Google Trends, Autocomplete et Reddit"
    )
    parser.add_argument(
        "--depth", type=int, default=2,
        help="Profondeur dans l'arbre de niches (1=catégories, 2=niches, 3=sous-niches)"
    )
    parser.add_argument(
        "--db", type=str, default="./data/opportunities.db",
        help="Chemin vers la base de données SQLite"
    )
    args = parser.parse_args()

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
