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
    **kwargs,
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

    dbg: list = kwargs.get("_dbg", [])

    def _log(msg: str) -> None:
        print(msg, flush=True)
        dbg.append(msg)

    try:
        # 1. Ouvrir et downscaler à 1024×1024
        img = PILImage.open(src_path).convert("RGB")
        _log(f"[dbg] opened {fname} size={img.size}")
        small = img.resize((DOWNSCALE_TO, DOWNSCALE_TO), PILImage.LANCZOS)

        buf = io.BytesIO()
        small.save(buf, format="PNG")
        small_bytes = buf.getvalue()
        _log(f"[dbg] downscaled to {DOWNSCALE_TO}px, payload={len(small_bytes)/1024:.0f} KB")

        # 2. Essai direct : imageUpscale avec base64 data URL
        b64_url = _image_to_base64_url(small_bytes)
        _log("[dbg] tentative imageUpscale direct avec base64...")
        upscaled_url = runware.upscale(b64_url, upscale_factor=4)
        _log(f"[dbg] imageUpscale direct → {upscaled_url or 'ECHEC'}")

        # 3. Fallback relay si le direct échoue
        if not upscaled_url:
            _log("[dbg] fallback relay imageInference (strength=0.25, steps=4)...")
            relay_url = runware.generate(
                positive_prompt="pattern tile",
                seed_image_url=b64_url,
                strength=0.25,
                steps=4,
                cfg_scale=1.0,
                tiling=False,
            )
            _log(f"[dbg] relay_url → {relay_url or 'ECHEC'}")
            if not relay_url:
                _log(f"[dbg] ECHEC TOTAL relay pour {fname}")
                return None
            upscaled_url = runware.upscale(relay_url, upscale_factor=4)
            _log(f"[dbg] imageUpscale relay → {upscaled_url or 'ECHEC'}")
            if not upscaled_url:
                _log(f"[dbg] ECHEC upscale relay pour {fname}")
                return None

        upscaled_bytes = runware.download(upscaled_url)
        _log(f"[dbg] download → {len(upscaled_bytes)/1024:.0f} KB" if upscaled_bytes else "[dbg] download ECHEC")
        if not upscaled_bytes:
            return None

        # 4. Charger et redimensionner à 4500×4500
        sharp = PILImage.open(io.BytesIO(upscaled_bytes)).convert("RGB")
        _log(f"[dbg] upscaled size={sharp.size}")
        if sharp.size != (TARGET_SIZE, TARGET_SIZE):
            sharp = sharp.resize((TARGET_SIZE, TARGET_SIZE), PILImage.LANCZOS)

        # 5. Sauvegarder avec DPI 300
        os.makedirs(out_dir, exist_ok=True)
        sharp.save(out_path, format="PNG", dpi=(300, 300))
        size_mb = os.path.getsize(out_path) / 1024 / 1024
        _log(f"[dbg] ✅ saved {out_path} → {size_mb:.1f} MB")
        return out_path

    except Exception as exc:
        print(f"[upscale_existing] erreur {fname}: {exc}", flush=True)
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
    # Exclure uniquement les colorways (suffixe "__<palette>.png"), PAS les bases
    # qui s'appellent "<nom>___base_<date>.png" (triple underscore).
    files = [f for f in files if "___base" in os.path.basename(f) or "user_upload" in os.path.basename(f)]
    if limit:
        files = files[:limit]

    if not files:
        print(f"Aucun PNG trouvé dans {input_dir}")
        return {}

    runware = RunwareClient()  # lit RUNWARE_API_KEY depuis l'environnement
    out_dir = output_dir or input_dir

    print(f"\n{'='*60}")
    print(f"  UPSCALE IA — {len(files)} image(s) via Runware Real-ESRGAN")
    print(f"  Pipeline : {input_dir}/")
    print(f"  Sortie   : {out_dir}/ ({'overwrite' if overwrite else 'suffix __sharp'})")
    print(f"  Coût estimé : ~${len(files) * 0.009:.2f} (relay imageInference + upscale Runware)")
    print(f"{'='*60}")

    import datetime
    dbg_lines: list = []
    log_path = os.path.join("reports", "upscale_debug.log")
    os.makedirs("reports", exist_ok=True)

    results = {}
    ok = 0
    total_cost = 0.0
    cost_measured = False
    for i, fp in enumerate(files, 1):
        fname = os.path.basename(fp)
        img_dbg: list = []
        runware.last_cost = None
        print(f"  [{i:2d}/{len(files)}] {fname[:55]}…", end=" ", flush=True)
        out = fix_image(fp, runware, out_dir, overwrite=overwrite, _dbg=img_dbg)
        dbg_lines.extend(img_dbg)
        if getattr(runware, "last_cost", None) is not None:
            total_cost += float(runware.last_cost)
            cost_measured = True
        if out:
            print("✅")
            ok += 1
        else:
            print("❌")
        results[fname] = out

    cost_line = (
        f"COUT REEL MESURE : ${total_cost:.4f} pour {ok} images (MEASURED)"
        if cost_measured else
        f"COUT : non fourni par Runware (UNAVAILABLE) — estimation ~${ok*0.005:.2f} (HEURISTIC)"
    )
    print(f"  {cost_line}")
    dbg_lines.append(cost_line)

    # Mode append : ne pas écraser le log de l'appel précédent (pipeline puis uploads)
    with open(log_path, "a") as f:
        f.write(f"\n=== {input_dir} — {datetime.datetime.utcnow().isoformat()} ===\n")
        f.write("\n".join(dbg_lines))
        f.write("\n")

    print(f"\n✅ {ok}/{len(files)} images re-upscalées → {out_dir}/ — {cost_line}")
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
