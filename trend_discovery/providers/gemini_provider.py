"""
Provider Gemini — recherche de tendances en temps réel via Google Search.

Utilise Gemini 2.0 Flash avec Google Search grounding pour trouver
les vraies tendances POD mondiales (Spoonflower, fabric design) actuelles.

Produit des "cahiers des charges" complets avec direction visuelle, palettes
de couleurs (hex), références de style, sous-niches, et prompts IA prêts à l'emploi.

Une seule clé : GEMINI_API_KEY
Gemini recherche le web → retourne des données MESURÉES (vraies sources web).

Installation : pip install google-genai
Clé : https://aistudio.google.com/app/apikey
"""
from __future__ import annotations

import json
import logging
import os
from datetime import date
from typing import Dict, List, Optional

import requests

from trend_discovery.providers.base_provider import DataProvider
from trend_discovery.provenance import Metric

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# ── Prompt enrichi pour la génération de cahiers des charges ──────────────────

_TREND_PROMPT_TEMPLATE = """Today is {today}. You are an expert in print-on-demand surface design and Spoonflower fabric patterns.

Search the web and identify the top 12 currently trending niches for {market} patterns and surface design in 2025.

For EACH trend, return a complete JSON object with ALL of these fields — be specific, use real hex codes, real style references:

{{
  "name": "2-4 word English trend name (e.g. Victorian Botanical Seamless)",
  "trending_score": integer 0-100 based on current web/social activity,
  "market_opportunity": "very_high" | "high" | "medium" | "low",
  "why_trending": "factual sentence with evidence (community, searches, recent posts, events)",
  "target_audience": "specific audience description (e.g. home decorators, quilters, crafters)",
  "sub_niches": [
    {{
      "name": "specific 2-5 word sub-niche",
      "trending_score": integer 0-100,
      "unique_angle": "what makes this sub-niche distinct and saleable",
      "prompt_keywords": ["keyword1", "keyword2", "keyword3"]
    }}
  ],
  "visual_direction": {{
    "mood": "comma-separated mood adjectives (e.g. romantic, nostalgic, scientific)",
    "composition": "repeat type and scale description (e.g. half-drop repeat, medium scale)",
    "line_style": "drawing/rendering style (e.g. fine pen lines with watercolor wash)",
    "color_palette": {{
      "primary": ["Color Name #HEXCODE", "Color Name #HEXCODE", "Color Name #HEXCODE"],
      "accent": ["Color Name #HEXCODE", "Color Name #HEXCODE"],
      "background": "Color Name #HEXCODE"
    }},
    "style_references": ["Artist or movement name", "Artist or movement name"],
    "texture": "surface texture description (e.g. aged paper, fine engraving lines)"
  }},
  "spoonflower_fit": {{
    "repeat_type": "half-drop" | "basic" | "brick" | "mirror" | "turn",
    "scale": "small" | "medium" | "large",
    "top_products": ["fabric", "wallpaper", "gift_wrap"],
    "competition_level": "very_high" | "high" | "medium" | "low"
  }},
  "ai_generation": {{
    "positive_prompt": "complete 80-120 word prompt. Must be highly detailed, cover subject, style, technique, colors, composition. Must end with: seamless repeat pattern, tileable, surface design, fabric pattern, professional textile design, flat lay, clean background",
    "negative_prompt": "specific 30-50 word negative prompt tailored to this niche's main pitfalls",
    "key_elements": ["must-have element 1", "must-have element 2", "must-have element 3"],
    "avoid_elements": ["thing to avoid 1", "thing to avoid 2"],
    "cfg_scale": 7.5,
    "style_weight": 0.85
  }},
  "wikimedia_query": "2-5 word query to find public domain reference images on Wikimedia Commons"
}}

Requirements:
- EXACTLY 4 sub-niches per trend
- Real hex codes for ALL colors (no "earthy brown" — use "#8B4513 Saddle Brown")
- positive_prompt must be 80-120 words, vivid, specific, end with the required suffix
- style_references must be real artists or movements (e.g. "William Morris", "Pierre-Joseph Redouté")
- Focus on trends that: are hot RIGHT NOW in 2025, tile beautifully as fabric, have strong visual identity
- wikimedia_query must find actual public domain illustration or art images

Return ONLY a valid JSON array of exactly 12 trend objects. No text before or after. No markdown wrapper.
"""


