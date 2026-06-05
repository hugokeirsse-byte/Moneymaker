"""
Listing Generator — fiches produit prêtes à publier, toutes plateformes.

Lit les CDCs JSON + scanne les images générées, produit :
  - reports/listings/spoonflower_upload_priority.csv   (toutes images, triées par score)
  - reports/listings/adobe_stock_keywords.csv           (50 keywords max)
  - reports/listings/etsy_bundles.csv                   (bundles par niche)
  - reports/listings/redbubble_listings.csv             (designs standalone)
  - reports/listings/all_listings.md                    (résumé human-readable)

Zéro API — pur Python, utilise les données CDC existantes.
"""
from __future__ import annotations

import csv
import glob
import json
import logging
import os
import re
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Palettes générées par le colorizer (doivent correspondre à color_rewriter.py)
KNOWN_COLORWAYS = ["cool_ocean", "earth_autumn", "midnight", "rose_gold"]

# Catégories Spoonflower → mots-clés déclencheurs dans le nom/mood du CDC
SPOONFLOWER_CATEGORY_MAP = [
    ("Floral & Botanical", ["botanical", "floral", "flower", "plant", "leaf", "fern", "rose",
                             "herb", "garden", "vine", "moss", "mushroom", "fungi"]),
    ("Animals & Insects", ["animal", "bird", "frog", "fox", "cat", "dog", "insect", "bee",
                            "butterfly", "fish", "moth", "heron", "crane", "koi", "bat",
                            "lobster", "snail", "raccoon", "duck", "egret", "stag", "octopus"]),
    ("Geometric", ["geometric", "art deco", "tessell", "tile", "grid", "chevron", "hex",
                   "diamond", "triangle", "abstract"]),
    ("Food & Drink", ["food", "drink", "wine", "bread", "sourdough", "fruit", "vegetable",
                      "cocktail", "coffee", "tea", "cake", "pizza"]),
    ("Vintage & Retro", ["vintage", "retro", "victorian", "art nouveau", "edwardian",
                          "mid-century", "antique", "apothecary", "enamelware"]),
    ("Nature & Outdoors", ["nature", "forest", "ocean", "mountain", "sky", "cloud", "stone",
                            "mineral", "crystal", "terrarium", "geological", "tidal"]),
    ("Folk & Traditional", ["folk", "nordic", "scandinavian", "toile", "william morris",
                             "block print", "chinoiserie", "japanese", "ukiyo"]),
    ("Abstract & Painterly", ["abstract", "watercolor", "painterly", "impressionist",
                               "expressionist", "ink", "wash"]),
]

ADOBE_STOCK_CATEGORY_MAP = [
    (2,  ["floral", "botanical", "flower", "plant"]),    # 2 = Backgrounds/Textures
    (2,  ["geometric", "abstract", "pattern"]),
    (19, ["vintage", "retro", "antique"]),               # 19 = Vintage
    (22, ["animal", "bird", "wildlife"]),                # 22 = Animals
    (17, ["nature", "forest", "ocean", "landscape"]),   # 17 = Nature
    (3,  ["food", "drink", "kitchen"]),                  # 3 = Food & Drink
]


def _slug(name: str) -> str:
    """Transforme un nom CDC en slug fichier (ex: 'Art Deco Koi' → 'art_deco_koi')."""
    s = name.lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


def _spoonflower_category(name: str, mood: str = "") -> str:
    text = (name + " " + mood).lower()
    for category, keywords in SPOONFLOWER_CATEGORY_MAP:
        if any(kw in text for kw in keywords):
            return category
    return "Abstract & Painterly"


def _adobe_category(name: str, mood: str = "") -> int:
    text = (name + " " + mood).lower()
    for cat_id, keywords in ADOBE_STOCK_CATEGORY_MAP:
        if any(kw in text for kw in keywords):
            return cat_id
    return 2  # default: Backgrounds/Textures


def _clean_tags(raw: List[str], extra: List[str], max_tags: int) -> List[str]:
    seen: set = set()
    result = []
    for tag in raw + extra:
        if not isinstance(tag, str):
            continue
        t = tag.strip().lower()
        t = re.sub(r"[^\w\s-]", "", t)[:50]
        if t and t not in seen and len(t) > 2:
            seen.add(t)
            result.append(t)
        if len(result) >= max_tags:
            break
    return result


