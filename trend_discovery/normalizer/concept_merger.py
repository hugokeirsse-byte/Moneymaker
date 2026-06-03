"""
Phase 2 — Normalisation des concepts.

Transforme des mots-clés bruts en concepts canoniques exploitables.
Fusionne les synonymes, détecte les doublons, regroupe les termes proches.

Exemple :
    "witch garden", "herbal garden", "medicinal plants", "apothecary herbs"
    → "Herboristerie"
"""
import difflib
import logging
import re
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Ontologie de synonymes POD (canonical_name → [synonyms, variants, fragments])
# ─────────────────────────────────────────────────────────────────────────────
SYNONYM_CLUSTERS: Dict[str, List[str]] = {
    # ── Nature / Botanique ──────────────────────────────────────────────────
    "Botanique": [
        "botanical", "botanique", "botanica", "plant illustration",
        "nature illustration", "natural history", "scientific illustration",
        "victorian botanical", "botanical print", "botanical art",
    ],
    "Floral": [
        "floral", "flowers", "flower pattern", "bloom", "blooms", "blossom",
        "florals", "flowering", "flower design", "rose", "roses", "peony",
        "peonies", "daisy", "daisies", "wildflower", "wildflowers",
        "ditsy floral", "ditsy flowers", "meadow flowers",
    ],
    "Herboristerie": [
        "herbal", "herbs", "herb garden", "herbal garden", "medicinal plants",
        "medicinal herbs", "apothecary", "apothecary herbs", "witch garden",
        "potion garden", "healing plants", "botanical medicine",
        "herboristerie", "plantes médicinales", "plantes aromatiques",
        "aromatic plants", "kitchen herbs", "cottage herbs",
    ],
    "Champignons": [
        "mushroom", "mushrooms", "fungi", "fungus", "toadstool", "toadstools",
        "shiitake", "amanita", "forest mushroom", "wild mushroom",
        "mushroom pattern", "mushroom design",
    ],
    "Océan & Marin": [
        "ocean", "sea", "marine", "nautical", "underwater", "ocean life",
        "sea creatures", "coral", "seaweed", "shells", "shell pattern",
        "beach", "coastal", "wave", "waves", "mermaid",
    ],
    "Tropical": [
        "tropical", "tropics", "jungle", "tropical leaves", "palm", "palms",
        "palm leaf", "monstera", "banana leaf", "tropical plants",
        "tropical flowers", "hawaii", "island",
    ],
    "Forêt": [
        "forest", "woodland", "woods", "trees", "pine", "ferns", "fern",
        "forest floor", "enchanted forest", "dark forest", "boreal forest",
    ],
    "Succulentes & Cactus": [
        "succulent", "succulents", "cactus", "cacti", "desert plants",
        "air plant", "terrarium plants",
    ],
    # ── Animaux ─────────────────────────────────────────────────────────────
    "Chats": [
        "cat", "cats", "kitten", "kittens", "feline", "kitty", "cat pattern",
        "cat design", "cute cats", "tabby",
    ],
    "Chiens": [
        "dog", "dogs", "puppy", "puppies", "canine", "dog pattern",
        "dog design", "cute dogs", "dachshund", "corgi",
    ],
    "Renards": [
        "fox", "foxes", "fox pattern", "fox design", "woodland fox",
        "forest fox", "cute fox",
    ],
    "Cerfs & Biches": [
        "deer", "stag", "doe", "fawn", "reindeer", "woodland deer",
        "forest deer", "deer pattern",
    ],
    "Oiseaux": [
        "bird", "birds", "avian", "feathers", "bird pattern", "songbird",
        "parrot", "tropical bird", "garden bird",
    ],
    "Corbeaux & Chouettes": [
        "raven", "ravens", "crow", "crows", "owl", "owls", "dark bird",
        "gothic bird", "mysterious bird", "halloween bird",
    ],
    "Papillons & Mites": [
        "butterfly", "butterflies", "moth", "moths", "lepidoptera",
        "butterfly pattern", "moth pattern", "insect pattern",
    ],
    "Abeilles": [
        "bee", "bees", "honeybee", "bumble bee", "bumblebee", "honey",
        "beehive", "bee pattern", "bee design", "pollinator",
    ],
    # ── Styles Esthétiques ──────────────────────────────────────────────────
    "Cottagecore": [
        "cottagecore", "cottage core", "cottage aesthetic", "cottage style",
        "rural aesthetic", "country cottage", "english cottage",
        "cottage garden", "cozy cottage",
    ],
    "Dark Academia": [
        "dark academia", "dark academe", "academic aesthetic",
        "gothic academia", "scholarly aesthetic", "old books",
    ],
    "Goblincore": [
        "goblincore", "goblin core", "goblin aesthetic", "frogcore",
        "moss core", "nature hoard", "earthy aesthetic",
    ],
    "Fairycore": [
        "fairycore", "fairy core", "fairy aesthetic", "fae", "faerie",
        "fairy garden", "enchanted", "magical forest",
    ],
    "Witchy & Occulte": [
        "witchy", "witch", "witchcraft", "occult", "mystical", "magic",
        "magical", "spellcraft", "witch aesthetic", "dark magic",
        "pagan", "wicca", "wiccan",
    ],
    "Gothique": [
        "gothic", "goth", "dark gothic", "victorian gothic", "dark aesthetic",
        "macabre", "memento mori", "skulls", "skull pattern",
    ],
    "Solarpunk": [
        "solarpunk", "solar punk", "eco punk", "green future",
        "sustainable aesthetic", "eco aesthetic", "nature tech",
    ],
    "Cyberpunk": [
        "cyberpunk", "cyber punk", "neon city", "dystopian", "sci fi",
        "futuristic", "neon aesthetic", "tech aesthetic",
    ],
    "Japandi": [
        "japandi", "japan scandi", "japanese minimalist", "nordic japanese",
        "wabi sabi", "minimalist japanese",
    ],
    "Boho": [
        "boho", "bohemian", "boho chic", "bohemian style", "hippie",
        "free spirit", "ethnic pattern",
    ],
    # ── Styles Graphiques ───────────────────────────────────────────────────
    "Géométrique": [
        "geometric", "geometry", "geometric pattern", "shapes", "hexagon",
        "triangle", "diamond", "grid", "tessellation", "mosaic",
    ],
    "Abstrait": [
        "abstract", "abstract pattern", "abstract art", "organic shapes",
        "fluid shapes", "blob", "blobs",
    ],
    "Aquarelle": [
        "watercolor", "watercolour", "water color", "painted", "wash",
        "watercolor pattern", "painted pattern",
    ],
    "Minimaliste": [
        "minimal", "minimalist", "minimalism", "clean", "simple",
        "simple pattern", "line art", "line drawing",
    ],
    "Art Nouveau": [
        "art nouveau", "nouveau", "jugendstil", "arts and crafts",
        "organic lines", "flowing lines",
    ],
    "Art Déco": [
        "art deco", "deco", "art déco", "roaring twenties", "gatsby",
        "deco pattern", "twenties", "twenties design",
    ],
    "Rétro & Vintage": [
        "retro", "vintage", "old school", "nostalgic", "mid century",
        "midcentury", "70s", "60s", "50s", "retro pattern", "vintage pattern",
    ],
    "Folk & Traditionnel": [
        "folk", "folklore", "traditional", "ethnic", "tribal", "folk art",
        "folk pattern", "traditional pattern", "naive art",
    ],
    # ── Mystique & Spirituel ────────────────────────────────────────────────
    "Tarot": [
        "tarot", "tarot card", "tarot cards", "major arcana", "minor arcana",
        "oracle", "oracle card", "divination",
    ],
    "Astrologie": [
        "astrology", "zodiac", "horoscope", "astrological", "birth chart",
        "star sign", "star signs", "constellation", "constellations",
    ],
    "Cristaux & Gemmes": [
        "crystal", "crystals", "gemstone", "gem", "gems", "amethyst",
        "quartz", "crystal pattern", "gemstone pattern", "mineral",
    ],
    "Céleste": [
        "celestial", "moon", "stars", "sun", "star", "lunar", "solar",
        "night sky", "galaxy", "cosmos", "celestial pattern",
        "moon and stars", "sun and moon",
    ],
    # ── Saisonnier ──────────────────────────────────────────────────────────
    "Noël": [
        "christmas", "xmas", "holiday", "festive", "winter holiday",
        "christmas pattern", "xmas pattern", "santa", "reindeer",
        "christmas tree", "snowflake", "snowflakes",
    ],
    "Halloween": [
        "halloween", "spooky", "trick or treat", "pumpkin", "pumpkins",
        "skeleton", "ghosts", "bat", "bats", "halloween pattern",
        "haunted", "creepy cute",
    ],
    "Pâques": [
        "easter", "spring", "bunny", "bunnies", "easter egg", "egg pattern",
        "chick", "chicks", "spring flowers",
    ],
    # ── Culturel ────────────────────────────────────────────────────────────
    "Japonais": [
        "japanese", "japan", "japanese pattern", "kimono pattern",
        "cherry blossom", "sakura", "koi", "koi fish", "sumi e",
        "ukiyo e", "japanese art", "zen", "torii",
    ],
    "Scandinave": [
        "scandinavian", "nordic", "norwegian", "swedish", "danish",
        "hygge", "scandi", "nordic pattern", "scandi pattern",
        "folk scandinavian",
    ],
    "Marocain": [
        "moroccan", "morocco", "arabesque", "moorish", "islamic pattern",
        "geometric islamic", "zellige", "marrakech", "medina",
    ],
    "Mexicain": [
        "mexican", "mexico", "dia de los muertos", "day of the dead",
        "sugar skull", "fiesta", "folk mexican", "oaxacan",
    ],
    "Celtique": [
        "celtic", "celtic knot", "irish", "scottish", "welsh", "knotwork",
        "celtic pattern", "druid",
    ],
    # ── Espace & Cosmos ─────────────────────────────────────────────────────
    "Espace": [
        "space", "galaxy", "nebula", "planet", "planets", "rocket",
        "astronaut", "space pattern", "cosmic", "universe", "milky way",
    ],
    # ── Médiéval & Fantasy ──────────────────────────────────────────────────
    "Médiéval": [
        "medieval", "middle ages", "knight", "castle", "dragon",
        "medieval pattern", "heraldic", "armory", "coat of arms",
    ],
    "Fantasy": [
        "fantasy", "magical creatures", "mythical", "dragon", "unicorn",
        "elf", "dwarf", "fantasy art", "high fantasy",
    ],
    "Steampunk": [
        "steampunk", "steam punk", "victorian sci fi", "clockwork",
        "gears", "clockwork pattern", "steampunk pattern",
    ],
}

