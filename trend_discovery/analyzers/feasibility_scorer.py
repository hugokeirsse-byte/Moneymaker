"""
Feasibility scorer — evaluates how easy it is to generate high-quality
POD images for a given niche using AI image generators.
"""
import logging
from dataclasses import dataclass
from typing import Dict, List

logger = logging.getLogger(__name__)

# Rule-based knowledge base for POD image generation feasibility.
# Each entry: niche_keyword_fragment -> score adjustments
_RULES: Dict[str, Dict[str, float]] = {
    # Very AI-friendly subjects
    "botanical": {"prompt_clarity": 90, "seamless_compatibility": 90, "color_flexibility": 85, "image_complexity": 30},
    "floral": {"prompt_clarity": 88, "seamless_compatibility": 92, "color_flexibility": 90, "image_complexity": 28},
    "geometric": {"prompt_clarity": 85, "seamless_compatibility": 95, "color_flexibility": 90, "image_complexity": 20},
    "watercolor": {"prompt_clarity": 82, "seamless_compatibility": 80, "color_flexibility": 88, "image_complexity": 35},
    "abstract": {"prompt_clarity": 75, "seamless_compatibility": 85, "color_flexibility": 92, "image_complexity": 30},
    "minimalist": {"prompt_clarity": 90, "seamless_compatibility": 88, "color_flexibility": 85, "image_complexity": 15},
    "celestial": {"prompt_clarity": 85, "seamless_compatibility": 85, "color_flexibility": 80, "image_complexity": 35},
    "space": {"prompt_clarity": 80, "seamless_compatibility": 78, "color_flexibility": 75, "image_complexity": 45},
    "mushrooms": {"prompt_clarity": 88, "seamless_compatibility": 88, "color_flexibility": 82, "image_complexity": 32},
    "cats": {"prompt_clarity": 85, "seamless_compatibility": 82, "color_flexibility": 80, "image_complexity": 45},
    "dogs": {"prompt_clarity": 83, "seamless_compatibility": 80, "color_flexibility": 78, "image_complexity": 48},
    "birds": {"prompt_clarity": 80, "seamless_compatibility": 82, "color_flexibility": 82, "image_complexity": 42},
    "foxes": {"prompt_clarity": 82, "seamless_compatibility": 82, "color_flexibility": 80, "image_complexity": 44},
    "butterflies": {"prompt_clarity": 85, "seamless_compatibility": 88, "color_flexibility": 88, "image_complexity": 38},
    "bees": {"prompt_clarity": 82, "seamless_compatibility": 85, "color_flexibility": 80, "image_complexity": 35},
    "cottagecore": {"prompt_clarity": 80, "seamless_compatibility": 82, "color_flexibility": 85, "image_complexity": 40},
    "japandi": {"prompt_clarity": 82, "seamless_compatibility": 85, "color_flexibility": 75, "image_complexity": 25},
    "art nouveau": {"prompt_clarity": 78, "seamless_compatibility": 80, "color_flexibility": 80, "image_complexity": 55},
    "retro": {"prompt_clarity": 80, "seamless_compatibility": 82, "color_flexibility": 85, "image_complexity": 38},
    "vintage": {"prompt_clarity": 78, "seamless_compatibility": 78, "color_flexibility": 80, "image_complexity": 42},
    "crystals": {"prompt_clarity": 85, "seamless_compatibility": 82, "color_flexibility": 85, "image_complexity": 38},
    "tropical": {"prompt_clarity": 85, "seamless_compatibility": 88, "color_flexibility": 88, "image_complexity": 35},
    "ocean": {"prompt_clarity": 80, "seamless_compatibility": 80, "color_flexibility": 80, "image_complexity": 42},
    "forest": {"prompt_clarity": 78, "seamless_compatibility": 78, "color_flexibility": 78, "image_complexity": 50},
    "scandinavian": {"prompt_clarity": 82, "seamless_compatibility": 85, "color_flexibility": 80, "image_complexity": 28},
    "moroccan": {"prompt_clarity": 82, "seamless_compatibility": 92, "color_flexibility": 88, "image_complexity": 38},
    "japanese": {"prompt_clarity": 82, "seamless_compatibility": 85, "color_flexibility": 82, "image_complexity": 42},
    "christmas": {"prompt_clarity": 88, "seamless_compatibility": 85, "color_flexibility": 72, "image_complexity": 38},
    "halloween": {"prompt_clarity": 88, "seamless_compatibility": 85, "color_flexibility": 72, "image_complexity": 40},
    "tarot": {"prompt_clarity": 70, "seamless_compatibility": 65, "color_flexibility": 78, "image_complexity": 65},
    "astrology": {"prompt_clarity": 80, "seamless_compatibility": 80, "color_flexibility": 78, "image_complexity": 42},
    "witchy": {"prompt_clarity": 78, "seamless_compatibility": 80, "color_flexibility": 78, "image_complexity": 45},
    "cyberpunk": {"prompt_clarity": 72, "seamless_compatibility": 72, "color_flexibility": 75, "image_complexity": 60},
    "dark academia": {"prompt_clarity": 70, "seamless_compatibility": 68, "color_flexibility": 72, "image_complexity": 62},
    "goblincore": {"prompt_clarity": 72, "seamless_compatibility": 75, "color_flexibility": 72, "image_complexity": 50},
    "solarpunk": {"prompt_clarity": 70, "seamless_compatibility": 75, "color_flexibility": 80, "image_complexity": 50},
    "fairycore": {"prompt_clarity": 75, "seamless_compatibility": 78, "color_flexibility": 82, "image_complexity": 48},
    "boho": {"prompt_clarity": 78, "seamless_compatibility": 80, "color_flexibility": 85, "image_complexity": 40},
}