def _spoonflower_tags(brief: dict) -> List[str]:
    base = list(brief.get("seo_keywords", []))
    vd = brief.get("visual_direction", {})
    mood_tags = [m.strip() for m in (vd.get("mood", "") or "").split(",") if m.strip()]
    spoon = brief.get("spoonflower", {}) or brief.get("spoonflower_fit", {})
    product_tags = [p.replace("cotton", "fabric").strip() for p in spoon.get("top_products", [])]
    extra = mood_tags + product_tags + ["seamless pattern", "repeat pattern",
                                         "surface design", "fabric pattern", "wallpaper"]
    return _clean_tags(base, extra, 20)


def _adobe_keywords(brief: dict) -> List[str]:
    base = list(brief.get("seo_keywords", []))
    vd = brief.get("visual_direction", {})
    mood_tags = [m.strip() for m in (vd.get("mood", "") or "").split(",") if m.strip()]
    # Sub-niche names
    sub_tags = []
    for sub in brief.get("sub_niches", []):
        if isinstance(sub, dict):
            sub_tags.append(sub.get("name", ""))
        elif isinstance(sub, str):
            sub_tags.append(sub)
    extra = mood_tags + sub_tags + [
        "seamless pattern", "repeat pattern", "surface design",
        "textile design", "fabric pattern", "vector background",
        "decorative pattern", "tileable", "4k resolution",
    ]
    return _clean_tags(base, extra, 50)


def _etsy_tags(brief: dict) -> List[str]:
    base = list(brief.get("seo_keywords", []))[:10]
    extra = [
        "digital download", "seamless pattern", "pattern bundle",
        "scrapbook paper", "digital paper", "printable pattern",
        "surface design", "commercial license", "instant download",
        "Cricut pattern", "Spoonflower upload",
    ]
    return _clean_tags(base, extra, 13)  # Etsy limit = 13 tags


def _spoonflower_title(brief: dict, colorway: Optional[str] = None) -> str:
    name = brief.get("name", "Pattern")
    title = f"{name} Seamless Repeat Pattern — Fabric & Wallpaper"
    if colorway and colorway != "base":
        suffix_map = {
            "cool_ocean": "Blue Ocean",
            "earth_autumn": "Earth Tones",
            "midnight": "Midnight Dark",
            "rose_gold": "Rose Gold Blush",
        }
        suffix = suffix_map.get(colorway, colorway.replace("_", " ").title())
        title = f"{name} Seamless Pattern — {suffix}"
    return title[:100]


def _adobe_title(brief: dict) -> str:
    name = brief.get("name", "Pattern")
    vd = brief.get("visual_direction", {})
    mood = (vd.get("mood", "") or "").split(",")[0].strip().title()
    if mood:
        return f"{mood} {name} Seamless Pattern Background"[:70]
    return f"{name} Seamless Repeat Pattern Surface Design"[:70]


def _etsy_title(brief: dict) -> str:
    name = brief.get("name", "Pattern")
    spoon = brief.get("spoonflower", {}) or brief.get("spoonflower_fit", {})
    products = spoon.get("top_products", [])
    prod_hint = products[0].replace("cotton", "").strip().title() if products else "Fabric"
    return f"{name} Seamless Pattern Bundle — Digital Download PNG for {prod_hint} Printing"[:140]


def _spoonflower_description(brief: dict) -> str:
    name = brief.get("name", "")
    why = (brief.get("why_trending") or brief.get("demand_evidence") or "")[:200]
    vd = brief.get("visual_direction", {})
    mood = vd.get("mood", "") if isinstance(vd, dict) else ""
    spoon = brief.get("spoonflower", {}) or brief.get("spoonflower_fit", {})
    repeat = spoon.get("repeat_type", "seamless half-drop")
    products = ", ".join(spoon.get("top_products", ["fabric", "wallpaper"])[:3])
    audience = brief.get("target_audience", "")
    seo = ", ".join(brief.get("seo_keywords", [])[:8])

    desc = f"{name} — {mood} seamless {repeat} pattern.\n\n"
    if why:
        desc += f"{why}\n\n"
    desc += f"Perfect for {products}.\n"
    if audience:
        desc += f"Designed for {audience}.\n\n"
    desc += f"Keywords: {seo}\n\n"
    desc += "File: PNG 4500×4500 px, 300 DPI, sRGB — ready to upload to Spoonflower."
    return desc[:2000]


