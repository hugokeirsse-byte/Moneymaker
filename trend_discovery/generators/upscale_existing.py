"""
Upscale IA des images existantes via Runware Real-ESRGAN.

Problème résolu : les images pipeline ont été générées à 1024×1024 puis
étirées avec Pillow LANCZOS → résultat flou et non publiable sur Spoonflower.

Solution : downscale 4500→1024 propre, upscale IA ×4 → 4096, pad → 4500.
Le résultat IA est nettement plus net que l'upscale LANCZOS direct.

Usage :
    python -m trend_discovery.generators.upscale_existing
    python -m trend_discovery.generators.upscale_existing --input output/spoonflower --limit 5
"""
from __future__ import annotations

import argparse
import base64
import io
import logging
import os
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

TARGET_SIZE = 4500
DOWNSCALE_TO = 1024  # résolution de travail pour l'upscale IA


def _image_to_base64_url(image_bytes: bytes) -> str:
    b64 = base64.b64encode(image_bytes).decode()
    return f"data:image/png;base64,{b64}"


def fix_image(
    src_path: str,
    runware,
    output_dir: Optional[str] = None,
    overwrite: bool = True,
) -> Optional[str]:
    """
    Prend une image blurry (4500×4500 LANCZOS), la downscale à 1024,
    la passe dans Runware AI upscale ×4 → 4096, redimensionne à 4500.

    Returns: chemin de l'image corrigée, ou None si échec.
    """
    from PIL import Image as PILImage

    out_dir = output_dir or os.path.dirname(src_path)
    fname = os.path.basename(src_path)
    out_path = os.path.join(out_dir, fname) if overwrite else os.path.join(out_dir, Path(src_path).stem + "__sharp.png")

    try:
        # 1. Ouvrir et downscaler à 1024×1024 (retrouve l'info de la génération originale)
        img = PILImage.open(src_path).convert("RGB")
        small = img.resize((DOWNSCALE_TO, DOWNSCALE_TO), PILImage.LANCZOS)

        buf = io.BytesIO()
        small.save(buf, format="PNG")
        small_bytes = buf.getvalue()

        # 2. Encoder en base64 et passer par imageInference (seedImage) pour obtenir
        #    une URL Runware CDN — imageUpscale n'accepte pas les data: URLs directement.
        b64_url = _image_to_base64_url(small_bytes)
        # imageUpscale n'accepte que des URLs CDN Runware, pas du base64.
        # On passe l'image par imageInference (img2img minimal) pour obtenir l'URL.
        relay_url = runware.generate(
            positive_prompt="seamless repeat pattern tile",
            seed_image_url=b64_url,
            strength=0.05,  # 5% modification — quasi-identique à l'original
            steps=4,        # minimum stable pour FLUX Dev
            cfg_scale=1.0,
            tiling=False,
        )
        if not relay_url:
            logger.error("[upscale_existing] relay imageInference échoué pour %s", fname)
            return None

        # 3. AI upscale ×4 via Runware Real-ESRGAN → 4096×4096
        upscaled_url = runware.upscale(relay_url, upscale_factor=4)
        if not upscaled_url:
            logger.error("[upscale_existing] upscale Runware échoué pour %s", fname)
            return None

        upscaled_bytes = runware.download(upscaled_url)
        if not upscaled_bytes:
            logger.error("[upscale_existing] download échoué pour %s", fname)
            return None

        # 4. Charger le 4096×4096 et redimensionner à 4500×4500
        sharp = PILImage.open(io.BytesIO(upscaled_bytes)).convert("RGB")
        if sharp.size != (TARGET_SIZE, TARGET_SIZE):
            sharp = sharp.resize((TARGET_SIZE, TARGET_SIZE), PILImage.LANCZOS)

        # 5. Sauvegarder avec DPI 300
        os.makedirs(out_dir, exist_ok=True)
        sharp.save(out_path, format="PNG", dpi=(300, 300))
        size_mb = os.path.getsize(out_path) / 1024 / 1024
        logger.info("[upscale_existing] ✅ %s → %.1f MB (4500×4500 AI sharp)", fname, size_mb)
        return out_path

    except Exception as exc:
        logger.error("[upscale_existing] erreur %s: %s", fname, exc)
        return None


def fix_directory(
    input_dir: str = "output/spoonflower",
    output_dir: Optional[str] = None,
    overwrite: bool = True,
    limit: Optional[int] = None,
    glob_pattern: str = "*.png",
) -> dict:
    """
    Re-upscale IA toutes les images d'un dossier.

    Args:
        input_dir  : dossier source (images blurry actuelles)
        output_dir : dossier de sortie (None = écrase les originaux)
        overwrite  : si True, remplace l'original
        limit      : tester sur N images d'abord
        glob_pattern : filtre fichiers

    Returns: dict {filename: out_path ou None}
    """
    import glob as _glob
    from trend_discovery.generators.runware_generator import RunwareGenerator as RunwareClient

    api_key = os.getenv("RUNWARE_API_KEY", "")
    if not api_key:
        print("ERREUR : RUNWARE_API_KEY non définie.")
        sys.exit(1)

    files = sorted(_glob.glob(os.path.join(input_dir, glob_pattern)))
    # Exclure les colorways déjà générés
    files = [f for f in files if "__" not in os.path.basename(f)]
    if limit:
        files = files[:limit]

    if not files:
        print(f"Aucun PNG trouvé dans {input_dir}")
        return {}

    runware = RunwareClient(api_key=api_key)
    out_dir = output_dir or input_dir

    print(f"\n{'='*60}")
    print(f"  UPSCALE IA — {len(files)} image(s) via Runware Real-ESRGAN")
    print(f"  Pipeline : {input_dir}/")
    print(f"  Sortie   : {out_dir}/ ({'overwrite' if overwrite else 'suffix __sharp'})")
    print(f"  Coût estimé : ~${len(files) * 0.009:.2f} (relay imageInference + upscale Runware)")
    print(f"{'='*60}")

    results = {}
    ok = 0
    for i, fp in enumerate(files, 1):
        fname = os.path.basename(fp)
        print(f"  [{i:2d}/{len(files)}] {fname[:55]}…", end=" ", flush=True)
        out = fix_image(fp, runware, out_dir, overwrite=overwrite)
        if out:
            print("✅")
            ok += 1
        else:
            print("❌")
        results[fname] = out

    print(f"\n✅ {ok}/{len(files)} images re-upscalées → {out_dir}/")
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)

    parser = argparse.ArgumentParser(description="Re-upscale IA des images existantes via Runware")
    parser.add_argument("--input",   default="./output/spoonflower", help="Dossier source")
    parser.add_argument("--output",  default="",    help="Dossier sortie (vide = overwrite)")
    parser.add_argument("--limit",   type=int, default=0, help="Tester sur N images (0 = toutes)")
    parser.add_argument("--no-overwrite", action="store_true", help="Sauvegarde avec suffixe __sharp")
    args = parser.parse_args()

    fix_directory(
        input_dir=args.input,
        output_dir=args.output or None,
        overwrite=not args.no_overwrite,
        limit=args.limit or None,
    )
