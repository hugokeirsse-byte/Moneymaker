"""
Thumbnail Generator — miniatures navigables dans GitHub.

Génère deux types d'artefacts :
  1. Vignettes individuelles (600×600 JPEG, ~50-100 KB chacune) → git-safe
  2. Planche-contact (contact sheet) — toutes les images en une seule image

Usage :
    gen = ThumbnailGenerator()
    gen.generate_dir("output/spoonflower", "output/thumbnails/pipeline")
    gen.generate_dir("output/colorways",   "output/thumbnails/colorways")
    gen.make_contact_sheet("output/spoonflower", "output/thumbnails", cols=4)
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import List, Optional, Tuple

logger = logging.getLogger(__name__)

THUMB_SIZE = 600       # pixels, carré
CONTACT_THUMB = 300    # taille de chaque vignette dans la planche
JPEG_QUALITY = 85


class ThumbnailGenerator:
    """Génère des vignettes JPEG navigables depuis GitHub."""

    def __init__(self, thumb_size: int = THUMB_SIZE, jpeg_quality: int = JPEG_QUALITY):
        self.thumb_size = thumb_size
        self.jpeg_quality = jpeg_quality

    def generate_dir(
        self,
        input_dir: str,
        output_dir: str,
        glob_pattern: str = "*.png",
        overwrite: bool = False,
    ) -> List[str]:
        """
        Génère une vignette JPEG par PNG dans input_dir.
        Returns: liste des chemins générés.
        """
        import glob as _glob
        from PIL import Image

        files = sorted(_glob.glob(os.path.join(input_dir, glob_pattern)))
        if not files:
            logger.info("[thumbnails] aucun PNG dans %s", input_dir)
            return []

        os.makedirs(output_dir, exist_ok=True)
        generated = []

        for fp in files:
            fname = Path(fp).stem + ".jpg"
            out_path = os.path.join(output_dir, fname)

            if os.path.exists(out_path) and not overwrite:
                generated.append(out_path)
                continue

            try:
                img = Image.open(fp).convert("RGB")
                img.thumbnail((self.thumb_size, self.thumb_size), Image.LANCZOS)
                img.save(out_path, format="JPEG", quality=self.jpeg_quality, optimize=True)
                size_kb = os.path.getsize(out_path) / 1024
                logger.info("[thumbnails] %s → %.0f KB", fname, size_kb)
                generated.append(out_path)
            except Exception as exc:
                logger.warning("[thumbnails] erreur %s: %s", fp, exc)

        logger.info("[thumbnails] %d/%d vignettes → %s", len(generated), len(files), output_dir)
        return generated

    def make_contact_sheet(
        self,
        input_dir: str,
        output_path: str,
        glob_pattern: str = "*.png",
        cols: int = 4,
        thumb_size: int = CONTACT_THUMB,
        label: Optional[str] = None,
    ) -> Optional[str]:
        """
        Génère une planche-contact JPG de toutes les images.
        output_path : chemin complet du fichier de sortie (.jpg).
        Returns: chemin du fichier, ou None si échec.
        """
        import glob as _glob
        import textwrap
        from PIL import Image, ImageDraw, ImageFont

        files = sorted(_glob.glob(os.path.join(input_dir, glob_pattern)))
        # Exclure les déjà-fixés pour éviter le doublon
        files = [f for f in files if "__seamless" not in os.path.basename(f)]
        if not files:
            return None

        rows = (len(files) + cols - 1) // cols
        label_h = 20  # pixels réservés pour le nom sous chaque vignette
        pad = 4

        sheet_w = cols * (thumb_size + pad) + pad
        sheet_h = rows * (thumb_size + label_h + pad) + pad + (30 if label else 0)

        sheet = Image.new("RGB", (sheet_w, sheet_h), color=(40, 40, 40))
        draw = ImageDraw.Draw(sheet)

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 11)
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 14)
        except Exception:
            font = font_title = ImageFont.load_default()

        if label:
            draw.text((pad + 2, 4), label, fill=(220, 220, 220), font=font_title)
            y_off = 30
        else:
            y_off = 0

        for idx, fp in enumerate(files):
            row = idx // cols
            col = idx % cols
            x = pad + col * (thumb_size + pad)
            y = y_off + pad + row * (thumb_size + label_h + pad)

            try:
                img = Image.open(fp).convert("RGB")
                img.thumbnail((thumb_size, thumb_size), Image.LANCZOS)
                # Centre dans la cellule
                off_x = (thumb_size - img.width) // 2
                off_y = (thumb_size - img.height) // 2
                sheet.paste(img, (x + off_x, y + off_y))
            except Exception:
                pass

            # Label nom du fichier (tronqué)
            name = Path(fp).stem[:30]
            draw.text((x, y + thumb_size + 2), name, fill=(180, 180, 180), font=font)

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        sheet.save(output_path, format="JPEG", quality=88, optimize=True)
        size_kb = os.path.getsize(output_path) / 1024
        logger.info("[thumbnails] planche-contact → %s (%.0f KB)", output_path, size_kb)
        return output_path

    def generate_all(
        self,
        pipeline_dir: str = "output/spoonflower",
        colorways_dir: str = "output/colorways",
        uploads_dir: str = "output/uploads/base",
        uploads_colorways_dir: str = "output/uploads/colorways",
        output_root: str = "output/thumbnails",
        make_contact_sheets: bool = True,
    ) -> dict:
        """
        Génère toutes les vignettes et planches-contact en une seule commande.
        Returns: dict avec les chemins générés par catégorie.
        """
        results = {}

        # Pipeline images
        if os.path.isdir(pipeline_dir):
            thumbs = self.generate_dir(pipeline_dir, os.path.join(output_root, "pipeline"))
            results["pipeline"] = thumbs
            if make_contact_sheets and thumbs:
                cs = self.make_contact_sheet(
                    pipeline_dir,
                    os.path.join(output_root, "contact_pipeline.jpg"),
                    label="Pipeline — Images Générées",
                )
                if cs:
                    results["contact_pipeline"] = cs

        # Colorways pipeline
        if os.path.isdir(colorways_dir):
            thumbs = self.generate_dir(colorways_dir, os.path.join(output_root, "colorways"))
            results["colorways"] = thumbs
            if make_contact_sheets and thumbs:
                cs = self.make_contact_sheet(
                    colorways_dir,
                    os.path.join(output_root, "contact_colorways.jpg"),
                    label="Colorways — Variantes HSV",
                    cols=6,
                )
                if cs:
                    results["contact_colorways"] = cs

        # Uploads
        if os.path.isdir(uploads_dir):
            thumbs = self.generate_dir(uploads_dir, os.path.join(output_root, "uploads"))
            results["uploads"] = thumbs
            if make_contact_sheets and thumbs:
                cs = self.make_contact_sheet(
                    uploads_dir,
                    os.path.join(output_root, "contact_uploads.jpg"),
                    label="Uploads — Images Utilisateur",
                )
                if cs:
                    results["contact_uploads"] = cs

        # Uploads colorways
        if os.path.isdir(uploads_colorways_dir):
            thumbs = self.generate_dir(uploads_colorways_dir, os.path.join(output_root, "uploads_colorways"))
            results["uploads_colorways"] = thumbs

        total = sum(len(v) if isinstance(v, list) else 1 for v in results.values())
        logger.info("[thumbnails] total : %d fichiers → %s/", total, output_root)
        print(f"✅ Thumbnails : {total} fichiers → {output_root}/")
        return results