def _adobe_description(brief: dict) -> str:
    name = brief.get("name", "")
    why = (brief.get("why_trending") or "")[:150]
    vd = brief.get("visual_direction", {})
    mood = vd.get("mood", "") if isinstance(vd, dict) else ""
    return f"{name} seamless pattern. {mood}. {why} High resolution 300 DPI tileable background for commercial use."[:1000]


def _etsy_description(brief: dict) -> str:
    name = brief.get("name", "")
    why = (brief.get("why_trending") or "")[:200]
    spoon = brief.get("spoonflower", {}) or brief.get("spoonflower_fit", {})
    products = ", ".join(spoon.get("top_products", ["fabric"])[:3])

    sub_lines = ""
    for sub in brief.get("sub_niches", [])[:3]:
        if isinstance(sub, dict):
            sub_lines += f"\n• {sub.get('name','')}: {sub.get('unique_angle', sub.get('differentiator',''))[:80]}"

    desc = f"✨ INSTANT DOWNLOAD — {name} Seamless Pattern Bundle\n\n"
    desc += f"{why}\n\n"
    desc += "📦 WHAT YOU GET:\n"
    desc += "• 5× PNG files (base + 4 coordinating colorways)\n"
    desc += "• 4500×4500 px, 300 DPI, sRGB — print-ready\n"
    desc += "• Seamless tile — testé pour répétition parfaite\n"
    desc += f"• Perfect for: {products}, wallpaper, gift wrap\n\n"
    if sub_lines:
        desc += f"🎨 VARIATIONS INCLUSES:{sub_lines}\n\n"
    desc += "✅ Commercial license included — sell your makes!\n"
    desc += "📥 Download immediately after purchase. No physical product."
    return desc[:2000]


def find_generated_images(
    spoonflower_dir: str = "./output/spoonflower",
    colorways_dir: str = "./output/colorways",
    uploads_dir: str = "./output/uploads/base",
    uploads_colorways_dir: str = "./output/uploads/colorways",
) -> List[Dict]:
    """
    Scanne les dossiers d'output et retourne la liste de toutes les images
    avec leur niche slug, colorway et chemin.
    """
    images = []

    def _scan(directory: str, source: str) -> None:
        for fp in sorted(glob.glob(os.path.join(directory, "*.png"))):
            fname = Path(fp).stem
            # Extrait le slug niche et la colorway du nom de fichier
            # Format: slug___base_YYYYMMDD_HHMM[__colorway].png
            m = re.match(r"^(.+?)___base_\d{8}_\d{4}(?:__(.+))?$", fname)
            if m:
                niche_slug = m.group(1)
                colorway = m.group(2) or "base"
            else:
                # uploads: user_upload_UUID[__colorway]
                m2 = re.match(r"^(user_upload_[a-f0-9-]+)(?:__(.+))?$", fname)
                if m2:
                    niche_slug = m2.group(1)
                    colorway = m2.group(2) or "base"
                else:
                    niche_slug = fname
                    colorway = "base"
            images.append({
                "path": fp,
                "filename": Path(fp).name,
                "niche_slug": niche_slug,
                "colorway": colorway,
                "source": source,
                "size_mb": round(os.path.getsize(fp) / 1_048_576, 1),
            })

    if os.path.isdir(spoonflower_dir):
        _scan(spoonflower_dir, "spoonflower")
    if os.path.isdir(colorways_dir):
        _scan(colorways_dir, "colorway")
    if os.path.isdir(uploads_dir):
        _scan(uploads_dir, "upload")
    if os.path.isdir(uploads_colorways_dir):
        _scan(uploads_colorways_dir, "upload_colorway")

    return images


def load_all_briefs(
    reports_dir: str = "./reports",
    redbubble_dir: str = "./reports/redbubble",
) -> Tuple[List[dict], List[dict]]:
    """
    Charge tous les CDCs Spoonflower + Redbubble depuis les rapports JSON.
    Retourne (spoonflower_briefs, redbubble_briefs).
    """
    def _load_dir(d: str) -> List[dict]:
        briefs = []
        for fp in sorted(glob.glob(os.path.join(d, "cahiers_des_charges_*.json"))):
            try:
                with open(fp, encoding="utf-8") as fh:
                    data = json.load(fh)
                raw = data.get("cahiers_des_charges") or data.get("briefs") or []
                briefs.extend(raw)
            except Exception as e:
                logger.warning("[listing] lecture %s échouée : %s", fp, e)
        return briefs

    sf = _load_dir(reports_dir)
    rb = _load_dir(redbubble_dir) if os.path.isdir(redbubble_dir) else []
    return sf, rb


