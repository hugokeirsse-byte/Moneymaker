"""
Scraper Registry — central orchestrator for all data sources.

This is the extensible hub of the collection pipeline.
Adding a new scraper = adding one entry to REGISTRY.
The pipeline calls collect_all() to gather signals from every active source.

Design principle: every scraper is optional and fails gracefully.
The pipeline always produces output even if all scrapers fail.
"""
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ScraperEntry:
    name: str                          # unique identifier
    description: str                   # human-readable description
    scraper_class: Any                 # the class to instantiate
    enabled: bool = True               # can be disabled per run
    requires_api_key: bool = False     # if True, only run when key is present
    api_key_env: str = ""              # env var name for the required key
    weight: float = 1.0               # how much this source is trusted (0-2)
    collect_fn: str = ""              # method name to call on the instance


# ─────────────────────────────────────────────────────────────────────────────
# Registry of all available scrapers
# ─────────────────────────────────────────────────────────────────────────────
def _build_registry() -> List[ScraperEntry]:
    entries = []

    try:
        from trend_discovery.scrapers.google_trends_scraper import GoogleTrendsScraper
        entries.append(ScraperEntry(
            name="google_trends",
            description="Google Trends — interest over time and related queries",
            scraper_class=GoogleTrendsScraper,
            weight=1.8,
            collect_fn="get_trending_searches",
        ))
    except ImportError:
        pass

    try:
        from trend_discovery.scrapers.google_autocomplete_scraper import GoogleAutocompleteScraper
        entries.append(ScraperEntry(
            name="google_autocomplete",
            description="Google Autocomplete — search volume proxy",
            scraper_class=GoogleAutocompleteScraper,
            weight=1.2,
            collect_fn="get_trending_pod_keywords",
        ))
    except ImportError:
        pass

    try:
        from trend_discovery.scrapers.reddit_scraper import RedditScraper
        entries.append(ScraperEntry(
            name="reddit",
            description="Reddit public JSON — community buzz",
            scraper_class=RedditScraper,
            weight=1.3,
            collect_fn="get_trending_keywords_from_reddit",
        ))
    except ImportError:
        pass

    try:
        from trend_discovery.scrapers.spoonflower_scraper import SpoonflowerScraper
        entries.append(ScraperEntry(
            name="spoonflower",
            description="Spoonflower — trending/bestselling design tags",
            scraper_class=SpoonflowerScraper,
            weight=1.8,
            collect_fn="get_top_tags",
        ))
    except ImportError:
        pass

    try:
        from trend_discovery.scrapers.redbubble_scraper import RedbubbleScraper
        entries.append(ScraperEntry(
            name="redbubble",
            description="RedBubble — competition and trending searches",
            scraper_class=RedbubbleScraper,
            weight=1.6,
            collect_fn="get_popular_tags",
        ))
    except ImportError:
        pass

    try:
        from trend_discovery.scrapers.etsy_scraper import EtsyScraper
        entries.append(ScraperEntry(
            name="etsy",
            description="Etsy — trending POD searches and tags",
            scraper_class=EtsyScraper,
            weight=1.5,
            collect_fn="get_trending_searches",
        ))
    except ImportError:
        pass

    try:
        from trend_discovery.scrapers.pinterest_scraper import PinterestScraper
        entries.append(ScraperEntry(
            name="pinterest",
            description="Pinterest — visual trend autocomplete",
            scraper_class=PinterestScraper,
            weight=1.6,
            collect_fn="get_trending_topics",
        ))
    except ImportError:
        pass

    try:
        from trend_discovery.scrapers.tiktok_scraper import TikTokScraper
        entries.append(ScraperEntry(
            name="tiktok",
            description="TikTok Creative Center — aesthetic hashtag trends",
            scraper_class=TikTokScraper,
            weight=1.4,
            collect_fn="get_aesthetic_hashtags",
        ))
    except ImportError:
        pass

    try:
        from trend_discovery.scrapers.amazon_merch_scraper import AmazonMerchScraper
        entries.append(ScraperEntry(
            name="amazon",
            description="Amazon — autocomplete demand signals",
            scraper_class=AmazonMerchScraper,
            weight=1.5,
            collect_fn="get_merch_bestsellers",
        ))
    except ImportError:
        pass

    try:
        from trend_discovery.scrapers.society6_scraper import Society6Scraper
        entries.append(ScraperEntry(
            name="society6",
            description="Society6 — trending design tags",
            scraper_class=Society6Scraper,
            weight=1.3,
            collect_fn="get_trending_tags",
        ))
    except ImportError:
        pass

    try:
        from trend_discovery.scrapers.deviantart_scraper import DeviantArtScraper
        entries.append(ScraperEntry(
            name="deviantart",
            description="DeviantArt — leading indicator for visual aesthetics",
            scraper_class=DeviantArtScraper,
            weight=1.1,
            collect_fn="get_trending_tags",
        ))
    except ImportError:
        pass

    try:
        from trend_discovery.scrapers.creative_market_scraper import CreativeMarketScraper
        entries.append(ScraperEntry(
            name="creative_market",
            description="Creative Market — B2B demand for design assets",
            scraper_class=CreativeMarketScraper,
            weight=1.4,
            collect_fn="get_popular_tags",
        ))
    except ImportError:
        pass

    try:
        from trend_discovery.scrapers.bing_trends_scraper import BingTrendsScraper
        entries.append(ScraperEntry(
            name="bing",
            description="Bing Autosuggest — triangulation search signal",
            scraper_class=BingTrendsScraper,
            weight=1.0,
            collect_fn="get_pod_suggestions",
        ))
    except ImportError:
        pass

    try:
        from trend_discovery.scrapers.youtube_trends_scraper import YouTubeTrendsScraper
        entries.append(ScraperEntry(
            name="youtube",
            description="YouTube — tutorial demand = niche interest",
            scraper_class=YouTubeTrendsScraper,
            requires_api_key=False,  # works via autocomplete without key
            api_key_env="YOUTUBE_API_KEY",
            weight=1.2,
            collect_fn="get_autocomplete_suggestions",
        ))
    except ImportError:
        pass

    return entries


