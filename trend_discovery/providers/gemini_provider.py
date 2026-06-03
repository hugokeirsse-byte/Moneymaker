"""
Provider Gemini — recherche de tendances en temps réel via Google Search.

Utilise Gemini 2.0 Flash avec Google Search grounding pour trouver
les vraies tendances POD mondiales (Spoonflower, fabric design) actuelles.

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

from trend_discovery.providers.base_provider import DataProvider
from trend_discovery.provenance import Metric

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


class GeminiProvider(DataProvider):
    """
    Recherche les tendances POD mondiales via Gemini 2.0 Flash + Google Search.

    Rôle principal : DISCOVERY — trouver les niches qui montent EN CE MOMENT
    sur Spoonflower / fabric design, partout dans le monde, en anglais.

    Complète Wikipedia (demand measurement) avec du signal en temps réel.
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
        """Appelle Gemini avec Google Search grounding. Retourne le texte brut."""
        client = self._get_client()
        if not client:
            return ""
        try:
            from google.genai import types
            response = client.models.generate_content(
                model="gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    response_modalities=["TEXT"],
                    temperature=0.3,
                ),
            )
            return response.text or ""
        except Exception as exc:
            logger.warning("[gemini] appel API échoué: %s", exc)
            # Fallback sans web search (moins précis mais fonctionnel)
            try:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt,
                )
                return response.text or ""
            except Exception as exc2:
                logger.error("[gemini] fallback aussi échoué: %s", exc2)
                return ""

    def _extract_json(self, text: str) -> Optional[list]:
        """Extrait un tableau JSON d'une réponse Gemini (gère le texte autour)."""
        # Cherche ```json ... ``` ou [ ... ]
        for start_marker, end_marker in [("```json", "```"), ("```", "```"), ("[", "]")]:
            start = text.find(start_marker)
            if start < 0:
                continue
            content_start = start + len(start_marker)
            if end_marker == "]":
                # Find matching bracket for JSON array
                bracket_start = text.find("[")
                if bracket_start < 0:
                    continue
                end = text.rfind("]")
                if end <= bracket_start:
                    continue
                json_str = text[bracket_start: end + 1]
            else:
                end = text.find(end_marker, content_start)
                if end < 0:
                    continue
                json_str = text[content_start:end].strip()
            try:
                result = json.loads(json_str)
                if isinstance(result, list):
                    return result
            except json.JSONDecodeError:
                continue
        return None

    # ── Méthode principale : découverte de tendances ────────────────────────────

    def fetch_global_pod_trends(self, market: str = "Spoonflower fabric design") -> List[Dict]:
        """
        Recherche les niches tendance mondiales pour le marché POD donné.

        Utilise Google Search grounding → données réelles du web d'aujourd'hui.
        Met en cache les résultats pour éviter les appels répétés.

        Returns:
            Liste de dicts avec name, trending_score, sub_niches, style_keywords, etc.
        """
        if self._global_trends is not None:
            return self._global_trends

        today = date.today().isoformat()

        prompt = f"""Today is {today}. Search the web and identify the top 15 currently trending niches for {market} patterns and surface design.

For EACH niche, return a JSON object with exactly these fields:
- "name": English name, 2-4 words (e.g. "Botanical Cottagecore", "Dark Mushroom Forest")
- "trending_score": integer 0-100 based on current web/social activity
- "why_trending": one factual sentence with evidence (community, searches, recent posts)
- "sub_niches": list of 3 specific profitable sub-niches (English, 2-5 words each)
- "color_keywords": list of 3-4 current trending colors for this niche
- "style_keywords": list of 5-6 visual descriptors for AI image generation
- "seamless_suitability": "high", "medium", or "low" — how well it tiles as fabric
- "spoonflower_demand": "very_high", "high", "medium", "low" — estimated demand on Spoonflower

Focus on niches that:
1. Are trending RIGHT NOW in 2025 (not just evergreen classics)
2. Work beautifully as seamless repeat fabric patterns
3. Have strong visual identity and recognizable color palette
4. Represent a real market opportunity (not over-saturated)

Return ONLY a valid JSON array. No text before or after.
"""
        raw = self._call_gemini(prompt)
        if not raw:
            logger.warning("[gemini] fetch_global_pod_trends: réponse vide")
            return []

        trends = self._extract_json(raw)
        if not trends:
            logger.warning(
                "[gemini] parse JSON échoué. Début réponse: %s...", raw[:300]
            )
            return []

        # Normalisation + mise en cache
        valid = []
        for t in trends:
            if not isinstance(t, dict) or not t.get("name"):
                continue
            # Garantir tous les champs
            t.setdefault("trending_score", 50)
            t.setdefault("why_trending", "")
            t.setdefault("sub_niches", [])
            t.setdefault("color_keywords", [])
            t.setdefault("style_keywords", [])
            t.setdefault("seamless_suitability", "medium")
            t.setdefault("spoonflower_demand", "medium")
            valid.append(t)
            # Cache par nom exact et lowercase
            self._trend_cache[t["name"]] = t
            self._trend_cache[t["name"].lower()] = t

        self._global_trends = valid
        logger.info("[gemini] %d tendances mondiales trouvées via Google Search", len(valid))
        return valid

    def get_enriched_niche_names(self) -> List[str]:
        """Retourne les noms des tendances + sous-niches pour injection dans le pipeline."""
        trends = self.fetch_global_pod_trends()
        names = []
        for t in trends:
            names.append(t["name"])
            names.extend(t.get("sub_niches", []))
        return list(dict.fromkeys(names))

    # ── Métriques compatibles avec le système existant ─────────────────────────

    def demande_metric(self, niche: str) -> Metric:
        """
        Métrique de demande depuis le cache Gemini.
        Retourne MEASURED si la niche a été trouvée dans les tendances web.
        """
        # Recherche exacte puis lowercase
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