class GeminiProvider(DataProvider):
    """
    Recherche les tendances POD mondiales via Gemini 2.0 Flash + Google Search.

    Rôle principal : DISCOVERY — trouver les niches qui montent EN CE MOMENT
    sur Spoonflower / fabric design, partout dans le monde, en anglais.

    Produit des cahiers des charges complets avec visuels Wikimedia Commons.
    """

    key = "gemini"
    name = "Gemini 2.0 Flash + Google Search (tendances mondiales temps réel)"
    required_env = ["GEMINI_API_KEY"]
    produces_measured_data = True

    def __init__(self):
        super().__init__()
        self._client = None
        self._trend_cache: Dict[str, Dict] = {}
        self._global_trends: Optional[List[Dict]] = None

    def _check_credentials(self) -> bool:
        return bool(GEMINI_API_KEY)

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from google import genai
            self._client = genai.Client(api_key=GEMINI_API_KEY)
            return self._client
        except ImportError:
            logger.error(
                "[gemini] google-genai non installé. Exécute: pip install google-genai"
            )
            return None
        except Exception as exc:
            logger.error("[gemini] init client échoué: %s", exc)
            return None

    def _call_gemini(self, prompt: str) -> str:
        """
        Appelle Gemini avec Google Search grounding. Retourne le texte brut.

        Ordre de tentatives :
        1. gemini-2.0-flash + Google Search grounding
        2. gemini-2.0-flash sans grounding
        3. gemini-1.5-flash + Google Search grounding (free tier plus permissif)
        4. gemini-1.5-flash sans grounding (dernier recours)
        """
        client = self._get_client()
        if not client:
            return ""

        from google.genai import types

        attempts = [
            ("gemini-2.0-flash", True),
            ("gemini-2.0-flash", False),
            ("gemini-2.0-flash-lite", True),
            ("gemini-2.0-flash-lite", False),
        ]

        for model, use_grounding in attempts:
            try:
                if use_grounding:
                    config = types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        response_modalities=["TEXT"],
                        temperature=0.3,
                    )
                else:
                    config = types.GenerateContentConfig(temperature=0.3)

                response = client.models.generate_content(
                    model=model,
                    contents=prompt,
                    config=config,
                )
                text = response.text or ""
                if text:
                    label = f"{model}{'+search' if use_grounding else ''}"
                    logger.info("[gemini] succès avec %s", label)
                    return text
            except Exception as exc:
                label = f"{model}{'+search' if use_grounding else ''}"
                logger.warning("[gemini] %s échoué: %s", label, str(exc)[:120])

        logger.error("[gemini] tous les modèles/configurations ont échoué")
        return ""

    def _extract_json(self, text: str) -> Optional[list]:
        """
        Extrait un tableau JSON d'une réponse Gemini.
        Gère : ```json ... ```, ``` ... ```, et [ ... ] brut.
        """
        if not text:
            return None

        # 1) Try ```json ... ``` block
        for start_marker, end_marker in [("```json", "```"), ("```", "```")]:
            start = text.find(start_marker)
            if start >= 0:
                content_start = start + len(start_marker)
                end = text.find(end_marker, content_start)
                if end > content_start:
                    json_str = text[content_start:end].strip()
                    try:
                        result = json.loads(json_str)
                        if isinstance(result, list):
                            return result
                    except json.JSONDecodeError:
                        pass

        # 2) Try raw [ ... ] array — use first [ to last ]
        bracket_start = text.find("[")
        bracket_end = text.rfind("]")
        if bracket_start >= 0 and bracket_end > bracket_start:
            json_str = text[bracket_start:bracket_end + 1]
            try:
                result = json.loads(json_str)
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        # 3) Try to find first { ... } if array wrapping is missing
        brace_start = text.find("{")
        brace_end = text.rfind("}")
        if brace_start >= 0 and brace_end > brace_start:
            json_str = "[" + text[brace_start:brace_end + 1] + "]"
            try:
                result = json.loads(json_str)
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                pass

        return None

    # ── Wikimedia Commons image search (no API key needed) ────────────────────

    def find_wikimedia_images(self, query: str, limit: int = 2) -> List[Dict]:
        """
        Cherche des images publiques sur Wikimedia Commons.

        Utilise l'API MediaWiki (pas de clé requise).
        Retourne des URLs d'images en domaine public pour servir de références visuelles.

        Args:
            query: terme de recherche (ex: "victorian botanical illustration engraving")
            limit: nombre maximum d'images à retourner

        Returns:
            Liste de dicts: {title, url, width, height}
        """
        try:
            params = {
                "action": "query",
                "generator": "search",
                "gsrsearch": f"filetype:bitmap {query}",
                "gsrnamespace": 6,
                "gsrlimit": max(limit + 1, 3),  # fetch a few extra to filter
                "prop": "imageinfo",
                "iiprop": "url|dimensions|mime",
                "format": "json",
            }
            resp = requests.get(
                "https://commons.wikimedia.org/w/api.php",
                params=params,
                timeout=10,
                headers={"User-Agent": "Moneymaker/1.0 (https://github.com/hugokeirsse-byte/Moneymaker; POD trend research)"},
            )
            resp.raise_for_status()
            data = resp.json()

            pages = data.get("query", {}).get("pages", {})
            results: List[Dict] = []
            for page in pages.values():
                info_list = page.get("imageinfo", [])
                if not info_list:
                    continue
                info = info_list[0]
                mime = info.get("mime", "")
                if mime not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
                    continue
                url = info.get("url", "")
                if not url:
                    continue
                results.append({
                    "title": page.get("title", "").replace("File:", ""),
                    "url": url,
                    "width": info.get("width", 0),
                    "height": info.get("height", 0),
                })
                if len(results) >= limit:
                    break

            logger.debug(
                "[gemini] Wikimedia '%s': %d image(s) trouvée(s)", query, len(results)
            )
            return results

        except Exception as exc:
            logger.warning("[gemini] Wikimedia search failed for '%s': %s", query, exc)
            return []

    # ── Méthode principale : découverte de tendances ───────────────────────────

    def fetch_global_pod_trends(self, market: str = "Spoonflower fabric design") -> List[Dict]:
        """
        Recherche les niches tendance mondiales pour le marché POD donné.

        Utilise Google Search grounding → données réelles du web d'aujourd'hui.
        Retourne des cahiers des charges complets avec direction visuelle, palettes
        de couleurs (hex), références de style, sous-niches structurées, et prompts IA.

        Met en cache les résultats pour éviter les appels répétés.

        Returns:
            Liste de dicts structurés avec tous les champs du cahier des charges.
        """
        if self._global_trends is not None:
            return self._global_trends

        today = date.today().isoformat()
        prompt = _TREND_PROMPT_TEMPLATE.format(today=today, market=market)

        raw = self._call_gemini(prompt)
        if not raw:
            logger.warning("[gemini] fetch_global_pod_trends: réponse vide")
            return []

        trends = self._extract_json(raw)
        if not trends:
            logger.warning(
                "[gemini] parse JSON échoué. Début réponse: %s...", raw[:400]
            )
            return []

        valid = []
        for t in trends:
            if not isinstance(t, dict) or not t.get("name"):
                continue

            # ── Garantir tous les champs top-level ──────────────────────────
            t.setdefault("trending_score", 50)
            t.setdefault("market_opportunity", "medium")
            t.setdefault("why_trending", "")
            t.setdefault("target_audience", "")
            t.setdefault("sub_niches", [])
            t.setdefault("wikimedia_query", t["name"].lower().replace(" ", " "))

            # ── Visual direction ─────────────────────────────────────────────
            vd = t.setdefault("visual_direction", {})
            vd.setdefault("mood", "")
            vd.setdefault("composition", "")
            vd.setdefault("line_style", "")
            vd.setdefault("texture", "")
            vd.setdefault("style_references", [])
            cp = vd.setdefault("color_palette", {})
            cp.setdefault("primary", [])
            cp.setdefault("accent", [])
            cp.setdefault("background", "")

            # ── Spoonflower fit ──────────────────────────────────────────────
            sf = t.setdefault("spoonflower_fit", {})
            sf.setdefault("repeat_type", "basic")
            sf.setdefault("scale", "medium")
            sf.setdefault("top_products", ["fabric"])
            sf.setdefault("competition_level", "medium")

            # ── AI generation ────────────────────────────────────────────────
            ag = t.setdefault("ai_generation", {})
            ag.setdefault("positive_prompt", "")
            ag.setdefault("negative_prompt", "")
            ag.setdefault("key_elements", [])
            ag.setdefault("avoid_elements", [])
            ag.setdefault("cfg_scale", 7.5)
            ag.setdefault("style_weight", 0.85)

            # ── Normalize sub_niches ─────────────────────────────────────────
            normalized_subs = []
            for sub in t.get("sub_niches", []):
                if isinstance(sub, str):
                    normalized_subs.append({
                        "name": sub,
                        "trending_score": 50,
                        "unique_angle": "",
                        "prompt_keywords": [],
                    })
                elif isinstance(sub, dict):
                    sub.setdefault("trending_score", 50)
                    sub.setdefault("unique_angle", "")
                    sub.setdefault("prompt_keywords", [])
                    normalized_subs.append(sub)
            t["sub_niches"] = normalized_subs

            # ── Legacy fields for backward compatibility ─────────────────────
            # Keep old-style fields so existing pipeline code still works
            color_palette = t["visual_direction"]["color_palette"]
            primary_colors = color_palette.get("primary", [])
            accent_colors = color_palette.get("accent", [])
            t.setdefault(
                "color_keywords",
                [c.split("#")[0].strip() for c in primary_colors[:3] + accent_colors[:1]],
            )
            t.setdefault(
                "style_keywords",
                [
                    t["visual_direction"].get("mood", ""),
                    t["visual_direction"].get("line_style", ""),
                    t["visual_direction"].get("texture", ""),
                ][:6],
            )
            t.setdefault(
                "seamless_suitability",
                "high" if sf.get("competition_level") != "very_high" else "medium",
            )
            t.setdefault("spoonflower_demand", sf.get("competition_level", "medium"))

            valid.append(t)
            # Cache par nom exact et lowercase
            self._trend_cache[t["name"]] = t
            self._trend_cache[t["name"].lower()] = t

        self._global_trends = valid
        logger.info(
            "[gemini] %d tendances mondiales trouvées via Google Search", len(valid)
        )
        return valid

    def build_production_briefs(self) -> List[Dict]:
        """
        Construit des cahiers des charges complets avec images de référence Wikimedia.

        Étapes :
        1. Appelle fetch_global_pod_trends() pour obtenir les 12 tendances structurées
        2. Pour chaque tendance, cherche des images Wikimedia Commons (domaine public)
        3. Retourne la liste enrichie avec le champ `reference_images`

        Returns:
            Liste de tendances enrichies avec reference_images [{title, url, width, height}]
        """
        trends = self.fetch_global_pod_trends()
        enriched = []

        for trend in trends:
            trend_copy = dict(trend)
            query = trend_copy.get("wikimedia_query", trend_copy.get("name", ""))
            images = self.find_wikimedia_images(query, limit=2)
            trend_copy["reference_images"] = images
            enriched.append(trend_copy)
            logger.debug(
                "[gemini] '%s' → %d image(s) de référence", trend_copy["name"], len(images)
            )

        logger.info(
            "[gemini] %d cahiers des charges construits (avec images Wikimedia)", len(enriched)
        )
        return enriched

    # ── Enrichissement des noms de niches ─────────────────────────────────────

    def get_enriched_niche_names(self) -> List[str]:
        """Retourne les noms des tendances + sous-niches pour injection dans le pipeline."""
        trends = self.fetch_global_pod_trends()
        names = []
        for t in trends:
            names.append(t["name"])
            for sub in t.get("sub_niches", []):
                if isinstance(sub, dict):
                    names.append(sub.get("name", ""))
                elif isinstance(sub, str):
                    names.append(sub)
        return list(dict.fromkeys(n for n in names if n))

    def load_trends_into_cache(self, trends: List[Dict]) -> None:
        """
        Charge manuellement des tendances dans le cache (utile pour les tests).

        Args:
            trends: liste de dicts de tendances (même format que fetch_global_pod_trends)
        """
        for t in trends:
            if isinstance(t, dict) and t.get("name"):
                self._trend_cache[t["name"]] = t
                self._trend_cache[t["name"].lower()] = t
        if trends:
            self._global_trends = trends
        logger.debug("[gemini] %d tendances chargées dans le cache", len(trends))

    # ── Métriques compatibles avec le système existant ────────────────────────

    def demande_metric(self, niche: str) -> Metric:
        """
        Métrique de demande depuis le cache Gemini.
        Retourne MEASURED si la niche a été trouvée dans les tendances web.
        """
        cached = self._trend_cache.get(niche) or self._trend_cache.get(niche.lower())
        if cached:
            score = float(cached.get("trending_score", 50))
            why = cached.get("why_trending", "tendance web confirmée")
            return Metric.measured(
                round(min(100.0, max(0.0, score)), 1),
                source="gemini+google_search",
                confidence=75.0,
                detail=f"Gemini web search: {why[:100]}",
            )
        return Metric.unavailable(detail=f"'{niche}' absent des tendances Gemini")

    def get_trend_metadata(self, niche: str) -> Optional[Dict]:
        """Retourne les métadonnées complètes d'une tendance (pour le prompt builder)."""
        return self._trend_cache.get(niche) or self._trend_cache.get(niche.lower())