# Commercial viability of each category for POD
_COMMERCIAL_VIABILITY: Dict[str, float] = {
    "botanical": 88, "floral": 90, "geometric": 85, "watercolor": 85,
    "abstract": 78, "minimalist": 82, "cottagecore": 88, "mushrooms": 82,
    "cats": 88, "dogs": 85, "celestial": 85, "crystals": 80, "witchy": 80,
    "halloween": 88, "christmas": 90, "tropical": 82, "scandinavian": 80,
    "japandi": 78, "boho": 80, "retro": 78, "vintage": 75,
}

_DEFAULT_SCORES = {
    "prompt_clarity": 72,
    "seamless_compatibility": 72,
    "color_flexibility": 75,
    "image_complexity": 50,
    "commercial_viability": 70,
}

# Prompt templates per niche
_PROMPT_TEMPLATES: Dict[str, List[str]] = {
    "botanical": [
        "seamless botanical pattern, watercolor leaves and branches, white background, repeat tile, high detail",
        "endless botanical print, tropical leaves, flat design, vector style, pastel colors",
    ],
    "floral": [
        "seamless floral pattern, watercolor roses and peonies, soft pastel tones, white background, repeat",
        "ditsy floral seamless pattern, small flowers, botanical illustration style, light background",
    ],
    "geometric": [
        "seamless geometric pattern, bold shapes, minimal color palette, modern, flat design, repeat tile",
        "abstract geometric seamless repeat, hexagons and triangles, two-tone, vector",
    ],
    "mushrooms": [
        "seamless mushroom pattern, cute illustrated mushrooms, cottagecore style, pastel, white background",
        "hand-drawn mushroom seamless repeat, forest floor, earthy tones, botanical illustration",
    ],
    "celestial": [
        "seamless celestial pattern, moons stars constellations, dark navy background, gold details, repeat",
        "celestial seamless pattern, sun and moon faces, watercolor style, mystical",
    ],
    "cats": [
        "seamless pattern with cute cats, various poses, cartoon style, pastel background, repeat",
        "minimalist cat silhouette seamless pattern, black and white, geometric",
    ],
}

