"""
Packager Spoonflower — normalise les images pour l'upload.

Spécifications officielles Spoonflower :
- Format : PNG
- Résolution : 300 DPI (recommandé), 150 DPI minimum
- Taille : minimum 200×200 px (mais ≥ 4500×4500 pour qualité professionnelle)
- Répétition : le motif doit tuiler parfaitement (seamless)
- Espace colorimétrique : sRGB
- Taille fichier : max 40 MB

On vise : PNG 300 DPI, ≥ 4500×4500 px, sRGB.
"""
from __future__ import annotations

import io
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

# Spécifications cibles Spoonflower
SPOONFLOWER_DPI = (300, 300)
SPOONFLOWER_MIN_SIZE = (4500, 4500)  # 15" × 15" à 300 DPI


class SpoonflowerPackager:
    """
    Prend des bytes d'image (PNG/JPEG) et produit un fichier
    PNG 300 DPI prêt à uploader sur Spoonflower.

    Requiert Pillow : pip install Pillow
    """

    def __init__(self, output_dir: str = "./output/spoonflower"):
        self._output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _get_pil(self):
        try:
            from PIL import Image
            return Image
        except ImportError:
            logger.error("Pillow non installé. Exécute: pip install Pillow")
            return None

    def _safe_filename(self, niche_name: str) -> str:
        """Convertit un nom de niche en nom de fichier sûr."""
        safe = "".join(c if c.isalnum() or c in (" ", "-", "_") else "_" for c in niche_name)
        safe = safe.strip().replace(" ", "_").lower()[:60]
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M")
        return f"{safe}_{timestamp}.png"

    def package(
        self,
        image_bytes: bytes,
        niche_name: str,
        ensure_min_size: bool = True,
    ) -> Optional[str]:
        """
        Transforme des bytes d'image en fichier PNG Spoonflower-ready.

        Args:
            image_bytes: contenu binaire de l'image (PNG ou JPEG)
            niche_name: nom de la niche (pour le nom de fichier)
            ensure_min_size: si True, upscale avec Pillow si < SPOONFLOWER_MIN_SIZE

        Returns:
            Chemin absolu vers le fichier PNG sauvegardé, ou None en cas d'erreur.
        """
        Image = self._get_pil()
        if not Image:
            return None

        try:
            img = Image.open(io.BytesIO(image_bytes))

            # Conversion en RGB (supprime canal alpha si présent — Spoonflower l'exige)
            if img.mode in ("RGBA", "LA"):
                # Fond blanc pour les motifs avec transparence
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, mask=img.split()[-1] if img.mode == "RGBA" else None)
                img = background
            elif img.mode != "RGB":
                img = img.convert("RGB")

            # Upscale si trop petite (dernier recours : Pillow Lanczos)
            w, h = img.size
            min_w, min_h = SPOONFLOWER_MIN_SIZE
            if ensure_min_size and (w < min_w or h < min_h):
                scale = max(min_w / w, min_h / h)
                new_w = int(w * scale)
                new_h = int(h * scale)
                logger.info(
                    "[packager] upscale Pillow %dx%d → %dx%d (Runware upscale insuffisant)",
                    w, h, new_w, new_h,
                )
                img = img.resize((new_w, new_h), Image.LANCZOS)

            # Sauvegarde PNG avec métadonnées DPI 300
            filename = self._safe_filename(niche_name)
            filepath = os.path.join(self._output_dir, filename)

            # PNG avec pHYs chunk = 300 DPI (300 / 0.0254 ≈ 11811 px/m)
            img.save(filepath, format="PNG", dpi=SPOONFLOWER_DPI, optimize=False)

            file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
            logger.info(
                "[packager] ✅ %s | %dx%d | 300 DPI | %.1f MB",
                filename, img.width, img.height, file_size_mb,
            )

            if file_size_mb > 40:
                logger.warning(
                    "[packager] ⚠️  Fichier %.1f MB > 40 MB limite Spoonflower!", file_size_mb
                )

            return filepath

        except Exception as exc:
            logger.error("[packager] erreur pour '%s': %s", niche_name, exc)
            return None

    def verify(self, filepath: str) -> Tuple[bool, str]:
        """
        Vérifie qu'un fichier est conforme aux specs Spoonflower.

        Returns:
            (ok, message)
        """
        Image = self._get_pil()
        if not Image:
            return False, "Pillow non disponible"

        try:
            img = Image.open(filepath)
            w, h = img.size
            file_mb = os.path.getsize(filepath) / (1024 * 1024)

            issues = []
            if img.mode not in ("RGB", "RGBA"):
                issues.append(f"mode {img.mode} (attendu RGB)")
            if w < SPOONFLOWER_MIN_SIZE[0] or h < SPOONFLOWER_MIN_SIZE[1]:
                issues.append(f"taille {w}×{h} < {SPOONFLOWER_MIN_SIZE[0]}×{SPOONFLOWER_MIN_SIZE[1]}")
            if file_mb > 40:
                issues.append(f"fichier {file_mb:.1f} MB > 40 MB")

            if issues:
                return False, "Problèmes: " + "; ".join(issues)
            return True, f"✅ OK — {w}×{h} px, {file_mb:.1f} MB, mode {img.mode}"

        except Exception as exc:
            return False, f"Erreur lecture: {exc}"