def _match_brief(niche_slug: str, briefs: List[dict]) -> Optional[dict]:
    """Trouve le CDC correspondant au slug d'un fichier image."""
    # Exact slug match
    for b in briefs:
        if _slug(b.get("name", "")) == niche_slug:
            return b
    # Partial match (slug starts-with or contains)
    for b in briefs:
        bslug = _slug(b.get("name", ""))
        if niche_slug.startswith(bslug) or bslug.startswith(niche_slug):
            return b
    return None


class ListingGenerator:
    """Génère les fiches d'upload pour toutes les plateformes."""

    def __init__(
        self,
        reports_dir: str = "./reports",
        spoonflower_dir: str = "./output/spoonflower",
        colorways_dir: str = "./output/colorways",
        uploads_dir: str = "./output/uploads/base",
        uploads_colorways_dir: str = "./output/uploads/colorways",
        redbubble_dir: str = "./output/redbubble",
        redbubble_reports_dir: str = "./reports/redbubble",
        output_dir: str = "./reports/listings",
    ):
        self.reports_dir = reports_dir
        self.spoonflower_dir = spoonflower_dir
        self.colorways_dir = colorways_dir
        self.uploads_dir = uploads_dir
        self.uploads_colorways_dir = uploads_colorways_dir
        self.redbubble_dir = redbubble_dir
        self.redbubble_reports_dir = redbubble_reports_dir
        self.output_dir = output_dir

    def run(self) -> str:
        """Lance la génération complète de tous les fichiers de listing."""
        os.makedirs(self.output_dir, exist_ok=True)
        today = date.today().strftime("%Y%m%d")

        sf_briefs, rb_briefs = load_all_briefs(self.reports_dir, self.redbubble_reports_dir)
        images = find_generated_images(
            self.spoonflower_dir, self.colorways_dir,
            self.uploads_dir, self.uploads_colorways_dir,
        )

        logger.info(
            "[listing] %d briefs Spoonflower, %d briefs Redbubble, %d images",
            len(sf_briefs), len(rb_briefs), len(images),
        )

        spoonflower_rows = self._build_spoonflower_rows(images, sf_briefs)
        adobe_rows = self._build_adobe_rows(sf_briefs)
        etsy_rows = self._build_etsy_rows(sf_briefs)
        redbubble_rows = self._build_redbubble_rows(rb_briefs)

        paths = []
        paths.append(self._write_csv(
            spoonflower_rows,
            os.path.join(self.output_dir, f"spoonflower_upload_priority_{today}.csv"),
            "Spoonflower",
        ))
        paths.append(self._write_csv(
            adobe_rows,
            os.path.join(self.output_dir, f"adobe_stock_keywords_{today}.csv"),
            "Adobe Stock",
        ))
        paths.append(self._write_csv(
            etsy_rows,
            os.path.join(self.output_dir, f"etsy_bundles_{today}.csv"),
            "Etsy",
        ))
        if redbubble_rows:
            paths.append(self._write_csv(
                redbubble_rows,
                os.path.join(self.output_dir, f"redbubble_listings_{today}.csv"),
                "Redbubble",
            ))

        md_path = self._write_summary_md(
            spoonflower_rows, adobe_rows, etsy_rows, redbubble_rows,
            os.path.join(self.output_dir, f"upload_guide_{today}.md"),
        )
        paths.append(md_path)

        print(f"\n✅ Listings générés dans {self.output_dir}/")
        for p in paths:
            size = os.path.getsize(p) // 1024
            print(f"   {Path(p).name}  ({size} KB)")
        return self.output_dir

    def _build_spoonflower_rows(
        self, images: List[dict], briefs: List[dict]
    ) -> List[dict]:
        """Une ligne par image (base + colorways), triées par opportunity_score desc."""
        rows = []
        for img in images:
            if img["source"] not in ("spoonflower", "colorway"):
                continue
            brief = _match_brief(img["niche_slug"], briefs)
            name = brief["name"] if brief else img["niche_slug"].replace("_", " ").title()
            opp_score = int(brief.get("opportunity_score", brief.get("trending_score", 50))) if brief else 50
            vd = (brief or {}).get("visual_direction", {})
            mood = vd.get("mood", "") if isinstance(vd, dict) else ""
            spoon = (brief or {}).get("spoonflower", {}) or (brief or {}).get("spoonflower_fit", {})
            tags = _spoonflower_tags(brief) if brief else ["seamless pattern", "repeat"]
            rows.append({
                "priority": opp_score,
                "filename": img["filename"],
                "colorway": img["colorway"],
                "design_title": _spoonflower_title({"name": name}, img["colorway"]),
                "category": _spoonflower_category(name, mood),
                "tags": ", ".join(tags),
                "repeat_type": spoon.get("repeat_type", "half-drop"),
                "description": _spoonflower_description(brief) if brief else f"{name} seamless pattern.",
                "niche": name,
                "opportunity_score": opp_score,
                "size_mb": img["size_mb"],
                "path": img["path"],
            })
        # Sort: base images first by score, then colorways
        rows.sort(key=lambda r: (-r["priority"], r["colorway"] != "base", r["colorway"]))
        return rows

    def _build_adobe_rows(self, briefs: List[dict]) -> List[dict]:
        """Une ligne par niche CDC (pas par image — Adobe Stock = upload unique)."""
        rows = []
        for brief in sorted(briefs, key=lambda b: -int(b.get("opportunity_score", b.get("trending_score", 0)))):
            name = brief.get("name", "")
            vd = brief.get("visual_direction", {})
            mood = vd.get("mood", "") if isinstance(vd, dict) else ""
            keywords = _adobe_keywords(brief)
            rows.append({
                "filename_pattern": f"{_slug(name)}___base_*.png",
                "title": _adobe_title(brief),
                "keywords": ", ".join(keywords),
                "keyword_count": len(keywords),
                "category": _adobe_category(name, mood),
                "description": _adobe_description(brief),
                "niche": name,
                "opportunity_score": brief.get("opportunity_score", brief.get("trending_score", 50)),
            })
        return rows

    def _build_etsy_rows(self, briefs: List[dict]) -> List[dict]:
        """Une ligne par niche = 1 bundle digital download (base + 4 colorways)."""
        rows = []
        for brief in sorted(briefs, key=lambda b: -int(b.get("opportunity_score", b.get("trending_score", 0)))):
            name = brief.get("name", "")
            slug = _slug(name)
            # Cherche les fichiers réels pour ce bundle
            base_files = glob.glob(os.path.join(self.spoonflower_dir, f"{slug}___base_*.png"))
            cw_files = [
                glob.glob(os.path.join(self.colorways_dir, f"{slug}___base_*__{cw}.png"))
                for cw in KNOWN_COLORWAYS
            ]
            total_files = len(base_files) + sum(len(f) for f in cw_files)
            tags = _etsy_tags(brief)
            rows.append({
                "listing_title": _etsy_title(brief),
                "tags": ", ".join(tags),
                "description": _etsy_description(brief)[:500],  # truncated for CSV
                "files_in_bundle": total_files,
                "base_image": Path(base_files[0]).name if base_files else f"{slug}___base_*.png",
                "price_suggestion_usd": "4.99" if total_files >= 5 else "2.99",
                "niche": name,
                "opportunity_score": brief.get("opportunity_score", brief.get("trending_score", 50)),
            })
        return rows

    def _build_redbubble_rows(self, briefs: List[dict]) -> List[dict]:
        """Une ligne par CDC Redbubble."""
        rows = []
        for brief in briefs:
            name = brief.get("name", "")
            slug = _slug(name)
            rb_files = glob.glob(os.path.join(self.redbubble_dir, f"{slug}*.png"))
            vd = brief.get("visual_direction", {})
            style = vd.get("style", "") if isinstance(vd, dict) else ""
            community = brief.get("niche_community", "")
            humor = brief.get("humor_level", "")
            tags_base = list(brief.get("seo_keywords", [])) if "seo_keywords" in brief else []
            if community:
                tags_base.append(community)
            if humor:
                tags_base.append(humor)
            tags_base += ["illustration", "sticker", "gift", "funny", "cute"]
            tags = _clean_tags(tags_base, [], 15)
            best_products = brief.get("best_products", ["sticker", "t-shirt"])
            rows.append({
                "filename_pattern": f"{slug}*.png",
                "image_found": "yes" if rb_files else "no",
                "title": name[:60],
                "tags": ", ".join(tags),
                "description": brief.get("concept", "")[:300],
                "best_products": ", ".join(best_products[:3]) if isinstance(best_products, list) else str(best_products),
                "community": community,
                "humor_level": humor,
                "style": style,
                "trending_score": brief.get("trending_score", 50),
            })
        return rows

    def _write_csv(self, rows: List[dict], path: str, label: str) -> str:
        if not rows:
            logger.warning("[listing] %s — aucune ligne", label)
            return path
        with open(path, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)
        logger.info("[listing] %s → %s (%d lignes)", label, path, len(rows))
        return path

    def _write_summary_md(
        self,
        sf_rows: List[dict],
        adobe_rows: List[dict],
        etsy_rows: List[dict],
        rb_rows: List[dict],
        path: str,
    ) -> str:
        today = date.today().isoformat()
        base_sf = [r for r in sf_rows if r["colorway"] == "base"]
        cw_sf = [r for r in sf_rows if r["colorway"] != "base"]

        lines = [
            f"# Guide d'Upload — {today}\n\n",
            f"**{len(base_sf)} designs base** + **{len(cw_sf)} colorways** Spoonflower  \n",
            f"**{len(adobe_rows)} designs** pour Adobe Stock  \n",
            f"**{len(etsy_rows)} bundles** pour Etsy Digital Downloads  \n",
            f"**{len(rb_rows)} designs** pour Redbubble  \n\n",
            "---\n\n",
        ]

        # Spoonflower top 10 priority
        if base_sf:
            lines.append("## 🏆 Spoonflower — Top 10 à uploader en premier\n\n")
            lines.append("| # | Design | Score | Colorways dispo | Catégorie |\n")
            lines.append("|---|--------|-------|-----------------|----------|\n")
            for i, row in enumerate(base_sf[:10], 1):
                slug = _slug(row["niche"])
                cw_count = sum(1 for r in cw_sf if _slug(r["niche"]) == slug)
                lines.append(
                    f"| {i} | **{row['niche']}** | {row['opportunity_score']} "
                    f"| {cw_count} colorways | {row['category']} |\n"
                )
            lines.append("\n")

        # Adobe Stock top 10
        if adobe_rows:
            lines.append("## 📸 Adobe Stock — Top 10 à uploader\n\n")
            lines.append("| # | Design | Catégorie | Mots-clés |\n")
            lines.append("|---|--------|-----------|----------|\n")
            for i, row in enumerate(adobe_rows[:10], 1):
                kw_preview = ", ".join(row["keywords"].split(", ")[:5])
                lines.append(
                    f"| {i} | **{row['niche']}** | {row['category']} | {kw_preview}… |\n"
                )
            lines.append("\n")

        # Etsy bundles top 10
        if etsy_rows:
            lines.append("## 🛍️ Etsy — Bundles à créer\n\n")
            lines.append("| # | Bundle | Fichiers | Prix suggéré |\n")
            lines.append("|---|--------|----------|-------------|\n")
            for i, row in enumerate(etsy_rows[:10], 1):
                lines.append(
                    f"| {i} | **{row['niche']}** | {row['files_in_bundle']} PNG | ${row['price_suggestion_usd']} |\n"
                )
            lines.append("\n")

        # Redbubble
        if rb_rows:
            found = sum(1 for r in rb_rows if r["image_found"] == "yes")
            lines.append(f"## 🔴 Redbubble — {found}/{len(rb_rows)} images prêtes\n\n")
            lines.append("| Design | Image | Produits | Communauté |\n")
            lines.append("|--------|-------|----------|------------|\n")
            for row in rb_rows:
                status = "✅" if row["image_found"] == "yes" else "⏳"
                lines.append(
                    f"| **{row['title'][:40]}** | {status} | {row['best_products'][:30]} | {row['community'][:25]} |\n"
                )
            lines.append("\n")

        with open(path, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
        logger.info("[listing] guide → %s", path)
        return path
