"""
Centralized configuration for the trend discovery system.
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Seed keywords for POD market ---
KEYWORDS_SEED = [
    "seamless pattern",
    "fabric design",
    "surface design",
    "wallpaper design",
    "gift wrap pattern",
    "repeat pattern",
    "textile design",
    "print design",
    "pattern design",
    "spoonflower design",
    "redbubble art",
    "sticker design",
    "phone case design",
    "tote bag design",
    "leggings pattern",
]

# --- Niche categories with sub-niches ---
NICHE_CATEGORIES = {
    "nature": [
        "botanical",
        "floral",
        "forest",
        "ocean",
        "mountain",
        "tropical",
        "desert",
        "garden",
    ],
    "animals": [
        "cats",
        "dogs",
        "birds",
        "foxes",
        "deer",
        "bees",
        "butterflies",
        "horses",
    ],
    "aesthetic_styles": [
        "cottagecore",
        "dark academia",
        "goblincore",
        "fairycore",
        "solarpunk",
        "cyberpunk",
        "japandi",
        "boho",
    ],
    "patterns": [
        "geometric",
        "abstract",
        "watercolor",
        "minimalist",
        "maximalist",
        "retro",
        "vintage",
        "art nouveau",
    ],
    "seasonal": [
        "christmas",
        "halloween",
        "easter",
        "valentines",
        "thanksgiving",
        "summer",
        "winter",
        "spring",
    ],
    "cultural": [
        "japanese",
        "scandinavian",
        "moroccan",
        "mexican",
        "indian",
        "celtic",
        "african",
    ],
    "themes": [
        "space",
        "mushrooms",
        "crystals",
        "tarot",
        "astrology",
        "cottagecore",
        "witchy",
        "celestial",
    ],
}

# --- Platforms ---
PLATFORMS = {
    "spoonflower": "https://www.spoonflower.com",
    "redbubble": "https://www.redbubble.com",
}

# --- Reddit subreddits to monitor ---
REDDIT_SUBREDDITS = [
    "surfacedesign",
    "patterndesign",
    "fabricdesign",
    "Spoonflower",
    "redbubble",
    "artstore",
    "passiveincome",
    "Etsy",
    "printondemand",
    "artbusiness",
]

# --- Scoring weights (must sum to 1.0) ---
SCORING_WEIGHTS = {
    "google_trend": 0.30,
    "reddit_buzz": 0.20,
    "competition": 0.20,
    "feasibility": 0.15,
    "seasonality": 0.15,
}

# --- Output directory ---
OUTPUT_DIR = "./reports"

# --- Database directory ---
DATA_DIR = "./data"
DB_PATH = "./data/opportunities.db"

# --- Rate limiting delays (seconds) ---
SCRAPER_DELAYS = {
    "google_trends":    {"min": 2, "max": 5},
    "google_autocomplete": {"min": 1, "max": 3},
    "reddit":           {"min": 1, "max": 2},
    "spoonflower":      {"min": 3, "max": 7},
    "redbubble":        {"min": 3, "max": 7},
    "etsy":             {"min": 4, "max": 8},
    "pinterest":        {"min": 3, "max": 7},
    "tiktok":           {"min": 2, "max": 5},
    "amazon":           {"min": 3, "max": 6},
    "society6":         {"min": 4, "max": 8},
    "deviantart":       {"min": 3, "max": 6},
    "creative_market":  {"min": 4, "max": 8},
    "bing":             {"min": 1, "max": 3},
    "youtube":          {"min": 1, "max": 3},
}

# --- Optional API credentials (from environment) ---
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID", "")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET", "")
REDDIT_USER_AGENT = os.getenv("REDDIT_USER_AGENT", "TrendDiscovery/1.0 by trend_bot")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# --- HTTP headers ---
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}
