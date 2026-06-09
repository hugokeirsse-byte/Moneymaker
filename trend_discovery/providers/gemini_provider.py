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


def _auto_naturalist_typography(t: Dict) -> Dict:
    """
    Auto-génère les layers de typographie pour une planche naturaliste.

    Extraits :
      - Nom commun  : brief name sans le suffixe "Plate" → position top
      - Nom sci.    : premier genre+espèce trouvé dans positive_prompt → italic_caption
    Couleur texte   : couleur sombre de la palette (luminance < 100) ou #1A1A2E.
    """
    import re

    name = t.get("name", "")
    common_name = re.sub(r"\s*\b(?:plate|planche|specimen|anatomy)\b\s*$", "",
                         name, flags=re.IGNORECASE).strip()

    positive_prompt = t.get("ai_generation", {}).get("positive_prompt", "")
    # Genre + espèce : Majuscule suivie de 1-2 mots en minuscules
    sci_match = re.search(r"\b([A-Z][a-z]+(?:\s+[a-z]+){1,2})\b", positive_prompt)
    scientific_name = sci_match.group(1) if sci_match else ""
    # Évite de dupliquer le nom commun
    if scientific_name.lower() == common_name.lower():
        scientific_name = ""

    # Couleur texte : cherche la plus sombre dans color_primary
    vd = t.get("visual_direction", {})
    colors_raw = vd.get("color_primary", vd.get("color_palette", {}).get("primary", []))
    text_color = "#1A1A2E"
    for c_str in colors_raw:
        hex_m = re.search(r"#([0-9A-Fa-f]{6})", str(c_str))
        if hex_m:
            h = hex_m.group(1)
            r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
            if 0.299 * r + 0.587 * g + 0.114 * b < 100:
                text_color = f"#{h}"
                break

    layers = []
    if common_name:
        layers.append({
            "text": common_name,
            "position": "top",
            "font_style": "serif",
            "size_pt": 32,
            "color": text_color,
            "y_offset_pct": 0.01,
            "max_width_pct": 0.80,
        })
    if scientific_name:
        layers.append({
            "text": scientific_name,
            "position": "bottom",
            "font_style": "serif_italic",
            "size_pt": 26,
            "color": text_color,
            "y_offset_pct": -0.02,
            "max_width_pct": 0.72,
        })

    return {"apply": bool(layers), "layers": layers}


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

        # Inject niche archive memory to prevent repetition
        archive_block = ""
        try:
            import json as _json
            _archive_path = "data/niche_archive.json"
            import os as _os
            if _os.path.exists(_archive_path):
                with open(_archive_path) as _fh:
                    _archive = _json.load(_fh)
                _names = [n["name"] for n in _archive.get("niches", [])]
                if _names:
                    _list = "\n".join(f"- {n}" for n in _names)
                    archive_block = (
                        "\nALREADY GENERATED — DO NOT REPEAT THESE NICHES (or close variants):\n"
                        f"{_list}\n"
                        "Generate entirely NEW and DIFFERENT niches that do not overlap thematically with the above.\n"
                    )
        except Exception:
            pass

        crossover_count = getattr(profile, "crossover_count", 2)
        # Override du nombre de niches via env (ex: viser 20 CDC sur un batch ciblé)
        _override = os.getenv("MONEYMAKER_NICHE_COUNT", "")
        niche_count = int(_override) if _override.isdigit() else profile.niche_count
        total_count = niche_count + crossover_count

        return f"""Today is {today}. You are an expert in print-on-demand surface design for {name}.
{archive_block}
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
  "elements": [
    {{{{
      "id": 1,
      "name": "short element name",
      "role": "hero" | "supporting" | "filler",
      "prompt": "SEE MANDATORY FORMAT BELOW"
    }}}}
    // EXACTLY 10 elements: 2-3 hero, 4-5 supporting, 2-3 filler
  ],
  "assembly_guide": {{{{
    "background_color": "#HEXCODE",
    "layout": "sticker" | "tessellate" | "grid",
    "density": "sparse" | "medium" | "dense",
    "sticker_border": true,
    "sticker_border_color": "#HEXCODE (usually white #FFFFFF or a light accent color)",
    "color_palette": ["#HEXCODE ColorName", "#HEXCODE ColorName", "#HEXCODE ColorName"],
    "tips": "1-2 sentences on grouping and arrangement"
  }}}},
  // layout guide:
  // "sticker"     → elements placed like patches/stickers on background (tossed, varied rotation, visible spacing)
  // "tessellate"  → single motif repeated side-by-side in offset rows (mermaid scales, fish scales, geometric tiles)
  // "grid"        → strict regular grid (symmetric geometric patterns)
  "visual_direction": {{{{
    "mood": "comma-separated mood adjectives (e.g. romantic, nostalgic, scientific)",
    "color_palette": {{{{
      "primary": ["Color Name #HEXCODE", "Color Name #HEXCODE", "Color Name #HEXCODE"],
      "accent": ["Color Name #HEXCODE", "Color Name #HEXCODE"],
      "background": "Color Name #HEXCODE"
    }}}}
  }}}},
  "spoonflower_fit": {{{{
    {repeat_field_hint}
    "scale": "small" | "medium" | "large",
    "top_products": ["{(profile.product_types[:1] or ['fabric'])[0]}"],
    "competition_level": "very_high" | "high" | "medium" | "low"
  }}}},
  "wikimedia_query": "2-5 word query to find public domain reference images on Wikimedia Commons",
  "spoonflower_query": "2-5 word query to search Spoonflower bestselling designs for this niche (e.g. 'nordic folk flat pattern')",
  "sub_niches": [
    {{{{
      "name": "specific sub-angle (2-4 words, e.g. 'Dark Academia Pressed Ferns')",
      "differentiator": "what makes this distinct from the parent niche — different aesthetic, buyer, or product use case",
      "opportunity": "very_high | high | medium | low",
      "buyer_intent": "what specific thing does this buyer want to make/buy (e.g. 'quilting fabric for baby blanket', 'wallpaper for home office')"
    }}}},
    // 3-5 sub-niches — researched REAL sub-angles within this parent niche
  ],
  "ai_generation": {{{{
    "positive_prompt": "SEE MANDATORY FLUX PROMPT FORMAT BELOW — the full seamless-pattern prompt for FLUX Dev 2",
    "cfg_scale": 4.0
  }}}}
}}}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY ELEMENT PROMPT FORMAT (apply to EVERY element)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Each element prompt MUST follow this EXACT structure (under 65 words):
  "One single [SPECIFIC OBJECT NAME], centered on pure white background.
  [NICHE STYLE ANCHOR — the visual tradition this niche belongs to].
  Flat 2D illustration, bold black outline, solid [HEX COLOR from palette] fill.
  No gradients, no shadows, no reflections, no other objects, isolated."

STYLE ANCHOR = the 3-6 word visual tradition that tells the AI model HOW to draw.
This is the most important part. Use the tradition that exists in training data
as inherently flat. Examples by niche type:
  • Japanese/Asian     → "Japanese ukiyo-e woodblock print style"
  • Nordic/Folk        → "Scandinavian folk art, Marimekko style"
  • Victorian science  → "Victorian natural history engraving style"
  • Arts & Crafts      → "William Morris Arts and Crafts flat design"
  • Art Deco           → "1920s Art Deco geometric poster style"
  • Botanical          → "botanical illustration, herbarium label style"
  • Retro/Vintage      → "mid-century modern flat illustration style"
  • Cyanotype          → "Anna Atkins cyanotype photogram style, white silhouette"

WORKED EXAMPLES (Japanese Woodblock niche):
  Hero:      "One single Japanese wave crest with foam tips, centered on pure white background. Japanese ukiyo-e woodblock print style, Hokusai inspired. Flat 2D illustration, bold black outline, solid indigo blue (#1B3A6B) fill, white foam at tips. No gradients, no shadows, no other objects, isolated."
  Support:   "One single cherry blossom branch with three open flowers, centered on pure white background. Japanese woodblock print style. Flat 2D illustration, bold black outline, solid pale pink petals, dark brown branch. No gradients, no shadows, no other objects, isolated."
  Filler:    "One single five-petal sakura blossom, centered on pure white background. Japanese woodblock print style. Flat 2D illustration, bold black outline, solid pale pink (#F4A0A0) petals, small yellow center. No gradients, no shadows, no other objects, isolated."

ROLE SIZING GUIDE:
  hero      : large recognizable shape (the dominant motif of the niche)
  supporting: medium element with clear identity (secondary motifs)
  filler    : small simple shape (accent dots, petals, leaves, small icons)

COLORS: every prompt must use a specific hex from the niche's color_palette.
Do NOT write "blue" — write "sky blue (#87CEEB)".

⚠️ COLOR CONTRAST RULE (critical): element fill colors MUST contrast strongly against background_color.
  • Dark background (luminance < 100, e.g. navy #1B3A6B, forest green #2D5A27, charcoal #333):
      → Use LIGHT fills: white (#FFFFFF), cream (#F5F0E8), pale pink (#F8C8C8), sky blue (#87CEEB),
        gold (#FFD700), coral (#E8855D), lavender (#C9A0DC), sage green (#7DB87D)
      → NEVER use a fill color close to the background (navy fill on navy bg = invisible — just contours)
  • Light background (luminance > 180, e.g. white #FFFFFF, ivory #F5F0E8, cream #FFF8E7):
      → Use DARK or SATURATED fills: deep teal (#1A6B6B), forest green (#2D5A27), burgundy (#7B2D42),
        navy (#1B3A6B), terracotta (#C26A3E), deep purple (#4A235A)
  Verification rule: if the element fill hex is within 60 RGB distance of background_color — WRONG, change it.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
MANDATORY FLUX DEV 2 PROMPT FORMAT (for ai_generation.positive_prompt)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is the single most important field. It is the prompt sent DIRECTLY to FLUX Dev 2
to generate the finished seamless pattern in ONE shot. FLUX Dev 2 is a flow-matching
diffusion model that understands natural descriptive English prose, NOT keyword tags.
Write like you are briefing a skilled human textile illustrator.

══════════════════════════════════════════════
CHOOSE THE APPROPRIATE STYLE TEMPLATE BELOW:
══════════════════════════════════════════════

STYLE A — SCATTERED / TOSSED (isolated elements on solid background)
Use for: Cabinet of curiosities, folk objects, vintage labels, scattered botanicals

  PART 1 — PATTERN DECLARATION: "Seamless tossed/scattered repeat pattern for [DESTINATION]."
  PART 2 — STYLE ANCHOR: "The pattern looks exactly like a [REAL REFERENCE] — [technique]."
  PART 3 — ELEMENTS: Name 5-8 elements with surgical precision + exact anatomy for animals.
  PART 4 — ANTI-FUSION LOCKS: "NO blending, NO merging, NO morphing between any objects.
    Distinct individual fully-formed [MOTIF TYPE] with clear spacing between each element."
  PART 5 — BACKGROUND: "Single solid uniform [COLOR (#HEX)] background across the entire tile,
    no texture, no gradient. All four edges tile perfectly."

──────────────────────────────────────────────
STYLE B — LARGE HERO MOTIF, DENSE FILL (1-3 BIG shapes dominate the tile)
Use for: large tropical leaves, oversized botanicals, bold single-leaf repeats, oversized geometric flowers.
SPOONFLOWER WALLPAPER RULE: each motif must be LARGE enough to read from 2 meters away.
A tile with 20 tiny elements looks like fabric texture — good for cloth, WRONG for wallpaper.
Target: 1-3 dominant shapes each filling 30-60% of the tile height/width.
SOBER PALETTE RULE (mandatory for Style B): 2-3 colors MAXIMUM. The power comes from SCALE and
SIMPLICITY — one giant monstera leaf on a rust background (cream + rust + sage = 3 colors). NOT 7 colors.
Proven bestseller formula: one oversized leaf/flower centered on a bold single-color background,
the repeat creates rhythm without clutter. Examples: pink monstera on terracotta, white peony on navy,
sage palm on charcoal. Rich texture on the motif (brushstroke quality, NOT flat graphic).
──────────────────────────────────────────────

  PART 1 — PATTERN DECLARATION: "Large-scale [half-drop/mirror/brick] repeat pattern
    for high-end wallpaper printing. [N=1-3] large hero motifs dominate the tile —
    each motif filling approximately [40-70]% of the tile height.
    Zero visible background — motif shapes and their colored fills cover the entire tile."

  PART 2 — SCALE ANCHOR (CRITICAL):
    Specify the size of the hero motif explicitly:
    "The central [SHAPE/FLOWER/FAN] spans approximately 70% of the tile width — it is
    LARGE and dominant. Only [2-4] of these motifs appear in the tile — they are not
    small repeating units but bold architectural-scale shapes."
    DO NOT describe dozens of tiny elements. 1-3 large shapes = correct. 20+ = wrong.

  PART 3 — MOTIF ANATOMY + COLOR FILL:
    Describe the large hero shape with crisp internal detail:
    "Each [SHAPE] is drawn with [N] precisely spaced radiating lines from base to arc tip.
    Colors: [2-4 hex codes only]. Each shape is filled with a single flat solid color —
    absolutely no gradient, no texture, no shadow inside any shape."
    Crisp outlines are MANDATORY: "each shape has a clean 2px dark outline separating
    it from neighbors — no blurry edges, no soft gradients."

  PART 4 — DENSITY LOCK:
    "The entire tile surface is covered with NO plain background visible anywhere.
    Every square millimeter is occupied by a motif shape or a colored fill.
    Clean crisp outlines separate each shape — no blurring, no bleeding between shapes."

  PART 5 — CLOSING:
    "All four edges of the tile interlock perfectly with zero seam.
    Designed for high-end wallpaper and premium fabric printing."

WORKED EXAMPLE STYLE B (Art Deco Palm Floral — aara palm type, ~8000 favorites):
  "Large-scale half-drop repeat pattern for high-end wallpaper printing.
  ONE large Art Deco palm fan flower dominates the center of the tile — the fan
  spans 70% of the tile width, radiating from a narrow stem base up to a wide
  arc of 18 precisely spaced palm frond lines. This is a LARGE architectural motif,
  not a small repeating unit. Only 2 full flowers appear in the tile (one centered,
  one half-visible at top edge for half-drop). Zero background visible — the fan
  petals and the colored fills between them cover the entire tile.
  Colors: blush pink (#F2A0A0), warm cream (#FDF6EC), golden amber (#D4A017).
  Each palm frond line is crisp and precise — flat solid fill, no gradient,
  no texture, no shadow inside any shape. Clean 2px outline separates each frond.
  The entire tile surface covered with NO plain background visible anywhere.
  Designed for Spoonflower peel-and-stick wallpaper — bold impact at room scale."

WORKED EXAMPLE STYLE A (Japanese Woodblock niche → ai_generation.positive_prompt):
  "Seamless half-drop repeat pattern for high-end fabric and wallpaper printing.
  The pattern looks exactly like a Hokusai ukiyo-e woodblock print textile —
  bold carved ink outlines, completely flat solid color fills, not a single gradient
  or shadow inside any shape. The design features: a stylized Kanagawa wave crest
  as a flat graphic shape with white foam tips; a white crane in side flight with
  exactly two wings fully extended and exactly two legs tucked under — no extra limbs;
  a red-orange koi in side profile with exactly one dorsal fin and one forked tail
  fin; a cherry blossom branch with flat five-petaled open flowers; a small geometric
  Mount Fuji silhouette. Colors: indigo navy (#1B3A6B), coral vermillion (#E34234),
  ivory white (#F5F2EB), gold ochre (#D4A017). NO blending, NO merging, NO morphing
  between any objects. Distinct individual motifs with clear spacing between each element.
  Single solid uniform ivory (#F5F2EB) background across the entire tile, no texture.
  All four edges tile perfectly. Designed for high-end wallpaper and textile printing."

──────────────────────────────────────────────
STYLE C — ANIMAL GEOMETRY (one animal centered = one tile — Spoonflower mirror does the rest)
Use for: birds, insects, fish, mammals with strong wing/fin/tail geometry.
THE PROVEN BESTSELLER FORMULA: Art Deco Swans 7500+ favorites, Art Deco Cranes, Herons.
HOW IT WORKS: the artist draws ONE animal, uploads it as a tile, Spoonflower mirror repeat
makes wings/fins touch automatically → instant dense interlocking pattern.
Generate ONE animal only — NOT a repeating pattern, NOT multiple animals, just ONE.
──────────────────────────────────────────────

  PART 1 — SINGLE ANIMAL DECLARATION:
    "Single [ANIMAL], centered on a solid [COLOR] background. Art Deco flat graphic
    silhouette style for high-end Spoonflower wallpaper tile.
    The animal fills 75-85% of the tile — equal margin on all 4 edges so Spoonflower
    mirror repeat will connect [wing tips / fin tips / tail] symmetrically."

  PART 2 — POSE & ANATOMY (CRITICAL — this determines if mirror repeat works):
    The animal MUST be posed symmetrically from left to right (facing front or spread):
    "The [ANIMAL] faces directly forward / is seen from above / wings fully spread
    left and right symmetrically. [Wings / fins / tail] extend toward the LEFT and
    RIGHT tile edges — these are the connection points for Spoonflower mirror repeat."
    For birds: wings fully spread, tips near left and right edges, head centered at top.
    For fish: top view, fins spread left/right, tail tip near bottom edge.
    For insects: dorsal view, wings spread left/right symmetrically.
    For mammals: frontal silhouette, antlers/ears near top edge.

  PART 3 — MINIMAL PALETTE (2-3 COLORS MAXIMUM — non-negotiable):
    High contrast is MANDATORY. Proven combinations:
    - Jet black (#0D0D0D) background + cream (#F5F0E8) animal + gold (#C9A84C) accent only on beak/eye
    - Deep navy (#1C2B4A) background + ivory (#FAF7F0) animal + copper (#B87333) accent
    - Charcoal (#2C2C2C) background + blush (#F2C9C0) animal (2 colors only)
    - Forest green (#2D4A2D) background + linen (#F0EBE0) animal + amber (#D4A017) accent
    "The [ANIMAL] is rendered as a single flat [COLOR 1] silhouette on a solid uniform
    [COLOR 2 (#HEX)] background — no gradient, no texture on the background.
    [Optional single accent: [COLOR 3] only on [beak/eye/feather tip/fin edge]]."

  PART 4 — ART DECO FLAT GRAPHIC TREATMENT:
    "Art Deco flat graphic rendering — bold silhouette, crisp hard edges, zero soft shading.
    [Wing feathers / fin rays / tail] drawn as [N] precisely spaced radiating lines, all
    crisp and sharp. The entire body is a single flat [COLOR] — no internal feather
    texture, no fur detail, no photographic shading anywhere. Clean vector-print quality.
    Outlines are firm and precise — no blurry edges."

  PART 5 — CLOSING:
    "Solid uniform [COLOR (#HEX)] background across the entire tile — no texture,
    no vignette, no gradient. Clean flat color to the edges.
    [Wing / fin] tips reach within 5% of the left and right tile edges to enable
    perfect Spoonflower mirror interlocking. 2-3 color palette for maximum
    fabric and wallpaper printing contrast."

WORKED EXAMPLE STYLE C (Art Deco Heron tile):
  "Single great blue heron, centered on a solid jet black (#0D0D0D) background.
  Art Deco flat graphic silhouette style for high-end Spoonflower wallpaper tile.
  The heron fills 80% of the tile — equal margin on all 4 edges so Spoonflower
  mirror repeat will connect wing tips symmetrically.
  The heron faces directly forward, wings fully spread left and right symmetrically.
  Wings extend toward the LEFT and RIGHT tile edges — wing tips reach within 5%
  of the tile edge on both sides. Long neck extended upward, head at the top center.
  The heron is rendered as a single flat cream (#F5F0E8) silhouette on the black background,
  with a single gold (#C9A84C) accent on the long beak only — no other colors.
  Art Deco flat graphic rendering — bold silhouette, crisp hard edges, zero soft shading.
  Primary feathers drawn as 16 precisely spaced radiating lines from shoulder to tip,
  all crisp and sharp. The entire body is flat cream — no internal feather texture,
  no shading, no gradients. Clean vector-print quality.
  Solid uniform jet black (#0D0D0D) background across the entire tile — no texture,
  no vignette, perfectly flat. 3-color palette for maximum wallpaper printing contrast."

──────────────────────────────────────────────
STYLE D — NARRATIVE / HUMOROUS / CONCEPT (the design tells a story or creates surprise)
Use for: anthropomorphized food/objects, trompe l'œil architecture, portrait-gallery animals,
room-specific humor. THE HIGHEST-ENGAGEMENT CATEGORY — Spoonflower award winners repeatedly.

Proven bestseller formulas to inspire (NOT copy — create original variations):
• ANTHROPOMORPHIZED FOOD/VEGGIES: "Carrots Dance" 1539 favs — vegetables with implied human
  bodies/poses, dancing/moving, illustrated with personality. Apply to: mushrooms hiking,
  avocados doing yoga, lemons arguing, radishes at a dinner party.
• PORTRAIT GALLERY ANIMALS: "Cat Cameos" 3347 favs (Award Winner) — animals in Victorian
  portrait medallions/frames on dark rich background. Apply to: dogs as aristocrats, frogs as
  professors, raccoons as thieves in mugshot frames, plants as royalty.
• TROMPE L'OEIL SHELVES: "Instant Library" 864 favs — wallpaper that simulates a real wall
  (bookshelves, wine racks, plate displays, vinyl record racks, terrarium shelves).
  These are room-specific by nature — library/study, kitchen, WC, bar.

ROOM-SPECIFIC HUMOR (specifically for WC / bathroom / kitchen niches):
  These perform extremely well because buyers have a SPECIFIC ROOM in mind:
  • WC / Toilet humor (non-vulgar, elegant): Victorian toilet paper roll patterns,
    plumbing diagrams as blueprints, "throne room" gold crowns + ornate frames
  • Bathroom: soap bar characters, rubber duck fleet, bathtub botanical garden,
    toothbrush cavalry, vintage medicine bottles
  • Kitchen: cookware portraits, spice jar library, recipe card pattern, knife display
  • Study/Library: bookshelf trompe l'oeil, globe collection, map fragments

STYLE D PROMPT STRUCTURE:
  PART 1 — CONCEPT DECLARATION: "Scattered [tossed/repeat] wallpaper featuring [SPECIFIC
    HUMOROUS CONCEPT]. The concept: [one sentence explaining the narrative/joke/surprise]."
  PART 2 — CHARACTER/OBJECT DESCRIPTION: Describe each element with PERSONALITY:
    "Each [CARROT/CAT/BOOK] is [ACTION/POSE/EXPRESSION] — [specific humorous detail].
    Semi-realistic illustration style with hand-drawn quality and visible ink texture."
  PART 3 — PALETTE + RENDERING: Rich illustrated palette (5-8 colors OK for Style D — more
    colors = more character). "Illustrated in [STYLE: Victorian engraving / editorial
    illustration / folk art / botanical illustration style]. Rich warm [PALETTE]."
  PART 4 — COMPOSITION: "Tossed scattered repeat — elements at varied angles and scales.
    Each element is fully formed with NO blending or merging between them."
  PART 5 — BACKGROUND: "Solid [rich dark / warm cream / sage green] background. All edges tile."

──────────────────────────────────────────────
STYLE E — TROMPE L'OEIL RÉALISTE (architectural illusion — the wallpaper IS the view)
Use for: window looking out on forest/garden/ocean, arched stone opening into landscape,
bookshelf wall with depth, vine-covered wall with hidden door, greenhouse glass panes.
THE CONCEPT: the wallpaper creates the illusion that the wall has opened. The buyer's room
gains a VIEW — a forest, a garden at dusk, a Parisian courtyard, a tropical canopy.
This style is the highest-end, most photorealistic approach. It does NOT repeat as tiles —
it is a SINGLE large mural composition (full repeat = half-drop so left/right edges match).
——————————————————————————————
  PART 1 — ILLUSION DECLARATION:
    "Seamless half-drop repeat wallpaper mural creating a trompe l'oeil illusion of [SPECIFIC VIEW].
    The viewer sees [what appears to be visible through the opening] as if standing in the room
    looking at [the architectural element — window frame / stone arch / wrought iron gate]."

  PART 2 — ARCHITECTURAL FRAME (the 'opening'):
    Describe the frame that makes the illusion work — it must be PHOTOREALISTIC:
    "A [carved stone arch / timber window frame / wrought iron arch / mossy stone doorway]
    frames the view. The frame is rendered in photorealistic detail — [specific material:
    aged limestone with lichen, dark weathered oak, wrought iron with rust bloom]. The frame
    occupies the left and right 15% of the tile — its edges interlock in the half-drop repeat
    so that the view between frames reads as one continuous panorama."

  PART 3 — THE VIEW (what lies beyond):
    "Beyond the frame: [SPECIFIC LANDSCAPE]. Rendered in painterly realism:
    [foreground elements], [midground], [background with atmospheric perspective].
    Light source: [golden hour / overcast / dappled morning light].
    Color mood: [muted / saturated / misty]."

  PART 4 — DEPTH + REALISM:
    "The composition has 3 layers of depth: foreground [plants/ivy/flowers] hanging INTO the
    frame, midground [the main landscape feature], background [sky/haze/distant trees].
    Painterly brushstroke quality — NOT flat illustration. Rich textural detail on every surface."

  PART 5 — TILE MECHANICS:
    "Left and right tile edges align perfectly so the panoramic view is CONTINUOUS across
    the wall with no visible seam. Top and bottom edges blend into the sky/ground naturally."

WORKED EXAMPLE STYLE E (Forest Window):
  "Seamless half-drop repeat wallpaper mural: a trompe l'oeil view through a weathered stone
  arch into an ancient deciduous forest at golden hour. The arch is rendered in photorealistic
  carved limestone — pale grey with patches of green lichen and amber rust stains. The arch
  occupies the sides of the tile, its curved edges interlock perfectly in half-drop repeat so
  adjacent arches create a continuous colonnade effect, with the forest vista stretching
  uninterrupted between columns. Beyond the arch: a sunlit forest floor, ancient oak trunks
  with deep bark texture, morning mist filtering through the canopy, shafts of golden light
  hitting patches of forest ferns and moss. Foreground: sprays of fern fronds and ivy
  hanging DOWN from the arch top edge into the frame. Midground: 3-4 oak trunks with
  rich brown-grey bark. Background: pale golden haze, distant tree silhouettes.
  Colors: limestone grey (#B8B0A0), bark brown (#5C3D2E), forest green (#2D5A27),
  golden light (#F5D78E), mist white (#F0EDE8). Painterly realism — NOT flat illustration.
  Each surface has visible texture: rough stone, ridged bark, velvet moss, translucent fern."

──────────────────────────────────────────────
STYLE F — RÉALISTE ÉPARS (scattered photorealistic elements on rich dark background)
Use for: naturalist specimen studies, terrarium floor elements, geological specimens,
forest floor scatter, underwater elements, mineral/crystal collections.
THE AESTHETIC: like image 1 in the reference — rocks, mosses, ferns, wood pieces scattered
on a dark navy/charcoal/forest green background. Rich detailed illustration, almost photographic.
Each element is a SPECIMEN — precise botanical/geological accuracy, visible texture, shadow.
——————————————————————————————
  PART 1 — COLLECTION DECLARATION:
    "Seamless scattered repeat pattern: a naturalist's specimen collection of [SPECIFIC ELEMENTS]
    on a solid [DEEP COLOR (#HEX)] background. Each element is a precisely rendered specimen —
    not stylized, not flat — but illustrated with the fidelity of a natural history museum plate."

  PART 2 — SPECIMEN DESCRIPTIONS (4-6 elements):
    For EACH element: "[SPECIFIC SPECIMEN NAME] rendered with [SPECIFIC TEXTURE DETAIL]:
    [surface characteristic — e.g. 'slate grey with white calcite veining', 'velvet green moss
    capsules with thread-thin stalks', 'amber-brown bark with deep longitudinal fissures']."
    Include subtle cast shadows for each element — they rest ON the background, not float.

  PART 3 — PALETTE:
    "Background: solid [deep navy #1B2A3B / forest green #1A2F1A / charcoal #2A2A2A /
    dark slate #1F2535] — flat uniform color, no texture.
    Elements: naturalistic colors — no artificial palette constraints. Each specimen is true-to-life:
    [grey slate, rust-orange lichen, viridian moss, warm tan wood, cream fungi]."

  PART 4 — DENSITY + SCATTER:
    "Elements scattered at varied scales and angles — some overlapping slightly (natural pile),
    some isolated. Medium density — the dark background breathes between specimens.
    NO blending between elements — each is a distinct solid object with its own shadow."

  PART 5 — BACKGROUND:
    "Solid uniform [deep color (#HEX)] background — no gradient, no texture. The specimens
    sit ON this background like objects on a dark felt display surface.
    All four tile edges interlock seamlessly."

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Requirements:
- EXACTLY 10 elements per niche (2-3 hero, 4-5 supporting, 2-3 filler)
- Every element prompt follows the MANDATORY ELEMENT FORMAT above — no exceptions
- ai_generation.positive_prompt follows the MANDATORY FLUX DEV 2 PROMPT FORMAT (5-part structure, 130-180 words, exact anatomy, anti-fusion locks, solid background) — no exceptions
- STYLE ASSIGNMENT RULE: assign each niche to the appropriate style:
    • STYLE A → scattered/tossed objects, stationery, food objects (NO vintage labels, NO retro/MCM — banned)
    • STYLE B → 1-3 LARGE hero motifs (oversized single leaf/flower on bold bg) — 2-3 colors MAX, sober + impactful
    • STYLE C → Art Deco single-animal geometric tile (ONE animal, Spoonflower mirror makes the pattern)
    • STYLE D → anthropomorphized animals in absurd/hilarious situations, trompe l'œil shelves, room-specific humor
    • STYLE E → trompe l'oeil réaliste architectural (window/arch/opening with photorealistic landscape beyond)
    • STYLE F → réaliste épars (scattered photorealistic naturalist specimens on dark background — terrarium/geological)
  STYLE ASSIGNMENT — DATA-DRIVEN: For each discovered trend, assign the style that BEST FITS its organic visual character.
  Let the trend's nature guide the choice — do NOT force a style that doesn't fit the content.
  DIVERSITY RULE: aim for variety across the batch — no more than 4 niches of the same style per batch of 20.
  If MONEYMAKER_FOCUS specifies a style emphasis, follow that instead.
  STYLE C animals (Art Deco single tile — Spoonflower mirror repeat creates the interlocking pattern):
    koi fish, fox, vampire bat, luna moth, manta ray, praying mantis, stag beetle, wolf, jaguar, salamander.
  STYLE D concepts (anthropomorphized animals in WILD/ABSURD situations):
    detectives, chefs at Michelin restaurants, DJs, judges in wigs, racing snails, speed-dating tortoises,
    therapy lobsters, guinea pigs at fancy dinner, frogs at wine tasting, raccoon heist planners.
  STYLE E concepts (trompe l'oeil architectural):
    stone arch into ancient forest, timber window onto misty Japanese garden, wrought-iron gate into Mediterranean courtyard,
    greenhouse window with tropical canopy, crumbling gothic arch into moonlit cemetery garden.
  STYLE F concepts (realistic naturalist scatter):
    forest floor (rocks + moss + ferns + bark), tide pool specimens, mineral/crystal collection, tropical terrarium,
    deep sea floor, geological cross-sections, lichen + stone wall.
  NO vintage labels. NO retro/mid-century modern. NO folk patterns. NO antique objects tossed pattern.
- ai_generation MUST NOT include a "negative_prompt" field — FLUX Dev 2 does not support it
- ai_generation.cfg_scale is ALWAYS 4.0 (FLUX Dev 2), never 7.5
- Real hex codes for ALL colors everywhere (no "earthy brown" — use "#8B4513 Saddle Brown")
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

SUB-NICHE RESEARCH (mandatory for ALL niches):
For each niche, research 3-5 REAL sub-niches — specific micro-angles within the parent trend that have their own distinct buyer, aesthetic variation, or product use case. Each sub-niche should have meaningfully lower competition than the parent, or address a more specific buyer need. Do NOT invent sub-niches — find evidence that buyers are searching for these variations (Etsy, Pinterest, Reddit, Spoonflower search). Sub-niche names should be specific enough that a designer could immediately understand the angle (e.g. "Glow-Dark Terrarium Lichen" vs vague "dark terrarium").

Return ONLY a valid JSON array of exactly {total_count} trend objects ({profile.niche_count} regular + {crossover_count} crossover gap). No text before or after. No markdown wrapper.
"""

    def _build_redbubble_prompt(
        self,
        profile: MarketProfile,
        today: str,
        extra_constraints: str = "",
    ) -> str:
        """
        Prompt Gemini dédié aux designs standalone Redbubble (t-shirts, stickers, mugs).

        Complètement distinct du prompt Spoonflower seamless : ici on cherche des
        concepts humor/niche/identité pour illustrations centrées sur fond blanc,
        pas des tuiles seamless.
        """
        products = ", ".join(profile.product_types)
        buyers = ", ".join(profile.buyer_segments)
        signals = "\n".join(f"- {s}" for s in profile.research_signals)
        excluded = ", ".join(profile.excluded_generic)

        crossover_count = getattr(profile, "crossover_count", 2)
        _override = os.getenv("MONEYMAKER_NICHE_COUNT", "")
        niche_count = int(_override) if _override.isdigit() else profile.niche_count
        total_count = niche_count + crossover_count

        extra_block = ""
        if extra_constraints:
            extra_block = f"\nOPERATOR CONSTRAINTS (must respect):\n{extra_constraints}\n"

        archive_block = ""
        try:
            import json as _json, os as _os
            _archive_path = "data/redbubble_archive.json"
            if _os.path.exists(_archive_path):
                with open(_archive_path) as _fh:
                    _archive = _json.load(_fh)
                _names = [n["name"] for n in _archive.get("niches", [])]
                if _names:
                    _list = "\n".join(f"- {n}" for n in _names)
                    archive_block = (
                        "\nALREADY DONE — DO NOT REPEAT:\n"
                        f"{_list}\n"
                        "Generate entirely new concepts.\n"
                    )
        except Exception:
            pass

        return f"""Today is {today}. You are a principal market analyst at a print-on-demand studio specializing in {profile.display_name}.

MANDATE: Find the white space — niches where buyer demand is documented and real, but the Redbubble
design supply is thin, low-quality, or misses the community's authentic aesthetic.

This is a RESEARCH TASK. You must complete every phase in order. The final JSON must contain the
evidence you found — not what you predict or imagine. Invented data → concept invalid.
{archive_block}{extra_block}
═══════════════════════════════════════════════════════════════════════
PHASE 1 — SATURATION MAPPING  (complete before proposing any concept)
═══════════════════════════════════════════════════════════════════════

Search Redbubble.com right now for each keyword below. Record the approximate result count.
BLACKLIST: any concept that is within 2 degrees of a term returning >40,000 results.

High-saturation terms to measure:
  anxiety · axolotl · capybara · frog · void cat · skeleton · skull ·
  plant mom · mental health · kawaii cat · cottagecore · dark academia ·
  mushroom · gaming · gamer · astrology · moon phases · witchy · pastel goth ·
  rainbow pride · be kind · motivational quote · feminist quote ·
  cat pushing things · depressed · overthinking · introvert

Permanently excluded categories (always blacklisted):
  {excluded}

After searching, write down the approximate result count you found for each term.
Use this map to avoid them. Do NOT rely on memory — search it now.

═══════════════════════════════════════════════════════════════════════
PHASE 2 — PLATFORM RESEARCH  (run all 5 checks for each candidate community)
═══════════════════════════════════════════════════════════════════════

Research these Redbubble-specific signals:
{signals}

For every community you consider, complete ALL five checks:

  CHECK A — REDBUBBLE COMPETITION:
    Search Redbubble for the community's core keyword.
    Record: result count + quality (are existing designs authentic or generic/low-effort?).
    PASS threshold: <20,000 results, OR results exist but are visually generic/miss community aesthetics.

  CHECK B — REDDIT COMMUNITY SIZE & PURCHASE INTENT:
    Find the primary subreddit(s) for this community.
    Search recent posts for: "merch", "sticker", "shirt", "I wish someone made", "where can I buy".
    Record: subreddit size (members) + any direct merch request posts found.
    PASS threshold: >5,000 members, at least one merch-adjacent post found.

  CHECK C — ETSY DEMAND SIGNAL:
    Search Etsy for "[community keyword] sticker" and "[community keyword] shirt".
    Record: number of listings found + whether top listings have recent sales (check "X sold in last 24h").
    PASS threshold: some demand exists on Etsy (>10 listings) with evidence of actual sales.

  CHECK D — TIKTOK / SOCIAL TREND SIGNAL:
    Search TikTok for the community hashtag(s). Check view counts.
    Alternatively: search YouTube or Instagram for community content posted in the last 30 days.
    Record: top hashtag view count or evidence of recent activity.
    PASS threshold: >1M hashtag views on TikTok, OR active YouTube/Instagram community.

  CHECK E — VISUAL IDENTITY TRANSLATES TO MERCH:
    Search Pinterest for "[community] aesthetic" or "[community] art".
    Confirm: does this community have a distinct, consistent visual language that works on a sticker/shirt?
    Record: Pinterest board evidence + visual aesthetic description.
    PASS threshold: at least one active Pinterest board with recognizable visual identity.

MINIMUM REQUIRED: a concept must PASS at least 3 of 5 checks to be included.
Concepts passing all 5 checks get priority. Document which checks passed in demand_evidence.

Products available: {products}
Target buyer segments: {buyers}

═══════════════════════════════════════════════════════════════════════
PHASE 3 — CONCEPT SELECTION & ANTI-CLONE FILTER
═══════════════════════════════════════════════════════════════════════

From your research, select {niche_count} mainstream-niche concepts + {crossover_count} crossover-gap concepts.
Sort by opportunity score (demand strength × competition weakness × community specificity), best first.

ANTI-CLONE FILTER (mandatory):
Before finalizing any concept, ask: "Could this appear as a variation of an existing top-20 Redbubble design?"
  → If YES → reject or find a community-authentic visual angle that no existing design has used.
  → The design must be specific enough that a community insider sees it and thinks "finally, someone who GETS us."

COMMUNITY AUTHENTICITY TEST: the design must include at least one element that:
  - Uses real community jargon, insider terminology, or tool names
  - References a specific technique, ritual, or experience only this community has
  - Would confuse an outsider but immediately resonate with a community member

REJECT if: the concept could be described as "cute [generic animal] + [generic emotion]" or
"[profession] appreciation" without any community-specific visual hook.

OPPORTUNITY SCORING (use for trending_score):
  80-100: MEASURED evidence — actual trending data (TikTok viral, Etsy bestseller, Reddit viral merch request)
  60-79:  STRONG evidence — 4-5 checks passed, community large + Redbubble competition thin
  40-59:  REASONABLE inference — 3 checks passed, adjacent trend with clear crossover
  0-39:   DO NOT INCLUDE — insufficient evidence

═══════════════════════════════════════════════════════════════════════
⚠️  MANDATORY TEXT SEPARATION RULE — READ BEFORE WRITING ANY PROMPT
═══════════════════════════════════════════════════════════════════════

The pipeline uses TWO separate tools:
  1. FLUX Dev 2 → generates the ILLUSTRATION ONLY (no text, no labels, no typography)
  2. text_applicator.py → adds all text AFTER generation, using fonts and precise placement

This separation is non-negotiable: AI image models render text poorly (garbled letters,
wrong spelling). A Python tool adds the text with real fonts at print quality (300 DPI).

CONSEQUENCE FOR YOUR OUTPUT:
  • ai_generation.positive_prompt: ZERO text, labels, typography, written words.
    Describe ONLY the visual elements: specimen, shape, illustration style, colors.
    "NO TEXT" means no annotation labels, no titles, no Latin names, no slogans, no badge text.
  • typography.layers: ALL text goes here — titles, subtitles, labels, annotations, curved badge text.
    Each layer specifies: text content, position, font_style, size_pt, color, and positioning params.

═══════════════════════════════════════════════════════════════════════
REDBUBBLE DESIGN STYLE TEMPLATES  (choose the one that fits the community's authentic aesthetic)
═══════════════════════════════════════════════════════════════════════

STYLE 1 — VINTAGE NATURALIST / SCIENTIFIC ILLUSTRATION
Use for: nature hobbyists (mycologists, birders, entomologists, fishkeepers, fossil hunters),
amateur scientists, field guide aesthetics. These communities HATE generic cute designs.
THE AESTHETIC: 19th century natural history museum plate — precise anatomical detail, field notes,
Latin nomenclature, aged paper quality. Strong merch for stickers, art prints, tote bags.

  PROMPT STRUCTURE:
  PART 1: "Single [SPECIMEN], centered on pure white background. Rendered as a 19th century
    natural history museum plate — the kind found in Audubon, Ernst Haeckel, or Anna Atkins publications."
  PART 2: "Fine pen and ink engraving style — precise cross-hatching, crisp botanical detail.
    [SPECIFIC SPECIMEN ANATOMY: 3-4 anatomically accurate features this community would recognize]."
  PART 3: "[VISUAL DETAIL: ink quality, cross-hatching density, anatomical accuracy — NO TEXT]."
  PART 4: "Colors: [2-4 HEX codes — muted, naturalistic]. No digital gradients. Ink line quality."
  PART 5: "White background. Isolated specimen. NO text, NO labels, NO written words anywhere.
    Bold enough to read at sticker size. Print-ready illustration quality."
  → Text (Latin name, field notes, scale bar) goes in typography.layers, NOT in this prompt.

WORKED EXAMPLE (Amateur Mycologist):
  "Single fly agaric mushroom, centered on pure white background.
  Rendered as a 19th century natural history museum plate in the style of James Sowerby's
  British Fungi illustrations. Fine pen and ink engraving — precise cross-hatching on cap surface,
  anatomically correct gills visible in cross-section, ring (annulus) clearly rendered on stem,
  volva at base. Small magnifying glass and field journal beside the specimen.
  Colors: scarlet cap (#C0392B), cream spots (#F5F0E8), warm white (#FAFAF8), dark ink (#1A1209).
  NO text, NO labels, NO written words. White background. Isolated specimen. Bold at sticker size."

──────────────────────────────────────────────────────────────────────
STYLE 2 — VINTAGE BADGE / MEMBERSHIP CERTIFICATE / GUILD SEAL
Use for: hobbyist pride communities (craft brewers, sourdough bakers, amateur radio, mechanical
keyboard builders, fountain pen collectors, film photographers). The design is an IDENTITY ARTIFACT —
like a vintage club patch, union badge, or official certificate. Instantly recognizable to the community.

  PROMPT STRUCTURE:
  PART 1: "Circular vintage badge design, centered on pure white background.
    Styled as a [1920s/1940s/1950s] [trade guild seal / club membership badge / official certificate]."
  PART 2: "Center illustration: [SPECIFIC TOOL/OBJECT/SYMBOL the community uses daily],
    rendered in woodblock/letterpress style. Surrounding: circular border, decorative elements
    (wreaths, stars, banners, measuring tools) — era-appropriate graphic ornaments. NO TEXT."
  PART 3: "[SPECIFIC DESIGN DETAILS: border elements, stars, wreaths — NO typography, NO letters]."
  PART 4: "Colors: [2-3 HEX codes — muted earth tones, aged feel]. Distressed texture.
    Letterpress-quality printing aesthetic. All text areas left BLANK for Python typography."
  PART 5: "White background. Clean circular composition. NO text, NO lettering, NO words.
    All typography (title, inner ring text, motto) will be added by a separate tool."
  → Badge text (title, inner ring, motto) goes in typography.layers, NOT in this prompt.

WORKED EXAMPLE (Sourdough Baker):
  "Circular vintage badge design, centered on pure white background.
  Styled as a 1930s artisan baker's guild seal — the type printed on flour sack labels.
  Center illustration: a ceramic sourdough crock with an active starter bubbling over the top,
  rendered in woodblock print style. Surrounding border: wheat stalks and measuring scales.
  Inner ring left blank for text overlay. Outer border: distressed badge edge with rope ornament.
  Decorative stars at compass points. NO text, NO lettering, NO written words anywhere.
  Colors: warm amber (#C4933F), cream (#F5F0E8), dark brown (#2C1A0E), muted gold (#A8882A).
  White background. Clean circular composition. Works at 2cm sticker AND 30cm print."

──────────────────────────────────────────────────────────────────────
STYLE 3 — FLAT MODERN VECTOR / TECHNICAL DIAGRAM
Use for: tech communities, engineers, cyclists, runners, data people, SRE/DevOps, scientists.
These communities respond to precision and wit, NOT cuteness. The design looks like a technical
diagram, data visualization, or exploded engineering drawing — but with dry humor or community irony.

  PROMPT STRUCTURE:
  PART 1: "Single [TECHNICAL OBJECT / SYSTEM DIAGRAM], centered on pure white background.
    Flat vector illustration — the precision of a technical manual, the wit of an insider joke."
  PART 2: "[SPECIFIC TECHNICAL ELEMENTS — shapes, components, connectors, status indicators].
    Leave text areas as blank rectangles or placeholder boxes. NO actual text in the image."
  PART 3: "[VISUAL DIAGRAM STRUCTURE: layout, component shapes, indicator lights, color coding].
    Annotation leader lines present but NO labels — text added by Python tool after generation."
  PART 4: "Colors: [2-3 HEX codes — monochrome with one accent color]. Bold geometric shapes, zero gradients."
  PART 5: "White background. Clean vector edges. All label areas left blank. Reads at sticker size."
  → Annotation text (component names, ironic labels, captions) goes in typography.layers.

WORKED EXAMPLE (SRE / Infrastructure Engineer):
  "Single server rack unit diagram, centered on pure white background.
  Flat vector illustration — precision of a data center technical manual.
  4 rack units visible: 1U slot with cooling fans and blinking status LED (red),
  2U slot with cable bundle entry, 4U slot with blank panel, 1U slot with power supply.
  Status LED strip at right: all indicators solid red. Blank label tags on each unit —
  text placeholder rectangles left empty. Temperature gauge at top: needle in red zone.
  Colors: off-white (#F8F8F6), charcoal (#2C2C2C), critical red (#D63031). Zero gradients.
  NO text, NO words, NO labels. White background. Clean vector edges. Reads at sticker size."

──────────────────────────────────────────────────────────────────────
STYLE 4 — EDITORIAL CARTOON / SATIRICAL ILLUSTRATION
Use for: professions with strong dark-humor culture (nurses, teachers, lawyers, academics,
social workers), hobbyists with self-aware community in-jokes, niche fandoms. The design
captures a SHARED EXPERIENCE that makes the community say "this is exactly us."
NOT generic meme format. Must reference something specific to the community's lived reality.

  PROMPT STRUCTURE:
  PART 1: "Single editorial cartoon illustration, centered on pure white background.
    Expressive hand-drawn linework — like a New Yorker cartoon panel meets community merch."
  PART 2: "[SPECIFIC CHARACTER/SCENARIO using real community context — not a generic archetype].
    [VISUAL IRONY: the gap between the expected and actual reality this community experiences daily]."
  PART 3: "[CAPTION or LABEL using community-specific jargon that makes insiders instantly recognize it]."
  PART 4: "Colors: [3-4 HEX codes]. Semi-flat with subtle hand-drawn texture. Expressive ink outlines."
  PART 5: "White background. One central composition. Text legible at sticker size."

WORKED EXAMPLE (Academic Researcher / PhD):
  "Single editorial cartoon illustration, centered on pure white background.
  Expressive hand-drawn linework — New Yorker cartoon quality.
  A lone researcher at a computer, surrounded by a towering spiral of increasingly specific
  academic papers labeled: 'THE LITERATURE', each paper title more obscure than the last.
  The researcher holds a coffee mug labeled 'GRANT PENDING'. Thought bubble reads:
  'My n=12 study will change everything.' Computer screen shows: 'Reviewer 2 has responded.'
  Semi-flat illustration with visible pencil texture. Slight exaggeration in the spiral height.
  Colors: warm charcoal (#2C2C2C), academic paper cream (#F5F0E0), burnt sienna highlight (#C0622A),
  muted blue accent (#3A6B8A). White background. Text legible at sticker size."

──────────────────────────────────────────────────────────────────────
STYLE 5 — RISOGRAPH / WOODBLOCK LIMITED-PALETTE PRINT
Use for: indie art communities, zine culture, printmaking, alternative music fans, underground
craft communities. This aesthetic IS the identity signal — it says "I know what a risograph is."
Bold 2-3 color limited palette, intentional registration variation, grain texture.

  PROMPT STRUCTURE:
  PART 1: "Single risograph-style illustration, centered on pure white background.
    Bold limited-palette print aesthetic — like a 2-color risograph zine cover."
  PART 2: "[SUBJECT with strong graphic silhouette — must read at thumbnail size].
    [COMMUNITY-SPECIFIC SUBJECT that would appear in a zine for this community]."
  PART 3: "Deliberate risograph register variation — slight misalignment between color layers.
    Grain texture on all filled areas. Bold black key layer with flat color overlays."
  PART 4: "Colors: [2-3 HEX codes only — classic riso colors: fluorescent pink (#F76C8A),
    teal (#00A79D), warm red (#F4543C), soy (#D4AC0D)]. Heavy grain on fills."
  PART 5: "White background. Strong graphic composition. Reads at 2cm sticker size."

WORKED EXAMPLE (Zine / Indie Print Community):
  "Single risograph-style illustration, centered on pure white background.
  Bold limited-palette print aesthetic — a 2-color risograph zine cover.
  A hand-cranked Risograph duplicator machine in profile — bold graphic silhouette,
  paper feeding through the drum, a stack of freshly printed zines emerging.
  Community text: 'PRINT IS NOT DEAD'. Deliberate register variation between color layers —
  slight 3px misalignment on the color fill. Heavy grain texture on all solid fills.
  Black key layer with single fluorescent pink (#F76C8A) color overlay.
  White background. Strong graphic silhouette. Reads at 2cm sticker size."

──────────────────────────────────────────────────────────────────────
STYLE 6 — KAWAII CHARACTER  (strict anti-saturation rules apply)
Use ONLY if: the concept involves a community NOT already represented in the axolotl/capybara/frog
wave — and the character has a community-specific prop, tool, or role that makes it instantly
recognizable to insiders. Generic "cute animal + emotion" → REJECTED. Must clear Phase 1 saturation check.

  THE AUTHENTIC KAWAII TEST: replace the animal with a random other animal. Does the design still work?
    → If YES: the character is generic. Reject.
    → If NO (only this specific animal/character with these specific props works for this community): VALID.

  PROMPT STRUCTURE:
  PART 1: "Single [SPECIFIC CHARACTER] with [COMMUNITY-SPECIFIC PROPS/TOOLS], centered on white background.
    Kawaii flat vector illustration — thick black outline, pastel fill, simple rounded shapes."
  PART 2: "[CHARACTER DETAILS with props that ONLY THIS COMMUNITY uses — real tool names, jargon].
    [EXPRESSION that captures the community's shared experience or inside joke]."
  PART 3: "[OPTIONAL TEXT ELEMENT using community-specific phrase or jargon — not a generic quote]."
  PART 4: "Colors: [3-4 HEX codes — pastel palette]. High contrast outline on white background."
  PART 5: "White background. Bold enough to read at 2cm sticker size. No gradients inside shapes."

WORKED EXAMPLE (Mechanical Keyboard Enthusiast):
  "Single chibi keycap character carrying a set of switch lubricating tools, centered on white.
  Kawaii flat vector illustration — thick black outline, pastel fill, simple rounded shapes.
  The keycap character has tiny arms holding: a Tribosys 3204 lubricant bottle and a tiny
  switch opener. Text bubble: 'Linears only.' A half-assembled keyboard lies at its feet labeled
  'endgame (temporary)'. Expression: blissfully satisfied.
  Colors: coral pink (#F7A8A0), pale yellow (#FFF3C4), light grey (#E8E8E8), black (#1A1A1A).
  White background. Bold outline at 2cm sticker size. No gradients."

═══════════════════════════════════════════════════════════════════════
MANDATORY CROSSOVER GAP NICHES — the last {crossover_count} entries MUST be crossover-gap concepts
═══════════════════════════════════════════════════════════════════════

These are NOT invented. You must find real unmet demand at the intersection of two communities
before including a crossover-gap concept.

RESEARCH PROTOCOL for each crossover gap:
1. Search Reddit for posts in niche communities asking for specific merch:
   r/fountainpens, r/sourdough, r/hamradio, r/mechanicalkeyboards, r/fermentation,
   r/mycology, r/birdingforbeginners, r/aquariums, r/minipainting, r/analog,
   r/ultralight, r/caving, r/beekeeping, r/wetfelting, r/fishkeeping, r/cichlids,
   r/homebrewing, r/longtail, r/openwater, r/pikeplants, r/hydroponics
   Look for: "I wish someone made [merch] for [hobby]", "can't find [design] anywhere",
   "does anyone sell [item] for [community]"

2. Confirm low Redbubble supply: search "[hobby keyword] sticker" on Redbubble.
   PASS: fewer than 2,000 quality results for the combined niche intersection.

3. Confirm the two communities share a potential visual overlap — a crossover aesthetic
   that serves BOTH identities simultaneously (e.g. sourdough baker + dark academia →
   vintage bread chemistry diagram; ham radio + retro tech → oscilloscope waveform art print).

4. Document WHAT you found in demand_gap_evidence: quote the actual Reddit post/thread,
   the Redbubble result count, and the visual overlap logic.

ZERO INVENTED CROSSOVERS: if you cannot find real evidence of demand at the intersection,
pick a different community pair where you DO find evidence.

Each crossover-gap concept must have:
  "crossover_gap": true
  "demand_gap_evidence": "concrete evidence: subreddit + post quote + RB result count + visual overlap"

═══════════════════════════════════════════════════════════════════════
JSON SCHEMA — return EXACTLY this structure for each concept
═══════════════════════════════════════════════════════════════════════

{{{{
  "name": "2-4 word concept name — specific, not generic (e.g. 'Sourdough Starter Guild Badge')",
  "concept": "one sentence: what makes an insider say 'finally, someone who GETS us'",
  "style_template": "1|2|3|4|5|6",
  "trending_score": integer 0-100 (see OPPORTUNITY SCORING above — must match evidence level),
  "market_opportunity": "very_high" | "high" | "medium" | "low",
  "competition_evidence": "Redbubble search keyword + result count found + quality note (e.g. 'redbubble search: ham radio sticker → 847 results, mostly generic call sign designs, no naturalist style')",
  "demand_evidence": "which of the 5 checks passed (A/B/C/D/E) + key findings for each: subreddit name+size, TikTok hashtag views, Etsy listing count, Pinterest board, any viral merch post found",
  "why_trending": "2 sentences: (1) specific signal proving demand exists RIGHT NOW, (2) specific reason competition is beatable",
  "target_buyer": "precise person: hobby, platform where they discovered you, product they buy first, where they put it",
  "best_products": ["sticker", "t-shirt"],
  "humor_level": "wholesome" | "relatable" | "absurdist" | "dark-cute" | "niche-pride",
  "niche_community": "specific community name with subreddit if applicable (e.g. 'amateur mycologists (r/mycology, 289k members)')",
  "color_count": 3,
  "visual_direction": {{{{
    "style": "naturalist|vintage-badge|technical-diagram|editorial-cartoon|risograph|kawaii",
    "mood": "comma-separated mood adjectives that match HOW THIS COMMUNITY sees itself",
    "color_palette": {{{{
      "primary": ["Color Name #HEXCODE", "Color Name #HEXCODE"],
      "accent": ["Color Name #HEXCODE"],
      "background": "White #FFFFFF"
    }}}}
  }}}},
  "ai_generation": {{{{
    "positive_prompt": "SEE STYLE TEMPLATES — 80-130 words, ZERO text/labels/typography, illustration only",
    "cfg_scale": 4.0
  }}}},
  "typography": {{{{
    "apply": true,
    "layers": [
      {{{{
        "text": "EXACT TEXT TO RENDER (community jargon, Latin name, badge title, annotation label...)",
        "position": "top_arc | bottom_arc | center | top | bottom | annotation | italic_caption",
        "font_style": "serif_bold | serif | serif_italic | mono | sans | sans_bold",
        "size_pt": 60,
        "color": "#HEXCODE",
        "arc_radius_pct": 38,
        "y_offset_pct": 0.0,
        "x_pct": 0.5,
        "y_pct": 0.5
      }}}},
      // Include ALL text that makes the design community-specific:
      // Style 1 → italic_caption for Latin name + annotation for field notes
      // Style 2 → top_arc for badge title + bottom_arc for motto/year
      // Style 3 → annotation layers for each labeled component
      // Style 4 → bottom for caption + center for ironic label
      // Style 5 → top for main slogan + bottom for subtext
      // Style 6 → bottom for community catchphrase
    ]
  }}}},
  "crossover_gap": false,
  "demand_gap_evidence": "",
  "wikimedia_query": "2-5 word query for public domain reference images on Wikimedia Commons",
  "redbubble_search_query": "the exact 2-4 word search you ran on Redbubble in Phase 1/Check A",
  "sub_niches": [
    {{{{
      "name": "specific sub-angle (2-4 words) — must be distinct, not just a name variation",
      "differentiator": "what sub-community, product type, or visual angle makes this distinct from the parent",
      "opportunity": "very_high | high | medium | low",
      "best_product": "sticker | t-shirt | mug | tote | art-print | phone-case | notebook"
    }}}},
    // 3-5 sub-niches — each with a distinct buyer or product fit. Researched, not invented.
  ]
}}}}

SUB-NICHE RESEARCH (mandatory): for each concept, find 3-5 real sub-angles within the community.
Each must have a distinct buyer or product context. Search Etsy and Reddit to confirm these
sub-angles have actual demand. Example: parent = "Amateur Radio Pride" → sub-niches:
  "CW Morse Code Art Print" (the subset who still use code, not just digital modes),
  "QRP Low-Power Field Radio Sticker" (the portable/backpacking ham radio crowd),
  "SDR Waterfall Display Art" (software-defined radio crowd, younger and tech-forward),
  "ARRL License Class Humor Mug" (exam culture, General/Extra/Technician jokes),
  "Portable Mast Setup Cartoon" (POTA/SOTA activators — park/summit on the air community).

Return ONLY a valid JSON array of exactly {total_count} objects ({niche_count} mainstream + {crossover_count} crossover-gap). No text before or after. No markdown wrapper.
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
        # Champs Redbubble spécifiques (ignorés si Spoonflower)
        t.setdefault("style_template", "")          # "1"-"6" pour les 6 styles Redbubble
        t.setdefault("competition_evidence", "")    # résultat Redbubble + note qualité
        t.setdefault("demand_evidence", "")         # checks A-E passés + données trouvées

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

        # ── Éléments et guide d'assemblage (nouveau schéma element-based) ────
        t.setdefault("elements", [])
        t.setdefault("assembly_guide", {
            "background_color": "#FFFFFF",
            "layout": "tossed",
            "density": "medium",
            "color_palette": [],
            "tips": "",
        })

        # ── Compatibilité plateforme ─────────────────────────────────────────
        sf = t.setdefault("spoonflower_fit", {})
        sf.setdefault("repeat_type", "basic")
        sf.setdefault("scale", "medium")
        sf.setdefault("top_products", ["fabric"])
        sf.setdefault("competition_level", "medium")

        # ── Génération IA ────────────────────────────────────────────────────
        ag = t.setdefault("ai_generation", {})
        ag.setdefault("positive_prompt", "")
        # FLUX Dev 2 ne supporte pas les négatifs — on garde le champ vide pour compat
        ag.pop("negative_prompt", None)  # supprime si Gemini l'a quand même généré
        ag.setdefault("key_elements", [])
        ag.setdefault("avoid_elements", [])
        ag.setdefault("cfg_scale", 4.0)  # FLUX Dev 2 sweet spot (7.5 distort)
        ag.setdefault("style_weight", 0.85)
        # Garde-fou : si Gemini renvoie un CFG type-SDXL (>5), le ramener au range FLUX
        try:
            if float(ag.get("cfg_scale", 4.0)) > 5.0:
                ag["cfg_scale"] = 4.0
        except (TypeError, ValueError):
            ag["cfg_scale"] = 4.0

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

        # ── Typographie (auto-générée pour planches naturalistes) ────────────
        if not t.get("typography"):
            name = t.get("name", "")
            if any(kw in name.lower() for kw in ("plate", "planche", "specimen", "anatomy")):
                t["typography"] = _auto_naturalist_typography(t)
            else:
                t.setdefault("typography", {"apply": False, "layers": []})
        else:
            t["typography"].setdefault("apply", False)
            t["typography"].setdefault("layers", [])

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

        # Orientation thématique pilotable via env (sans toucher au code)
        if not extra_constraints:
            extra_constraints = os.getenv("MONEYMAKER_FOCUS", "")

        profile = _coerce_profile(profile)
        today = date.today().isoformat()
        # Redbubble uses a dedicated standalone-illustration prompt
        if profile.key == "redbubble":
            prompt = self._build_redbubble_prompt(profile, today, extra_constraints)
        else:
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

        if profile.key == "redbubble":
            prompt = f"""You are a senior Redbubble market analyst reviewing a junior's proposed concept list.

