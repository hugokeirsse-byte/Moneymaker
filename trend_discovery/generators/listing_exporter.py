"""
Listing Exporter — génère les fiches produit prêtes-à-publier par plateforme.

Pour chaque CdC (cahier des charges), produit :
  - Un nom de motif optimisé SEO par plateforme
  - Une description adaptée au tone of voice de chaque marketplace
  - Les tags/mots-clés (jusqu'à la limite de la plateforme)
  - La catégorie recommandée
  - Le type de repeat (seamless tile)
  - Un prix suggéré

Usage:
    exporter = ListingExporter()
    exporter.export_all("reports/cahiers_des_charges_20260605_1130.json", "output/listings")
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional


# ── Config plateformes ──────────────────────────────────────────────────────

PLATFORMS: Dict[str, Dict] = {
    "spoonflower": {
        "label": "Spoonflower",
        "max_tags": 20,
        "max_title_chars": 100,
        "max_desc_chars": 2000,
        "categories": ["Floral & Botanical", "Geometric", "Animals & Insects", "Food & Drink",
                        "Abstract & Painterly", "Vintage & Retro", "Holiday & Seasonal",
                        "Nature & Outdoors", "Folk & Traditional", "Art Nouveau"],
        "tone": "descriptive_craft",
        "price_note": "Spoonflower fixe le prix — royalty 10–15%",
    },
    "redbubble": {
        "label": "Redbubble",
        "max_tags": 15,
        "max_title_chars": 60,
        "max_desc_chars": 500,
        "categories": ["Pattern", "Nature", "Vintage", "Illustration", "Botanical"],
        "tone": "short_punchy",
        "price_note": "Markup libre, défaut 20% recommandé",
    },
    "zazzle": {
        "label": "Zazzle",
        "max_tags": 10,
        "max_title_chars": 160,
        "max_desc_chars": 1000,
        "categories": ["Floral", "Pattern", "Vintage", "Nature", "Abstract"],
        "tone": "descriptive_craft",
        "price_note": "Royalty libre, recommandé 15–20%",
    },
    "society6": {
        "label": "Society6",
        "max_tags": 15,
        "max_title_chars": 60,
        "max_desc_chars": 300,
        "categories": ["Floral & Botanical", "Abstract", "Geometric", "Vintage", "Nature"],
        "tone": "artistic_premium",
        "price_note": "Commission 10% fixe",
    },
    "creative_market": {
        "label": "Creative Market",
        "max_tags": 10,
        "max_title_chars": 100,
        "max_desc_chars": 1500,
        "categories": ["Patterns", "Illustrations", "Textures", "Backgrounds"],
        "tone": "technical_designer",
        "price_note": "Prix libre — recommandé 8–20$ par tile, 70% pour toi",
    },
    "fine_art_america": {
        "label": "Fine Art America / Pixels",
        "max_tags": 15,
        "max_title_chars": 75,
        "max_desc_chars": 1000,
        "categories": ["Floral", "Pattern", "Abstract", "Nature", "Vintage"],
        "tone": "descriptive_craft",
        "price_note": "Markup libre au-dessus du base price",
    },
}


def _truncate(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[:limit - 3] + "..."


def _build_tags(brief: dict, platform: str, max_tags: int) -> List[str]:
    """Assemble les tags depuis seo_keywords + visuels du CdC."""
    tags = []
    # 1. SEO keywords du CdC (déjà filtrés par Gemini)
    seo = brief.get("seo_keywords", [])
    tags.extend(seo)
    # 2. Sub-niches
    for sub in brief.get("sub_niches", []):
        if isinstance(sub, dict):
            tags.append(sub.get("name", ""))
        elif isinstance(sub, str):
            tags.append(sub)
    # 3. Visual keywords from key_elements
    ai = brief.get("ai_generation", {})
    for el in ai.get("key_elements", []):
        if isinstance(el, str) and len(el) < 30:
            tags.append(el)
    # 4. Platform-specific additions
    if platform in ("spoonflower", "zazzle"):
        tags += ["seamless pattern", "repeat pattern", "fabric pattern", "wallpaper pattern"]
    elif platform == "redbubble":
        tags += ["pattern", "seamless", "repeat"]
    elif platform == "society6":
        tags += ["pattern", "surface design"]
    elif platform == "creative_market":
        tags += ["seamless tile", "surface pattern", "textile design", "PNG 300dpi"]
    # Deduplicate + clean
    seen = set()
    clean = []
    for t in tags:
        t = t.strip().lower()
        if t and t not in seen and len(t) > 2:
            seen.add(t)
            clean.append(t)
    return clean[:max_tags]


def _build_title(brief: dict, platform: str, max_chars: int) -> str:
    """Construit un titre SEO adapté à chaque plateforme."""
    name = brief.get("name", "Seamless Pattern")
    seeds = brief.get("title_seeds", [])

    if platform == "spoonflower":
        title = f"{name} Seamless Pattern — Fabric & Wallpaper"
    elif platform == "redbubble":
        title = f"{name} Pattern"
    elif platform == "zazzle":
        title = f"{name} Seamless Repeat Pattern Design"
    elif platform == "society6":
        title = name
    elif platform == "creative_market":
        title = f"{name} — Seamless Surface Pattern (PNG 4500×4500 300 DPI)"
    elif platform == "fine_art_america":
        title = f"{name} Seamless Pattern"
    else:
        title = seeds[0] if seeds else f"{name} Pattern"

    return _truncate(title, max_chars)


def _build_description(brief: dict, platform: str, max_chars: int) -> str:
    """Construit une description adaptée au tone of voice de la plateforme."""
    name = brief.get("name", "")
    market_opp = brief.get("market_opportunity", "")
    why = brief.get("why_trending", "")
    audience = brief.get("target_audience", "")
    _vd = brief.get("visual_direction", "")
    if isinstance(_vd, dict):
        visual_dir = _vd.get("mood", "") or " ".join(str(v) for v in _vd.values() if v)
    else:
        visual_dir = str(_vd) if _vd else ""
    spoon = brief.get("spoonflower", {})
    repeat_type = spoon.get("repeat_type", "seamless half-drop")
    color_palette = spoon.get("color_palette", "")
    ai = brief.get("ai_generation", {})
    elements = ai.get("key_elements", [])

    if platform in ("spoonflower", "zazzle", "fine_art_america"):
        desc = (
            f"{name} — seamless {repeat_type} pattern.\n\n"
            f"{visual_dir}\n\n"
            f"Palette : {color_palette}\n"
            f"Key elements : {', '.join(str(e) for e in elements[:6])}\n\n"
            f"Perfect for fabric, wallpaper, home décor. Designed for {audience}."
        )
    elif platform == "redbubble":
        desc = f"{name} pattern. {visual_dir[:150] if visual_dir else ''} Great for home décor & fashion."
    elif platform == "society6":
        desc = f"{visual_dir[:200] if visual_dir else name + ' seamless pattern.'}"
    elif platform == "creative_market":
        desc = (
            f"**{name}** — seamless surface pattern tile.\n\n"
            f"**What you get:**\n"
            f"- 1× PNG tile, 4500×4500 px, 300 DPI, sRGB\n"
            f"- Seamless {repeat_type} (tiling-ready)\n"
            f"- Commercial license (see terms)\n\n"
            f"**Design:** {visual_dir}\n\n"
            f"**Palette:** {color_palette}\n\n"
            f"**Trending because:** {why[:300] if why else ''}"
        )
    else:
        desc = visual_dir or f"{name} seamless pattern."

    return _truncate(desc, max_chars)


def build_listing(brief: dict, platform: str) -> dict:
    """Construit la fiche complète pour un CdC × une plateforme."""
    cfg = PLATFORMS[platform]
    spoon = brief.get("spoonflower", {})
    ai = brief.get("ai_generation", {})

    listing = {
        "platform": cfg["label"],
        "niche_name": brief.get("name", ""),
        "title": _build_title(brief, platform, cfg["max_title_chars"]),
        "description": _build_description(brief, platform, cfg["max_desc_chars"]),
        "tags": _build_tags(brief, platform, cfg["max_tags"]),
        "category": spoon.get("category", cfg["categories"][0]),
        "repeat_type": spoon.get("repeat_type", "half-drop"),
        "color_palette": spoon.get("color_palette", ""),
        "colorways": [f"earth_tones", "navy_mono", "pastel_soft"],
        "price_note": cfg["price_note"],
        "trending_score": brief.get("trending_score", 0),
        "opportunity_score": brief.get("opportunity_score", 0),
    }

    # Filename pattern
    slug = brief.get("name", "").lower().replace(" ", "_").replace("&", "and")
    slug = "".join(c if c.isalnum() or c == "_" else "" for c in slug)
    listing["expected_filename"] = f"{slug}___base_*.png"
    listing["colorway_filenames"] = [
        f"{slug}___base_*__{pal}.png"
        for pal in listing["colorways"]
    ]

    return listing


class ListingExporter:
    """Exporte les fiches produit pour tous les CdCs × toutes les plateformes."""

    def __init__(self, platforms: Optional[List[str]] = None):
        self.platforms = platforms or list(PLATFORMS.keys())

    def export_all(
        self,
        cdc_path: str,
        output_dir: str = "./output/listings",
    ) -> str:
        """
        Génère output/listings/listings_<date>.json avec toutes les fiches.

        Returns:
            Chemin du fichier généré.
        """
        os.makedirs(output_dir, exist_ok=True)

        with open(cdc_path, encoding="utf-8") as fh:
            data = json.load(fh)

        briefs = data.get("briefs", data.get("cahiers_des_charges", []))
        ts = data.get("generated_at", "")[:10].replace("-", "")

        all_listings = []
        for brief in briefs:
            for platform in self.platforms:
                listing = build_listing(brief, platform)
                all_listings.append(listing)

        # Save full JSON
        out_json = os.path.join(output_dir, f"listings_{ts}.json")
        with open(out_json, "w", encoding="utf-8") as fh:
            json.dump({"generated_from": cdc_path, "total": len(all_listings), "listings": all_listings}, fh, indent=2, ensure_ascii=False)

        # Save per-platform CSV-like markdown for easy copy-paste
        self._export_markdown(all_listings, output_dir, ts)

        print(f"✅ {len(all_listings)} fiches générées → {out_json}")
        return out_json

    def _export_markdown(self, listings: list, output_dir: str, ts: str) -> None:
        """Markdown par plateforme — une fiche par motif, format copier-coller."""
        by_platform: Dict[str, list] = {}
        for l in listings:
            by_platform.setdefault(l["platform"], []).append(l)

        lines = ["# Fiches Produits — Prêtes à Publier\n\n"]
        lines.append(f"*Généré le {ts[:4]}-{ts[4:6]}-{ts[6:]} | {len(listings)} fiches totales*\n\n")
        lines.append("---\n\n")

        for plat, items in by_platform.items():
            lines.append(f"## {plat}\n\n")
            for item in items:
                lines.append(f"### {item['niche_name']}\n\n")
                lines.append(f"**Titre :** `{item['title']}`\n\n")
                lines.append(f"**Catégorie :** {item['category']}\n\n")
                lines.append(f"**Tags :** `{', '.join(item['tags'])}`\n\n")
                lines.append(f"**Description :**\n\n```\n{item['description']}\n```\n\n")
                lines.append(f"**Fichier attendu :** `{item['expected_filename']}`\n\n")
                lines.append(f"**Variantes couleur :** {', '.join(item['colorway_filenames'])}\n\n")
                lines.append(f"**Prix :** {item['price_note']}\n\n")
                lines.append("---\n\n")

        out_md = os.path.join(output_dir, f"listings_{ts}.md")
        with open(out_md, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
        print(f"✅ Markdown → {out_md}")
