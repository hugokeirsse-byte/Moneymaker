"""
Spoonflower scraper — respectful scraping with delays, retry logic, and
realistic headers. No API key required.
"""
import logging
import random
import time
from typing import Dict, List, Optional
from collections import Counter
from urllib.parse import urlencode, quote_plus

import requests
from bs4 import BeautifulSoup

from trend_discovery.config import DEFAULT_HEADERS, PLATFORMS, SCRAPER_DELAYS

logger = logging.getLogger(__name__)

SPOONFLOWER_BASE = PLATFORMS["spoonflower"]


class SpoonflowerScraper:
    """
    Scrapes Spoonflower for trending, best-selling, and new designs.
    All public pages — no credentials needed.
    """

    def __init__(self):
        self._delays = SCRAPER_DELAYS["spoonflower"]
        self._session = requests.Session()
        self._session.headers.update(DEFAULT_HEADERS)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _sleep(self):
        """Polite delay between requests."""
        delay = random.uniform(self._delays["min"], self._delays["max"])
        time.sleep(delay)

    def _get(self, url: str, params: Optional[Dict] = None, retries: int = 3) -> Optional[BeautifulSoup]:
        """
        GET a URL with retry / exponential backoff on 429/503.

        Returns a BeautifulSoup object or None on failure.
        """
        for attempt in range(retries):
            try:
                self._sleep()
                response = self._session.get(url, params=params, timeout=20)
                if response.status_code in (429, 503):
                    wait = (2 ** attempt) * random.uniform(5, 10)
                    logger.warning(
                        "Spoonflower rate-limited (%s). Waiting %.1fs before retry %d/%d.",
                        response.status_code, wait, attempt + 1, retries,
                    )
                    time.sleep(wait)
                    continue
                response.raise_for_status()
                return BeautifulSoup(response.text, "lxml")
            except requests.exceptions.RequestException as exc:
                logger.error("Spoonflower request error (attempt %d/%d): %s", attempt + 1, retries, exc)
                if attempt < retries - 1:
                    time.sleep(random.uniform(3, 6))
        return None

    def _parse_designs(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Parse design cards from a Spoonflower listing page.
        Returns a list of dicts with 'title' and 'tags'.
        """
        designs = []
        if soup is None:
            return designs

        # Spoonflower renders design cards with various class conventions;
        # we target both the legacy and current markup patterns.
        card_selectors = [
            "li[class*='DesignCard']",
            "li[class*='design-card']",
            "div[class*='DesignCard']",
            "div[class*='design-card']",
        ]
        cards = []
        for selector in card_selectors:
            cards = soup.select(selector)
            if cards:
                break

        # Fallback: grab any <img alt="..."> inside a product list
        if not cards:
            imgs = soup.select("ul img[alt]")
            for img in imgs:
                title = img.get("alt", "").strip()
                if title:
                    designs.append({"title": title, "tags": []})
            return designs

        for card in cards:
            title = ""
            tags: List[str] = []

            # Title from alt text or dedicated title element
            title_el = card.select_one("[class*='title'], [class*='Title']")
            if title_el:
                title = title_el.get_text(strip=True)
            else:
                img = card.select_one("img[alt]")
                if img:
                    title = img.get("alt", "").strip()

            # Tags from data attributes or anchor text in tag lists
            for tag_el in card.select("a[class*='tag'], [class*='Tag'] a, [data-tag]"):
                tag_text = tag_el.get_text(strip=True) or tag_el.get("data-tag", "")
                if tag_text:
                    tags.append(tag_text.lower().strip())

            if title or tags:
                designs.append({"title": title, "tags": tags})

        return designs

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_trending_designs(self) -> List[Dict]:
        """
        Scrape trending designs from Spoonflower.

        Returns:
            List of dicts with 'title' and 'tags'.
        """
        url = f"{SPOONFLOWER_BASE}/designs"
        soup = self._get(url, params={"sort": "trending"})
        designs = self._parse_designs(soup)
        logger.info("Spoonflower trending: fetched %d designs.", len(designs))
        return designs

    def get_bestseller_designs(self) -> List[Dict]:
        """
        Scrape best-selling designs from Spoonflower.

        Returns:
            List of dicts with 'title' and 'tags'.
        """
        url = f"{SPOONFLOWER_BASE}/designs"
        soup = self._get(url, params={"sort": "bestSelling"})
        designs = self._parse_designs(soup)
        logger.info("Spoonflower bestsellers: fetched %d designs.", len(designs))
        return designs

    def get_new_designs(self) -> List[Dict]:
        """
        Scrape the newest designs from Spoonflower.

        Returns:
            List of dicts with 'title' and 'tags'.
        """
        url = f"{SPOONFLOWER_BASE}/designs"
        soup = self._get(url, params={"sort": "date"})
        designs = self._parse_designs(soup)
        logger.info("Spoonflower new designs: fetched %d designs.", len(designs))
        return designs

    def search_designs(self, keyword: str) -> List[Dict]:
        """
        Search Spoonflower designs by keyword.

        Args:
            keyword: Search term.

        Returns:
            List of dicts with 'title' and 'tags'.
        """
        url = f"{SPOONFLOWER_BASE}/designs"
        soup = self._get(url, params={"q": keyword})
        designs = self._parse_designs(soup)
        logger.info("Spoonflower search '%s': fetched %d designs.", keyword, len(designs))
        return designs

    def extract_tags_from_designs(self, designs_list: List[Dict]) -> Counter:
        """
        Count all tags across a list of design dicts.

        Args:
            designs_list: Output of any scrape method.

        Returns:
            Counter mapping tag -> count.
        """
        tag_counter: Counter = Counter()
        for design in designs_list:
            for tag in design.get("tags", []):
                if tag:
                    tag_counter[tag] += 1
        return tag_counter

    def _parse_designs_with_images(self, soup: BeautifulSoup) -> List[Dict]:
        """
        Parse design cards en extrayant titre + URL d'image preview.
        Essaie __NEXT_DATA__ en premier (Next.js SSR), puis fallback HTML.
        """
        if soup is None:
            return []

        # Essai 1 : __NEXT_DATA__ (Next.js embed JSON)
        next_script = soup.find("script", {"id": "__NEXT_DATA__"})
        if next_script and next_script.string:
            try:
                data = __import__("json").loads(next_script.string)
                designs = self._dig_next_designs(data)
                if designs:
                    return designs
            except Exception:
                pass

        # Essai 2 : balises <img> dans les cards de design
        results = []
        card_selectors = [
            "li[class*='DesignCard']", "li[class*='design-card']",
            "div[class*='DesignCard']", "div[class*='design-card']",
        ]
        cards = []
        for selector in card_selectors:
            cards = soup.select(selector)
            if cards:
                break

        for card in cards:
            img = card.select_one("img")
            if not img:
                continue
            src = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""
            alt = img.get("alt", "").strip()
            if src and ("spoonflower" in src or "cloudfront" in src or "fabric" in src):
                results.append({
                    "title": alt or "Spoonflower bestseller",
                    "image_url": src,
                    "design_url": "",
                    "source": "spoonflower",
                })

        # Essai 3 : toutes les <img> CDN cloudfront dans la page
        if not results:
            import re
            all_imgs = soup.find_all("img")
            for img in all_imgs:
                src = img.get("src") or img.get("data-src") or ""
                if "cloudfront" in src and ("fabric" in src or "design" in src):
                    results.append({
                        "title": img.get("alt", "Spoonflower design").strip(),
                        "image_url": src,
                        "design_url": "",
                        "source": "spoonflower",
                    })

        return results

    def _dig_next_designs(self, data, depth: int = 0) -> List[Dict]:
        """Cherche récursivement des designs avec images dans le JSON Next.js."""
        if depth > 8:
            return []
        if isinstance(data, list):
            candidates = [
                x for x in data if isinstance(x, dict)
                and (x.get("previewUrl") or x.get("imageUrl") or x.get("thumbnailUrl"))
            ]
            if len(candidates) >= 2:
                out = []
                for d in candidates:
                    url = d.get("previewUrl") or d.get("imageUrl") or d.get("thumbnailUrl", "")
                    if url:
                        out.append({
                            "title": d.get("name") or d.get("title") or str(d.get("id", "")),
                            "image_url": url,
                            "design_url": d.get("url") or "",
                            "source": "spoonflower",
                        })
                return out
            for item in data[:5]:
                r = self._dig_next_designs(item, depth + 1)
                if r:
                    return r
        if isinstance(data, dict):
            for key in ("designs", "results", "items", "data", "pageProps",
                        "initialData", "searchResults", "props"):
                if key in data:
                    r = self._dig_next_designs(data[key], depth + 1)
                    if r:
                        return r
            for val in data.values():
                if isinstance(val, (dict, list)):
                    r = self._dig_next_designs(val, depth + 1)
                    if r:
                        return r
        return []

    def search_bestsellers_with_images(self, query: str, limit: int = 3) -> List[Dict]:
        """
        Cherche les designs bestsellers pour une niche et retourne leurs images.

        Utilisé pendant le preview pour enrichir les CdCs avec des références
        visuelles réelles (seedImage pour Runware, strength 0.20-0.25).

        Args:
            query: terme de niche (ex: "nordic folk art flat pattern")
            limit: nombre d'images souhaitées

        Returns:
            List de dicts {title, image_url, design_url, source}
            Retourne [] si scraping impossible (pas de crash).
        """
        try:
            soup = self._get(
                f"{SPOONFLOWER_BASE}/designs",
                params={"q": query, "sort": "bestSelling"},
            )
            if soup is None:
                return []
            results = self._parse_designs_with_images(soup)
            results = [r for r in results if r.get("image_url")][:limit]
            logger.info(
                "[spoonflower] '%s' → %d image(s) bestseller trouvée(s)",
                query, len(results),
            )
            return results
        except Exception as exc:
            logger.warning("[spoonflower] search_bestsellers_with_images '%s': %s", query, exc)
            return []


        """
        Aggregate tags from trending, bestselling, and new pages.

        Args:
            limit: Return the top N tags.

        Returns:
            Dict {tag: count} sorted by count descending.
        """
        all_designs: List[Dict] = []
        all_designs.extend(self.get_trending_designs())
        all_designs.extend(self.get_bestseller_designs())
        all_designs.extend(self.get_new_designs())

        counter = self.extract_tags_from_designs(all_designs)
        top = counter.most_common(limit)
        return dict(top)
