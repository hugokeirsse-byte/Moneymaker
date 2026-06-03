"""
Provider Wikipedia — intérêt public réel, 100 % GRATUIT, sans clé.

C'est la source de demande la plus précieuse en budget zéro :
    - Pageviews API : nombre RÉEL de vues d'une page par mois (intérêt mesuré)
    - dérive la croissance (pente sur 12 mois) et la saisonnalité (variation)
    - MediaWiki API : découverte de sous-niches réelles (liens, catégories)

Aucune authentification. Wikimedia exige seulement un User-Agent descriptif.
Ne bloque pas les IP de datacenter (contrairement à Google/Reddit anonymes).

Docs :
    https://wikimedia.org/api/rest_v1/  (pageviews)
    https://www.mediawiki.org/wiki/API:Main_page

Limite honnête : les vues Wikipédia mesurent l'intérêt encyclopédique, pas
l'intention d'achat. C'est un excellent proxy de DEMANDE et de TENDANCE, à
croiser avec la compétition marché réelle (Etsy) pour juger la rentabilité.
"""
from __future__ import annotations

import logging
import math
import os
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

import requests

from trend_discovery.providers.base_provider import DataProvider
from trend_discovery.provenance import Metric

logger = logging.getLogger(__name__)

WIKI_REST = "https://wikimedia.org/api/rest_v1/metrics/pageviews"
WIKI_API = "https://en.wikipedia.org/w/api.php"
# Wikimedia impose un User-Agent identifiable (sinon 403).
WIKI_UA = "Moneymaker/1.0 (POD trend research; contact via repo)"