Here is the JSON array of proposed concepts:
{trends_json}

Your mandate: apply the same rigorous 3-phase methodology used to generate these concepts.

CRITIQUE PASS — perform ALL of the following:

1. SATURATION RE-CHECK (mandatory for every concept):
   Search Redbubble for each concept's "redbubble_search_query" value.
   If the search returns >30,000 results AND the existing designs are high quality →
   either DROP the concept or PIVOT it to a community-authentic sub-angle with <10,000 results.
   Permanently excluded themes: {excluded}

2. COMMUNITY AUTHENTICITY FILTER:
   For each concept, verify the "ai_generation.positive_prompt" contains at least one detail that:
   - Uses real community jargon, tool names, or insider terminology
   - References a specific experience only this community has
   - Would confuse an outsider but immediately resonate with a community member
   → If missing: REWRITE the positive_prompt to add authentic community specificity.

3. EVIDENCE INTEGRITY CHECK:
   Verify "trending_score" is consistent with what "demand_evidence" actually reports.
   - 80+: requires actual measured data (viral TikTok, Etsy bestseller, Reddit merch request)
   - 60-79: requires 4+ of the 5 checks (A/B/C/D/E) documented in demand_evidence
   - If trending_score is inflated relative to evidence → lower it and note why
   If "competition_evidence" or "demand_evidence" is vague or empty → attempt to fill it with web research.

4. STYLE TEMPLATE MATCH:
   Verify each concept's "ai_generation.positive_prompt" matches its "style_template" number (1-6).
   If mismatched → rewrite the prompt to correctly follow the assigned style template structure.

5. SUB-NICHE SHARPENING:
   For each concept's sub_niches array: verify each sub-niche has a distinct buyer or product angle.
   Reject vague name variations. Ensure "differentiator" explains a real distinction.

6. FINAL RANKING:
   Re-sort the array by opportunity score (demand strength × competition weakness), best first.
   Crossover-gap niches (crossover_gap: true) go last.

Return ONLY a valid JSON array using the EXACT SAME object schema and fields as the input.
Do not add or remove top-level fields. No prose, no markdown wrapper."""

        else:
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