# Inverse map: synonym → canonical_name
_INVERSE_MAP: Dict[str, str] = {}
for canonical, synonyms in SYNONYM_CLUSTERS.items():
    for syn in synonyms:
        _INVERSE_MAP[syn.lower()] = canonical


def _normalize_text(text: str) -> str:
    """Lowercase, strip, collapse whitespace."""
    return re.sub(r"\s+", " ", text.lower().strip())


class ConceptMerger:
    """
    Phase 2 — Maps raw keywords/phrases to canonical niche concepts.

    Strategy:
      1. Exact match against synonym dictionary
      2. Substring match (raw contains synonym or vice-versa)
      3. Fuzzy match via difflib (threshold configurable)
    """

    def __init__(self, fuzzy_threshold: float = 0.75):
        self._threshold = fuzzy_threshold
        self._inverse = _INVERSE_MAP

    def normalize(self, raw: str) -> Optional[str]:
        """
        Map a raw keyword to its canonical niche name.

        Returns:
            Canonical niche name, or None if no match found.
        """
        key = _normalize_text(raw)
        # 1. Exact match
        if key in self._inverse:
            return self._inverse[key]
        # 2. Substring match
        for syn, canon in self._inverse.items():
            if syn in key or key in syn:
                return canon
        # 3. Fuzzy match (slower — only if no exact match)
        best_ratio = 0.0
        best_canon = None
        for syn, canon in self._inverse.items():
            ratio = difflib.SequenceMatcher(None, key, syn).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_canon = canon
        if best_ratio >= self._threshold:
            return best_canon
        return None

    def normalize_many(self, raws: List[str]) -> Dict[str, Optional[str]]:
        """Map a list of raw keywords to their canonical names."""
        return {r: self.normalize(r) for r in raws}

    def cluster_keywords(self, keywords: List[str]) -> Dict[str, List[str]]:
        """
        Group a list of keywords by their canonical niche.

        Returns:
            {canonical_name: [raw_keywords_that_map_to_it], ...}
            Keywords with no match are stored under "__unknown__".
        """
        clusters: Dict[str, List[str]] = {}
        for kw in keywords:
            canon = self.normalize(kw)
            bucket = canon if canon else "__unknown__"
            clusters.setdefault(bucket, []).append(kw)
        return clusters

    def deduplicate(self, keywords: List[str]) -> List[str]:
        """
        Remove near-duplicates from a keyword list by normalizing all to
        canonical names and returning one representative per canonical niche.
        """
        seen_canons: Set[str] = set()
        result: List[str] = []
        for kw in keywords:
            canon = self.normalize(kw) or kw
            if canon not in seen_canons:
                seen_canons.add(canon)
                result.append(kw)
        return result

    def find_synonyms(self, canonical: str) -> List[str]:
        """Return all synonyms for a canonical niche name."""
        return SYNONYM_CLUSTERS.get(canonical, [])

    def all_canonical_niches(self) -> List[str]:
        """Return the full list of canonical niche names."""
        return list(SYNONYM_CLUSTERS.keys())

    def get_best_search_terms(self, canonical: str, top_n: int = 5) -> List[str]:
        """
        Return the top N search terms for a canonical niche —
        useful for feeding into scrapers.
        """
        synonyms = SYNONYM_CLUSTERS.get(canonical, [canonical])
        # Prefer shorter, more generic terms first
        sorted_syns = sorted(synonyms, key=lambda s: (len(s.split()), len(s)))
        return sorted_syns[:top_n]
