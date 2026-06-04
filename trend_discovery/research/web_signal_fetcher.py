"""
WebSignalFetcher — validation externe des niches via Gemini + Google Search grounding.

Principe : 2 appels Gemini batchés (tous les niches d'un coup) avec grounding activé.
Si grounding_metadata contient des grounding_chunks → données réelles → Metric MEASURED.
Sinon → Metric HEURISTIC.

Ne plante jamais. Retourne des signaux vides sur erreur réseau.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from trend_discovery.providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


@dataclass
class NicheSignals:
    niche_name: str
    etsy_listing_estimate: Optional[int] = None        # ~count of Etsy listings
    etsy_competition_level: Optional[str] = None       # "low"|"medium"|"high"|"very_high"
    etsy_evidence: str = ""                            # 1 sentence of what was found
    interest_score: Optional[float] = None             # 0-100 web interest
    demand_evidence: str = ""                          # 2-3 real sources/evidence
    trending_now: bool = False
    grounding_confirmed: bool = False                  # True = real web search happened


class WebSignalFetcher:
    def __init__(self, gemini_provider: "GeminiProvider"):
        self._gemini = gemini_provider

    def fetch_all(self, niche_names: List[str]) -> Dict[str, NicheSignals]:
        """Fetches external signals for all niches in 2 batched Gemini calls."""
        results: Dict[str, NicheSignals] = {
            name: NicheSignals(niche_name=name) for name in niche_names
        }
        if not niche_names:
            return results

        try:
            comp_data, comp_grounding = self._fetch_competition_signals(niche_names)
        except Exception as exc:
            logger.warning("[WebSignalFetcher] competition signals failed: %s", exc)
            comp_data, comp_grounding = {}, False

        try:
            demand_data, demand_grounding = self._fetch_demand_signals(niche_names)
        except Exception as exc:
            logger.warning("[WebSignalFetcher] demand signals failed: %s", exc)
            demand_data, demand_grounding = {}, False

        for name in niche_names:
            signals = results[name]

            comp = comp_data.get(name) or {}
            if comp:
                raw_count = comp.get("etsy_count")
                if raw_count is not None:
                    try:
                        signals.etsy_listing_estimate = int(raw_count)
                    except (TypeError, ValueError):
                        pass
                signals.etsy_competition_level = comp.get("competition_level")
                signals.etsy_evidence = comp.get("evidence", "")

            dem = demand_data.get(name) or {}
            if dem:
                raw_score = dem.get("interest_score")
                if raw_score is not None:
                    try:
                        signals.interest_score = float(raw_score)
                    except (TypeError, ValueError):
                        pass
                signals.demand_evidence = dem.get("demand_evidence", "")
                signals.trending_now = bool(dem.get("trending_now", False))

            signals.grounding_confirmed = comp_grounding or demand_grounding

        return results

    def _fetch_competition_signals(self, niches: List[str]) -> Tuple[Dict, bool]:
        """Call 1: Etsy listing counts + competition level for all niches."""
        today = date.today().isoformat()
        niches_json = json.dumps(niches, ensure_ascii=False)
        prompt = (
            f"Today is {today}. Search Etsy RIGHT NOW for the following fabric/wallpaper pattern niches.\n"
            "For each niche, search \"etsy.com [niche name] fabric pattern\" and \"etsy.com [niche name] wallpaper\".\n"
            "Report the approximate number of listings you find and assess competition level.\n\n"
            f"Niches to research: {niches_json}\n\n"
            "Return a JSON array ONLY (no explanation):\n"
            "[{\"niche\": \"exact name from list\", \"etsy_listing_estimate\": number or null, "
            "\"competition_level\": \"low|medium|high|very_high\", "
            "\"evidence\": \"1 sentence: what you found on Etsy\"}]"
        )

        text, grounding_confirmed = self._call_with_grounding_meta(prompt)
        if not text:
            return {}, grounding_confirmed

        parsed = self._parse_json_array(text)
        if not parsed:
            logger.warning("[WebSignalFetcher] competition JSON parse failed: %s...", text[:200])
            return {}, grounding_confirmed

        lower_map = {n.lower(): n for n in niches}
        data: Dict = {}
        for item in parsed:
            if not isinstance(item, dict):
                continue
            niche_key = item.get("niche", "")
            canonical = niche_key if niche_key in niches else lower_map.get(niche_key.lower())
            if not canonical:
                continue
            data[canonical] = {
                "etsy_count": item.get("etsy_listing_estimate"),
                "competition_level": item.get("competition_level"),
                "evidence": item.get("evidence", ""),
            }
        return data, grounding_confirmed

    def _fetch_demand_signals(self, niches: List[str]) -> Tuple[Dict, bool]:
        """Call 2: Web interest/demand signals for all niches."""
        today = date.today().isoformat()
        niches_json = json.dumps(niches, ensure_ascii=False)
        prompt = (
            f"Today is {today}. Search the web RIGHT NOW for these fabric/surface design niches.\n"
            "For each, find evidence of online interest: Pinterest boards, craft blogs, Instagram hashtags, "
            "magazine features, Design Challenges — from the LAST 6 MONTHS.\n\n"
            f"Niches to research: {niches_json}\n\n"
            "Return a JSON array ONLY (no explanation):\n"
            "[{\"niche\": \"exact name from list\", \"interest_score\": 0-100, "
            "\"demand_evidence\": \"2-3 concrete sources you found (name them)\", "
            "\"trending_now\": true/false}]"
        )

        text, grounding_confirmed = self._call_with_grounding_meta(prompt)
        if not text:
            return {}, grounding_confirmed

        parsed = self._parse_json_array(text)
        if not parsed:
            logger.warning("[WebSignalFetcher] demand JSON parse failed: %s...", text[:200])
            return {}, grounding_confirmed

        lower_map = {n.lower(): n for n in niches}
        data: Dict = {}
        for item in parsed:
            if not isinstance(item, dict):
                continue
            niche_key = item.get("niche", "")
            canonical = niche_key if niche_key in niches else lower_map.get(niche_key.lower())
            if not canonical:
                continue
            data[canonical] = {
                "interest_score": item.get("interest_score"),
                "demand_evidence": item.get("demand_evidence", ""),
                "trending_now": item.get("trending_now", False),
            }
        return data, grounding_confirmed

    def _call_with_grounding_meta(self, prompt: str) -> Tuple[str, bool]:
        """Calls Gemini with grounding and extracts grounding_confirmed from metadata."""
        client = self._gemini._get_client()
        if not client:
            return "", False

        try:
            from google.genai import types
        except ImportError:
            logger.warning("[WebSignalFetcher] google-genai not available")
            return "", False

        models = self._gemini._ranked_flash_models()[:4]

        for model in models:
            try:
                config = types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    response_modalities=["TEXT"],
                    temperature=0.2,
                )
                response = client.models.generate_content(
                    model=model, contents=prompt, config=config
                )
                text = response.text or ""
                if not text:
                    continue

                grounding_confirmed = False
                try:
                    candidate = response.candidates[0] if response.candidates else None
                    if candidate:
                        gm = getattr(candidate, "grounding_metadata", None)
                        if gm:
                            chunks = getattr(gm, "grounding_chunks", None) or []
                            queries = getattr(gm, "web_search_queries", None) or []
                            grounding_confirmed = len(chunks) > 0 or len(queries) > 0
                except Exception:
                    pass

                logger.info(
                    "[WebSignalFetcher] %s — grounding_confirmed=%s",
                    model, grounding_confirmed,
                )
                return text, grounding_confirmed

            except Exception as exc:
                logger.warning("[WebSignalFetcher] %s failed: %s", model, str(exc)[:140])
                continue

        return "", False

    @staticmethod
    def _parse_json_array(text: str) -> Optional[list]:
        """Extracts a JSON array from Gemini response text."""
        if not text:
            return None

        for start_marker, end_marker in [("```json", "```"), ("```", "```")]:
            start = text.find(start_marker)
            if start >= 0:
                content_start = start + len(start_marker)
                end = text.find(end_marker, content_start)
                if end > content_start:
                    try:
                        result = json.loads(text[content_start:end].strip())
                        if isinstance(result, list):
                            return result
                    except json.JSONDecodeError:
                        pass

        bracket_start = text.find("[")
        bracket_end = text.rfind("]")
        if bracket_start >= 0 and bracket_end > bracket_start:
            try:
                result = json.loads(text[bracket_start:bracket_end + 1])
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        return None
