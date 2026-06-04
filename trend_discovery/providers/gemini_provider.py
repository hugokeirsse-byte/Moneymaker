"""
Provider Gemini — recherche de tendances en temps réel via Google Search.

Utilise Gemini 2.0 Flash avec Google Search grounding pour trouver
les vraies tendances POD mondiales (agnostique au marché : voir MarketProfile).

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
from typing import Dict, List, Optional, Union

import requests

from trend_discovery.markets.market_profile import MarketProfile, SPOONFLOWER
from trend_discovery.providers.base_provider import DataProvider
from trend_discovery.provenance import Metric

logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")


def _coerce_profile(profile: Union[MarketProfile, str, None]) -> MarketProfile:
    """
    Compat ascendante : accepte un MarketProfile, une chaîne (clé/marché) ou None.

    Les anciens appels passaient une chaîne `market` ou rien — on retombe alors
    proprement sur le profil Spoonflower par défaut.
    """
    if isinstance(profile, MarketProfile):
        return profile
    if isinstance(profile, str) and profile:
        from trend_discovery.markets.market_profile import get_profile
        return get_profile(profile)
    return SPOONFLOWER


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
        self._available_models: Optional[List[str]] = None

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

    def _discover_models(self) -> List[str]:
        """
        Demande à l'API la liste réelle des modèles disponibles pour cette clé.

        Robuste face aux dépréciations : au lieu de deviner les noms de modèles,
        on utilise ceux que l'API déclare réellement supporter pour generateContent.
        """
        if self._available_models is not None:
            return self._available_models
        client = self._get_client()
        models: List[str] = []
        if client:
            try:
                for m in client.models.list():
                    name = (getattr(m, "name", "") or "").replace("models/", "")
                    methods = (
                        getattr(m, "supported_actions", None)
                        or getattr(m, "supported_generation_methods", None)
                        or []
                    )
                    if name and (not methods or "generateContent" in methods):
                        models.append(name)
                logger.info(
                    "[gemini] %d modèles disponibles pour cette clé : %s",
                    len(models), ", ".join(models[:20]),
                )
            except Exception as exc:
                logger.warning("[gemini] list models échoué : %s", str(exc)[:200])
        self._available_models = models
        return models

    def _ranked_flash_models(self) -> List[str]:
        """Modèles 'flash' disponibles, classés du plus récent/capable au moins."""
        import re
        discovered = self._discover_models()
        exclude = ("image", "tts", "audio", "embedding", "vision", "live", "thinking")
        flash = [m for m in discovered if "flash" in m and not any(x in m for x in exclude)]

        def score(m: str) -> float:
            s = 0.0
            ver = re.search(r"(\d+\.\d+)", m)
            if ver:
                s += float(ver.group(1)) * 10
            if "lite" in m:
                s -= 2
            if "latest" in m:
                s += 1.5
            if "preview" in m or "exp" in m:
                s -= 1
            return s

        ranked = sorted(flash, key=score, reverse=True)
        # Fallbacks codés en dur (modèles courants 2025-2026), ajoutés s'ils manquent
        for fb in ("gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash",
                   "gemini-2.5-flash-lite", "gemini-2.0-flash-lite"):
            if fb not in ranked:
                ranked.append(fb)
        return ranked

    def _call_gemini(self, prompt: str) -> str:
        """
        Appelle Gemini avec Google Search grounding. Retourne le texte brut.

        Stratégie robuste :
        1. Découvre les modèles 'flash' réellement disponibles pour la clé
        2. Essaie les meilleurs candidats, chacun AVEC puis SANS grounding web
        """
        client = self._get_client()
        if not client:
            return ""

        from google.genai import types

        candidates = self._ranked_flash_models()[:4]  # top 4 modèles
        logger.info("[gemini] candidats testés : %s", ", ".join(candidates))

        for model in candidates:
            for use_grounding in (True, False):
                label = f"{model}{'+search' if use_grounding else ''}"
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
                        model=model, contents=prompt, config=config,
                    )
                    text = response.text or ""
                    if text:
                        logger.info("[gemini] succès avec %s", label)
                        return text
                except Exception as exc:
                    logger.warning("[gemini] %s échoué : %s", label, str(exc)[:140])

        logger.error(
            "[gemini] tous les modèles/configurations ont échoué — "
            "quota free-tier à 0 ? Active la facturation sur le projet Google Cloud."
        )
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

    # ── Construction du prompt de tendances depuis un MarketProfile ────────────

    def _build_trend_prompt(
        self,
        profile: MarketProfile,
        today: str,
        extra_constraints: str = "",
    ) -> str:
        """
        Construit le prompt de découverte de tendances À PARTIR d'un MarketProfile.

        Tout le savoir marché (plateforme, produits, signaux de recherche,
        catégories saturées, contraintes d'export, nombre de niches) est injecté
        depuis le profil — le moteur reste donc agnostique au marché : changer de
        plateforme = changer de MarketProfile, sans toucher à ce code.

        Args:
            profile: le MarketProfile décrivant le marché ciblé.
            today: date du jour (ISO) injectée dans le prompt.
            extra_constraints: contraintes additionnelles de l'opérateur
                (ex: termes à exclure / sujets à privilégier).

        Returns:
            Le prompt complet prêt à passer à _call_gemini.
        """
        of = profile.output_format or {}
        file_fmt = of.get("file", "PNG")
        dpi = of.get("dpi", 300)
        min_px = of.get("min_px", 4500)
        color_profile = of.get("color_profile", "sRGB")
        max_mb = of.get("max_mb", 40)

        products = ", ".join(profile.product_types) or "surface design products"
        buyers = ", ".join(profile.buyer_segments) or "independent buyers"
        signals = "\n".join(f"- {s}" for s in profile.research_signals) or "- current marketplace bestsellers and trending tags"
        excluded = ", ".join(profile.excluded_generic) or "broad generic themes"
        name = profile.display_name

        # Contrainte de repeat seamless selon le profil
        if profile.repeat_required:
            repeat_line = (
                "Every niche MUST tile beautifully as a SEAMLESS REPEAT pattern "
                "(perfect edge-to-edge tile, no visible seam)."
            )
            quality_suffix = (
                "seamless repeat pattern, tileable, surface design, fabric pattern, "
                "professional textile design, flat lay, even lighting, high detail, "
                f"{dpi} DPI, clean background"
            )
            repeat_field_hint = '"repeat_type": "half-drop" | "basic" | "brick" | "mirror" | "turn",'
        else:
            repeat_line = (
                "Each niche must work as a strong standalone composition for the "
                "products listed (no seamless tiling required)."
            )
            quality_suffix = (
                "clean professional artwork, bold composition, even lighting, "
                f"high detail, {dpi} DPI, clean background"
            )
            repeat_field_hint = '"repeat_type": "standalone" | "centered" | "allover",'

        extra_block = ""
        if extra_constraints:
            extra_block = (
                "\nOPERATOR CONSTRAINTS (must respect):\n"
                f"{extra_constraints}\n"
            )

        crossover_count = getattr(profile, "crossover_count", 2)
        total_count = profile.niche_count + crossover_count

        return f"""Today is {today}. You are an expert in print-on-demand surface design for {name}.

Use Google Search to find REAL, CURRENT data SPECIFIC to {profile.platform_description}. Identify {total_count} OPPORTUNITY niches total: {profile.niche_count} mainstream opportunity niches + {crossover_count} crossover gap niches (see instructions at the bottom) — all with strong and growing buyer demand BUT that are NOT yet oversaturated.

Research these real {name} signals before answering:
{signals}

The products buyers actually purchase here: {products}.
The buyer segments to design for: {buyers}.
{extra_block}
CRITICAL selection rules:
- PRIORITIZE the opportunity gap: high demand + LOW or MEDIUM competition. A niche with huge demand but "very_high" competition is NOT a good pick — skip it or find a fresh sub-angle.
- EXCLUDE oversaturated/generic categories: {excluded} — unless you find a genuinely fresh, specific, underserved angle.
- Every niche must be SPECIFIC and differentiated (a precise aesthetic + subject combo), never a broad generic theme.
- "trending_score" must represent the OPPORTUNITY (demand strength × scarcity of competition), NOT raw popularity. Rank the {profile.niche_count} by this opportunity score, best first.
- {repeat_line}

For EACH trend, return a complete JSON object with ALL of these fields — be specific, use real hex codes, real style references:

{{{{
  "name": "2-4 word English trend name (e.g. Victorian Botanical Seamless)",
  "trending_score": integer 0-100 based on current web/social activity,
  "market_opportunity": "very_high" | "high" | "medium" | "low",
  "why_trending": "2 factual sentences: (1) the real demand evidence you found on the web, (2) why it is an OPPORTUNITY on {name} specifically — i.e. demand is rising but competition is still beatable, and the fresh angle that sets it apart",
  "target_audience": "specific {name} buyer segment + what they make (drawn from: {buyers})",
  "sub_niches": [
    {{{{
      "name": "specific 2-5 word sub-niche",
      "trending_score": integer 0-100,
      "unique_angle": "what makes this sub-niche distinct and saleable",
      "prompt_keywords": ["keyword1", "keyword2", "keyword3"]
    }}}}
  ],
  "visual_direction": {{{{
    "mood": "comma-separated mood adjectives (e.g. romantic, nostalgic, scientific)",
    "composition": "repeat type and scale description (e.g. half-drop repeat, medium scale)",
    "line_style": "drawing/rendering style (e.g. fine pen lines with watercolor wash)",
    "color_palette": {{{{
      "primary": ["Color Name #HEXCODE", "Color Name #HEXCODE", "Color Name #HEXCODE"],
      "accent": ["Color Name #HEXCODE", "Color Name #HEXCODE"],
      "background": "Color Name #HEXCODE"
    }}}},
    "style_references": ["Artist or movement name", "Artist or movement name"],
    "texture": "surface texture description (e.g. aged paper, fine engraving lines)"
  }}}},
  "spoonflower_fit": {{{{
    {repeat_field_hint}
    "scale": "small" | "medium" | "large",
    "top_products": ["{(profile.product_types[:1] or ['fabric'])[0]}"],
    "competition_level": "very_high" | "high" | "medium" | "low"
  }}}},
  "ai_generation": {{{{
    "positive_prompt": "ULTRA-COMPLETE 120-180 word prompt engineered to produce the PERFECT pattern in ONE generation (before any upscaling). Must explicitly cover, in this order: (1) main subject and the specific motifs/objects, (2) exact layout and repeat structure (e.g. half-drop, evenly spaced, balanced negative space, no large gaps), (3) art style + medium + technique (e.g. gouache, vintage engraving, flat vector, watercolor), (4) line quality and level of detail, (5) the precise color palette naming the actual hex colors, (6) lighting/shading approach (flat, soft, even — no harsh cast shadows), (7) background treatment. MUST end with exactly: {quality_suffix}",
    "negative_prompt": "specific 40-70 word negative prompt tailored to this niche's exact pitfalls (e.g. for botanical: 'wilted, dead leaves, muddy colors'), plus seam/tiling defects, harsh shadows, text, watermarks, low resolution",
    "key_elements": ["must-have element 1", "must-have element 2", "must-have element 3", "must-have element 4"],
    "avoid_elements": ["thing to avoid 1", "thing to avoid 2", "thing to avoid 3"],
    "cfg_scale": 7.5,
    "style_weight": 0.85
  }}}},
  "wikimedia_query": "2-5 word query to find public domain reference images on Wikimedia Commons",
  "spoonflower_query": "2-5 word query to search Spoonflower bestselling designs for this niche (e.g. 'nordic folk flat pattern')"
}}}}

Requirements:
- EXACTLY 4 sub-niches per trend
- Real hex codes for ALL colors (no "earthy brown" — use "#8B4513 Saddle Brown")
- positive_prompt must be 120-180 words, vivid, specific, follow the 7-part structure, end with the required suffix
- style_references must be real artists or movements (e.g. "William Morris", "Pierre-Joseph Redouté")
- Focus on trends that are hot RIGHT NOW ({today}), have strong visual identity for {name} — each backed by real web evidence in why_trending
- Target export: {file_fmt}, {dpi} DPI, {min_px}x{min_px}px min, {color_profile}, max {max_mb}MB
- wikimedia_query must find actual public domain illustration or art images

MANDATORY CROSSOVER GAP NICHES — the last {crossover_count} entries in the array MUST be "crossover gap" niches.
These are NOT invented — you must RESEARCH and DOCUMENT real unmet demand before including them.

RESEARCH PROTOCOL for each crossover gap:
1. Search Reddit for communities asking for specific fabric/wallpaper/home decor: r/terrariums, r/sourdough, r/fountainpens, r/analog, r/vandwellers, r/aquariums, r/vinylcollectors, r/tarot, r/urbangardening, r/mushroomhunting — look for posts like "I wish there was fabric for...", "can't find wallpaper that matches my..."
2. Search Etsy: confirm that searching "[hobby] fabric pattern" or "[hobby] wallpaper" returns VERY FEW (< 50) truly dedicated, quality designs — not generic
3. Search Pinterest: find active boards proving the community has strong visual identity that translates to surface design
4. Document WHAT you found in the "why_trending" field: quote the real evidence (subreddit, search result count, Pinterest board examples)

Each crossover niche MUST combine: (1) a real passionate micro-community with documented evidence of demand + (2) a distinct visual aesthetic that already has proven appeal (gothic botanical, vintage scientific, mid-century, dark academia, cottagecore-scientific, etc.)

ZERO INVENTED DATA: if you cannot find real evidence of demand for a crossover, do NOT include it — pick a different community where you DO find evidence.

Add "crossover_gap": true and "demand_gap_evidence": "1-2 sentences: what specific evidence you found (e.g. '342 upvote post on r/aquariums asking for underwater botanical wallpaper, Etsy search shows only 8 relevant listings')" to the JSON of each crossover niche.
These crossover niches must also follow ALL the same JSON schema as regular niches.

Return ONLY a valid JSON array of exactly {total_count} trend objects ({profile.niche_count} regular + {crossover_count} crossover gap). No text before or after. No markdown wrapper.
"""

    # ── Normalisation d'une tendance brute Gemini ──────────────────────────────

    def _normalize_trend(self, t: Dict) -> Dict:
        """
        Garantit que tous les champs attendus existent sur une tendance Gemini.

        Sécurise le schéma (top-level, visual_direction, spoonflower_fit,
        ai_generation, sub_niches) et ajoute des champs legacy pour compat
        ascendante avec le prompt builder existant. Ne plante jamais sur un
        JSON Gemini partiel.
        """
        # ── Champs top-level ─────────────────────────────────────────────────
        t.setdefault("trending_score", 50)
        t.setdefault("market_opportunity", "medium")
        t.setdefault("why_trending", "")
        t.setdefault("target_audience", "")
        t.setdefault("sub_niches", [])
        t.setdefault("crossover_gap", False)    # True pour les niches micro-niche crossover
        t.setdefault("demand_gap_evidence", "")  # Preuve concrète de demande inassouvie (crossover uniquement)
        t.setdefault("wikimedia_query", t.get("name", ""))

        # ── Direction visuelle ───────────────────────────────────────────────
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

        # ── Compatibilité plateforme ─────────────────────────────────────────
        sf = t.setdefault("spoonflower_fit", {})
        sf.setdefault("repeat_type", "basic")
        sf.setdefault("scale", "medium")
        sf.setdefault("top_products", ["fabric"])
        sf.setdefault("competition_level", "medium")

        # ── Génération IA ────────────────────────────────────────────────────
        ag = t.setdefault("ai_generation", {})
        ag.setdefault("positive_prompt", "")
        ag.setdefault("negative_prompt", "")
        ag.setdefault("key_elements", [])
        ag.setdefault("avoid_elements", [])
        ag.setdefault("cfg_scale", 7.5)
        ag.setdefault("style_weight", 0.85)

        # ── Normalisation des sous-niches ────────────────────────────────────
        normalized_subs = []
        for sub in t.get("sub_niches", []):
            if isinstance(sub, str):
                normalized_subs.append({
                    "name": sub, "trending_score": 50,
                    "unique_angle": "", "prompt_keywords": [],
                })
            elif isinstance(sub, dict):
                sub.setdefault("trending_score", 50)
                sub.setdefault("unique_angle", "")
                sub.setdefault("prompt_keywords", [])
                normalized_subs.append(sub)
        t["sub_niches"] = normalized_subs

        # ── Champs legacy (compat prompt builder existant) ───────────────────
        primary = cp.get("primary", [])
        accent = cp.get("accent", [])
        t.setdefault(
            "color_keywords",
            [c.split("#")[0].strip() for c in primary[:3] + accent[:1]],
        )
        t.setdefault(
            "style_keywords",
            [v for v in (vd.get("mood", ""), vd.get("line_style", ""), vd.get("texture", "")) if v][:6],
        )
        t.setdefault(
            "seamless_suitability",
            "high" if sf.get("competition_level") != "very_high" else "medium",
        )
        t.setdefault("spoonflower_demand", sf.get("competition_level", "medium"))
        return t

    # ── Méthode principale : découverte de tendances ───────────────────────────

    def fetch_global_pod_trends(
        self,
        profile: Union[MarketProfile, str, None] = None,
        extra_constraints: str = "",
    ) -> List[Dict]:
        """
        Recherche les niches tendance mondiales pour le marché POD donné.

        Utilise Google Search grounding → données réelles du web d'aujourd'hui.
        Retourne des cahiers des charges complets avec direction visuelle, palettes
        de couleurs (hex), références de style, sous-niches structurées, et prompts IA.

        Met en cache les résultats pour éviter les appels répétés.

        Args:
            profile: MarketProfile ciblé. Compat ascendante : accepte aussi une
                chaîne (clé marché) ou None → repli sur SPOONFLOWER.
            extra_constraints: contraintes opérateur injectées dans le prompt.

        Returns:
            Liste de dicts structurés avec tous les champs du cahier des charges.
        """
        if self._global_trends is not None:
            return self._global_trends

        profile = _coerce_profile(profile)
        today = date.today().isoformat()
        prompt = self._build_trend_prompt(profile, today, extra_constraints)

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
            t = self._normalize_trend(t)
            valid.append(t)
            # Cache par nom exact et lowercase
            self._trend_cache[t["name"]] = t
            self._trend_cache[t["name"].lower()] = t

        self._global_trends = valid
        logger.info(
            "[gemini] %d tendances mondiales trouvées via Google Search", len(valid)
        )
        return valid

    def critique_and_refine(
        self,
        trends: List[Dict],
        profile: Union[MarketProfile, str, None] = None,
    ) -> List[Dict]:
        """
        Passe d'AUTO-CRITIQUE : un SECOND appel Gemini qui révise les niches proposées.

        Demande à Gemini de :
          - signaler/retirer les niches en réalité sur-saturées,
          - resserrer l'angle différenciant de chaque niche,
          - réécrire les positive_prompts faibles au standard 120-180 mots.

        Le résultat respecte EXACTEMENT le même schéma JSON (liste des mêmes objets,
        affinés). En cas d'échec (réponse vide/invalide), retourne les tendances
        d'origine inchangées — la critique ne doit jamais dégrader le pipeline.

        Args:
            trends: liste des niches proposées (sortie de fetch_global_pod_trends).
            profile: MarketProfile (ou chaîne/None) pour contextualiser la critique.

        Returns:
            La liste affinée (même schéma) ou l'originale si la critique échoue.
        """
        if not trends:
            return trends
        profile = _coerce_profile(profile)

        try:
            trends_json = json.dumps(trends, ensure_ascii=False)
        except (TypeError, ValueError) as exc:
            logger.warning("[gemini] critique : sérialisation JSON échouée : %s", exc)
            return trends

        excluded = ", ".join(profile.excluded_generic) or "broad generic themes"
        prompt = f"""You are a senior {profile.display_name} surface-design strategist reviewing a junior's niche proposals.

Here is the JSON array of proposed niches:
{trends_json}

Critically REVIEW and REFINE this list. Your job:
1. SATURATION CHECK — for any niche that is actually oversaturated or too generic ({excluded}), either drop it or pivot it to a genuinely fresh, underserved angle. Adjust its "competition_level" honestly.
2. SHARPEN the differentiating angle of EVERY niche (name, why_trending, sub_niches[].unique_angle) so each is specific and clearly distinct from the others.
3. UPGRADE any weak "positive_prompt" so EVERY niche has a vivid 120-180 word prompt following the same 7-part structure and ending with the same required suffix as the input.
4. Keep "trending_score" as the OPPORTUNITY score (demand × scarcity); re-rank best first.

Return ONLY a valid JSON array using the EXACT SAME object schema and fields as the input (same keys, same nesting). Do not add or remove fields. No prose, no markdown wrapper."""

        raw = self._call_gemini(prompt)
        if not raw:
            logger.info("[gemini] critique : réponse vide — tendances inchangées")
            return trends

        refined = self._extract_json(raw)
        if not refined:
            logger.info("[gemini] critique : parse JSON échoué — tendances inchangées")
            return trends

        # Garder uniquement les objets nommés valides ; sécuriser tous les champs.
        valid = [t for t in refined if isinstance(t, dict) and t.get("name")]
        if not valid:
            logger.info("[gemini] critique : aucune niche valide — tendances inchangées")
            return trends

        normalized = [self._normalize_trend(t) for t in valid]
        logger.info(
            "[gemini] critique : %d niches affinées (sur %d proposées)",
            len(normalized), len(trends),
        )
        return normalized

    def build_production_briefs(
        self,
        profile: Union[MarketProfile, str, None] = None,
        extra_constraints: str = "",
    ) -> List[Dict]:
        """
        Construit des cahiers des charges complets avec images de référence Wikimedia.

        Étapes :
        1. Appelle fetch_global_pod_trends() pour obtenir les niches structurées
        2. Pour chaque tendance, cherche des images Wikimedia Commons (domaine public)
        3. Retourne la liste enrichie avec le champ `reference_images`

        Args:
            profile: MarketProfile (ou chaîne/None) — repli SPOONFLOWER.
            extra_constraints: contraintes opérateur injectées dans le prompt.

        Returns:
            Liste de tendances enrichies avec reference_images [{title, url, width, height}]
        """
        profile = _coerce_profile(profile)
        trends = self.fetch_global_pod_trends(profile, extra_constraints)
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