_DEFAULT_PROMPTS = [
    "seamless {niche} pattern, repeat tile, high quality, surface design, white background",
    "{niche} seamless repeat pattern, digital art, fabric print, detailed illustration",
]


@dataclass
class FeasibilityScore:
    niche: str
    image_complexity: float = 0.0         # 0-100, higher = MORE complex (worse)
    prompt_clarity: float = 0.0           # 0-100, higher = easier to prompt
    seamless_compatibility: float = 0.0   # 0-100, how well it tiles
    color_flexibility: float = 0.0        # 0-100, can be recolored easily
    commercial_viability: float = 0.0     # 0-100, POD market appetite
    overall_feasibility: float = 0.0      # 0-100 composite
    prompt_suggestions: list = None

    def __post_init__(self):
        if self.prompt_suggestions is None:
            self.prompt_suggestions = []


class FeasibilityScorer:
    """Rule-based feasibility assessment for AI-generated POD images."""

    def _lookup(self, niche: str) -> Dict[str, float]:
        """Find the best matching rule for a niche keyword."""
        niche_lower = niche.lower()
        # Exact match
        if niche_lower in _RULES:
            return _RULES[niche_lower].copy()
        # Partial match
        for key, rule in _RULES.items():
            if key in niche_lower or niche_lower in key:
                return rule.copy()
        return _DEFAULT_SCORES.copy()

    def assess_feasibility(self, niche: str) -> FeasibilityScore:
        """
        Calculate the feasibility score for generating POD images for a niche.

        Complexity is inverted: higher complexity = lower contribution to feasibility.
        """
        rules = self._lookup(niche)
        complexity = rules.get("image_complexity", _DEFAULT_SCORES["image_complexity"])
        prompt_clarity = rules.get("prompt_clarity", _DEFAULT_SCORES["prompt_clarity"])
        seamless = rules.get("seamless_compatibility", _DEFAULT_SCORES["seamless_compatibility"])
        color_flex = rules.get("color_flexibility", _DEFAULT_SCORES["color_flexibility"])

        # Commercial viability lookup
        niche_lower = niche.lower()
        commercial = _COMMERCIAL_VIABILITY.get(niche_lower, _DEFAULT_SCORES["commercial_viability"])
        for key, val in _COMMERCIAL_VIABILITY.items():
            if key in niche_lower or niche_lower in key:
                commercial = val
                break

        # Invert complexity for scoring purposes
        ease = 100.0 - complexity

        overall = round(
            ease * 0.15
            + prompt_clarity * 0.30
            + seamless * 0.25
            + color_flex * 0.15
            + commercial * 0.15,
            2,
        )

        prompts = self.generate_prompt_suggestions(niche)

        return FeasibilityScore(
            niche=niche,
            image_complexity=round(complexity, 1),
            prompt_clarity=round(prompt_clarity, 1),
            seamless_compatibility=round(seamless, 1),
            color_flexibility=round(color_flex, 1),
            commercial_viability=round(commercial, 1),
            overall_feasibility=round(overall, 1),
            prompt_suggestions=prompts,
        )

    def generate_prompt_suggestions(self, niche: str) -> List[str]:
        """Return 2 ready-to-use AI image generation prompts for the niche."""
        niche_lower = niche.lower()
        # Exact or partial template lookup
        for key, templates in _PROMPT_TEMPLATES.items():
            if key in niche_lower or niche_lower in key:
                return templates[:2]
        return [t.format(niche=niche) for t in _DEFAULT_PROMPTS]

    def score_niches(self, niches: List[str]) -> List[FeasibilityScore]:
        """Score a list of niches and return sorted by overall_feasibility desc."""
        scores = [self.assess_feasibility(n) for n in niches]
        scores.sort(key=lambda s: s.overall_feasibility, reverse=True)
        return scores