REGISTRY: List[ScraperEntry] = _build_registry()


class ScraperOrchestrator:
    """
    Runs all registered scrapers and aggregates raw signals.
    Each scraper is isolated — failure of one never stops the pipeline.
    """

    def __init__(self, enabled_only: bool = True):
        self._entries = [e for e in REGISTRY if (not enabled_only or e.enabled)]
        logger.info(
            "ScraperOrchestrator initialized with %d scrapers: %s",
            len(self._entries),
            [e.name for e in self._entries],
        )

    def list_scrapers(self) -> List[Dict]:
        """Return metadata about all registered scrapers."""
        return [
            {
                "name": e.name,
                "description": e.description,
                "enabled": e.enabled,
                "requires_api_key": e.requires_api_key,
                "weight": e.weight,
            }
            for e in REGISTRY
        ]

    def collect_raw_signals(self) -> Dict[str, Any]:
        """
        Run all enabled scrapers and collect raw signals.

        Returns:
            {
                "scraper_name": raw_output,
                ...
            }
        """
        raw_signals: Dict[str, Any] = {}
        successful = []
        failed = []

        for entry in self._entries:
            logger.info("Running scraper: %s", entry.name)
            try:
                instance = entry.scraper_class()
                if entry.collect_fn:
                    method = getattr(instance, entry.collect_fn, None)
                    if method:
                        result = method()
                        if result:
                            raw_signals[entry.name] = result
                            successful.append(entry.name)
                            logger.info(
                                "✓ %s: collected %d items",
                                entry.name,
                                len(result) if hasattr(result, "__len__") else 1,
                            )
                    else:
                        logger.warning("Method %s not found on %s", entry.collect_fn, entry.name)
            except Exception as exc:
                logger.warning("✗ %s failed (non-fatal): %s", entry.name, exc)
                failed.append(entry.name)

        logger.info(
            "Collection complete: %d/%d scrapers succeeded (%s failed)",
            len(successful),
            len(self._entries),
            failed or "none",
        )
        return raw_signals

    def add_scraper(self, entry: ScraperEntry) -> None:
        """Add a new scraper to the registry at runtime."""
        REGISTRY.append(entry)
        self._entries.append(entry)
        logger.info("Added new scraper: %s", entry.name)