class WikipediaProvider(DataProvider):
    key = "wikipedia"
    name = "Wikipedia Pageviews + MediaWiki (gratuit, sans clé)"
    required_env = []  # aucune clé requise
    produces_measured_data = True

    def __init__(self, lang: str = "en", cache_path: str = "./data/cache_wikipedia.json"):
        super().__init__()
        self._lang = lang
        self._session = requests.Session()
        self._session.headers.update({"User-Agent": WIKI_UA, "Accept": "application/json"})
        self._title_cache: Dict[str, Optional[str]] = {}

    def _check_credentials(self) -> bool:
        # Toujours disponible : pas de clé nécessaire.
        return True

    # ── Résolution du titre de page ──────────────────────────────────────────
    def resolve_title(self, query: str) -> Optional[str]:
        """
        Trouve le titre de page Wikipédia le plus pertinent pour une niche.
        Ex : "cottagecore" → "Cottagecore", "botanique" → "Botanical illustration".
        """
        if query in self._title_cache:
            return self._title_cache[query]
        try:
            resp = self._session.get(WIKI_API, params={
                "action": "query", "list": "search", "srsearch": query,
                "srlimit": 1, "format": "json",
            }, timeout=15)
            resp.raise_for_status()
            hits = resp.json().get("query", {}).get("search", [])
            title = hits[0]["title"] if hits else None
            self._title_cache[query] = title
            return title
        except Exception as exc:
            logger.warning("[wikipedia] résolution titre '%s' échouée: %s", query, exc)
            self._title_cache[query] = None
            return None

    # ── Pageviews ──────────────────────────────────────────────────────────────
    def get_monthly_pageviews(self, title: str, months: int = 12) -> List[int]:
        """
        Retourne les vues mensuelles réelles d'une page sur les N derniers mois.
        """
        end = datetime.now(timezone.utc).replace(day=1)
        start = end - timedelta(days=months * 31)
        article = title.replace(" ", "_")
        url = (
            f"{WIKI_REST}/per-article/{self._lang}.wikipedia/all-access/all-agents/"
            f"{requests.utils.quote(article, safe='')}/monthly/"
            f"{start.strftime('%Y%m%d')}00/{end.strftime('%Y%m%d')}00"
        )
        try:
            resp = self._session.get(url, timeout=20)
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            items = resp.json().get("items", [])
            return [it.get("views", 0) for it in items]
        except Exception as exc:
            logger.warning("[wikipedia] pageviews '%s' échoué: %s", title, exc)
            return []

    # ── Métriques tracées ─────────────────────────────────────────────────────
    def demande_metric(self, niche: str) -> Metric:
        """Demande réelle (0-100) basée sur les vues mensuelles moyennes."""
        title = self.resolve_title(niche)
        if not title:
            return Metric.unavailable(detail=f"Pas de page Wikipédia pour '{niche}'")
        views = self.get_monthly_pageviews(title)
        if not views:
            return Metric.unavailable(detail=f"Pas de pageviews pour '{title}'")
        avg = sum(views) / len(views)
        if avg <= 0:
            return Metric.measured(0.0, source="wikipedia", confidence=70.0,
                                   detail=f"page '{title}' : 0 vue")
        # Échelle log : 1k vues/mois→~45, 10k→~62, 100k→~80, 1M→~97
        score = min(100.0, (math.log10(avg + 1) / 6.2) * 100)
        return Metric.measured(
            round(score, 1), source="wikipedia", confidence=82.0,
            detail=f"page '{title}' : {int(avg):,} vues/mois (réel)".replace(",", " "),
        )

    def croissance_metric(self, niche: str) -> Metric:
        """Croissance réelle (0-100) : pente des vues sur 12 mois."""
        title = self.resolve_title(niche)
        if not title:
            return Metric.unavailable(detail=f"Pas de page pour '{niche}'")
        views = self.get_monthly_pageviews(title)
        if len(views) < 4:
            return Metric.unavailable(detail="historique insuffisant")
        recent = sum(views[-3:]) / 3
        old = sum(views[:3]) / 3
        if old <= 0:
            return Metric.measured(60.0, source="wikipedia", confidence=65.0,
                                   detail="page récente (réel)")
        growth = (recent - old) / old * 100
        score = max(0.0, min(100.0, 50 + growth / 2))
        return Metric.measured(
            round(score, 1), source="wikipedia", confidence=78.0,
            detail=f"évolution {growth:+.0f}% des vues sur 12 mois (réel)",
        )

    def seasonality_metric(self, niche: str) -> Metric:
        """Saisonnalité (0-100) : coefficient de variation des vues mensuelles."""
        title = self.resolve_title(niche)
        if not title:
            return Metric.unavailable()
        views = self.get_monthly_pageviews(title)
        if len(views) < 6:
            return Metric.unavailable(detail="historique insuffisant")
        avg = sum(views) / len(views)
        if avg <= 0:
            return Metric.unavailable()
        std = math.sqrt(sum((v - avg) ** 2 for v in views) / len(views))
        cov = min(100.0, (std / avg) * 100)
        return Metric.measured(
            round(cov, 1), source="wikipedia", confidence=75.0,
            detail=f"variation mensuelle {cov:.0f}% (réel)",
        )

    # ── Découverte de sous-niches ───────────────────────────────────────────────
    def get_subniches(self, niche: str, limit: int = 25) -> List[str]:
        """
        Découvre des sous-niches réelles via les liens sortants d'une page
        Wikipédia (les concepts les plus liés au sujet).
        """
        title = self.resolve_title(niche)
        if not title:
            return []
        try:
            resp = self._session.get(WIKI_API, params={
                "action": "query", "titles": title, "prop": "links",
                "pllimit": limit, "plnamespace": 0, "format": "json",
            }, timeout=15)
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})
            links = []
            for page in pages.values():
                for link in page.get("links", []):
                    links.append(link.get("title", ""))
            return [l for l in links if l]
        except Exception as exc:
            logger.warning("[wikipedia] sous-niches '%s' échoué: %s", niche, exc)
            return []

    def get_related_categories(self, niche: str, limit: int = 20) -> List[str]:
        """Catégories Wikipédia d'une page = familles de niches réelles."""
        title = self.resolve_title(niche)
        if not title:
            return []
        try:
            resp = self._session.get(WIKI_API, params={
                "action": "query", "titles": title, "prop": "categories",
                "cllimit": limit, "format": "json",
            }, timeout=15)
            resp.raise_for_status()
            pages = resp.json().get("query", {}).get("pages", {})
            cats = []
            for page in pages.values():
                for cat in page.get("categories", []):
                    name = cat.get("title", "").replace("Category:", "")
                    if name and not name.startswith(("Articles", "CS1", "Wikipedia", "All ")):
                        cats.append(name)
            return cats
        except Exception as exc:
            logger.warning("[wikipedia] catégories '%s' échoué: %s", niche, exc)
            return []
