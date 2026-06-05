"""
Seamless Auditor — détecte et corrige automatiquement les tuiles non-seamless.

Algorithme :
  1. Check : compare bande gauche↔droite et haut↔bas (MAD pixel).
     Score < threshold → seamless. Score ≥ threshold → coutures visibles.
  2. Fix  : mirror quad 2×2 (orig | flip_H / flip_V | rot180).
     La symétrie garantit ZÉRO couture visible — toujours parfait.
     L'image est redimensionnée à 4500×4500 après assemblage.

Usage :
    auditor = SeamlessAuditor()
    report  = auditor.audit_and_fix_dir("output/spoonflower", fix=True)
    # → dict {filename: {"score": float, "was_fixed": bool, "output": str}}
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

# MAD [0–255] threshold: images below this are considered seamless
SEAMLESS_THRESHOLD = 12.0

# Target size for fixed images
TARGET_SIZE = 4500


def _edge_score(arr: np.ndarray, strip: int = 30) -> float:
    """
    Mean Absolute Difference between opposite border strips.
    Returns value in [0, 255]: lower = more seamless.

    For a seamless tile: right edge should flow into left edge of next tile
    (same values), and bottom into top of the tile below.
    """
    h, w, _ = arr.shape
    strip = min(strip, w // 4, h // 4)

    left   = arr[:, :strip, :].astype(np.float32)
    right  = arr[:, -strip:, :].astype(np.float32)
    top    = arr[:strip, :, :].astype(np.float32)
    bottom = arr[-strip:, :, :].astype(np.float32)

    h_diff = np.mean(np.abs(left - right))
    v_diff = np.mean(np.abs(top  - bottom))
    return float((h_diff + v_diff) / 2.0)


def _mirror_quad(arr: np.ndarray) -> np.ndarray:
    """
    Build a 2×2 mirror quad from a single tile.

    Layout:
      Q1 (original)          | Q2 (flip horizontal)
      Q3 (flip vertical)     | Q4 (flip both = rot180)

    The shared edges are exact mirrors of each other → ZERO seam.
    """
    q1 = arr
    q2 = arr[:, ::-1, :]
    q3 = arr[::-1, :, :]
    q4 = arr[::-1, ::-1, :]

    top    = np.concatenate([q1, q2], axis=1)
    bottom = np.concatenate([q3, q4], axis=1)
    return np.concatenate([top, bottom], axis=0)


class SeamlessAuditor:
    """
    Audite et corrige automatiquement les images de tuile PNG.

    Méthodes principales:
      check(img_path)              → (score, is_seamless)
      fix(img_path, out_path)      → out_path fixed image
      audit_and_fix_dir(dir, ...)  → rapport complet
    """

    def __init__(self, threshold: float = SEAMLESS_THRESHOLD, target_size: int = TARGET_SIZE):
        self.threshold = threshold
        self.target_size = target_size

    # ── Public API ─────────────────────────────────────────────────────────────

    def check(self, img_path: str) -> Tuple[float, bool]:
        """
        Returns (edge_score, is_seamless).
        edge_score: MAD in [0, 255]; lower = better.
        is_seamless: True if score < threshold.
        """
        from PIL import Image
        arr = np.array(Image.open(img_path).convert("RGB"))
        score = _edge_score(arr)
        return score, score < self.threshold

    def fix(self, img_path: str, out_path: Optional[str] = None) -> str:
        """
        Applique le mirror quad et sauvegarde.
        out_path: si None, ajoute '__seamless' avant l'extension.
        Returns: out_path of the fixed file.
        """
        from PIL import Image

        src = Path(img_path)
        if out_path is None:
            out_path = str(src.parent / (src.stem + "__seamless" + src.suffix))

        img = Image.open(img_path).convert("RGB")
        arr = np.array(img)

        quad = _mirror_quad(arr)
        quad_img = Image.fromarray(quad.astype(np.uint8))
        fixed = quad_img.resize((self.target_size, self.target_size), Image.LANCZOS)

        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        fixed.save(out_path, format="PNG", dpi=(300, 300))
        size_mb = os.path.getsize(out_path) / 1024 / 1024
        logger.info("[seamless_auditor] fixed → %s (%.1f MB)", Path(out_path).name, size_mb)
        return out_path

    def audit_and_fix_dir(
        self,
        input_dir: str,
        output_dir: Optional[str] = None,
        fix: bool = True,
        overwrite: bool = False,
        glob_pattern: str = "*.png",
    ) -> Dict[str, dict]:
        """
        Audite tous les PNGs du dossier, corrige ceux qui ne sont pas seamless.

        Args:
            input_dir    : dossier source
            output_dir   : dossier de sortie (None = in-place dans input_dir)
            fix          : si True, applique le mirror quad sur les images non-seamless
            overwrite    : si True, écrase les images originales (sinon ajoute __seamless)
            glob_pattern : pattern de fichiers (défaut *.png)

        Returns:
            dict {filename: {"score": float, "is_seamless": bool, "was_fixed": bool, "output": str}}
        """
        import glob as _glob

        out_dir = output_dir or input_dir
        os.makedirs(out_dir, exist_ok=True)

        files = sorted(_glob.glob(os.path.join(input_dir, glob_pattern)))
        # Exclure les déjà-fixés pour éviter la récursion
        files = [f for f in files if "__seamless" not in os.path.basename(f)]

        if not files:
            logger.warning("[seamless_auditor] aucun PNG trouvé dans %s", input_dir)
            return {}

        report: Dict[str, dict] = {}
        n_ok = n_fixed = n_skip = 0

        logger.info("[seamless_auditor] audit de %d images (seuil MAD=%.1f)…", len(files), self.threshold)

        for fp in files:
            fname = os.path.basename(fp)
            try:
                score, is_seamless = self.check(fp)
            except Exception as exc:
                logger.warning("[seamless_auditor] erreur check %s: %s", fname, exc)
                report[fname] = {"score": -1, "is_seamless": False, "was_fixed": False, "output": fp, "error": str(exc)}
                continue

            entry: dict = {"score": round(score, 2), "is_seamless": is_seamless, "was_fixed": False, "output": fp}

            if is_seamless:
                status = "✅ seamless"
                n_ok += 1
            else:
                status = f"⚠️  non-seamless (MAD={score:.1f})"
                if fix:
                    if overwrite:
                        out_path = os.path.join(out_dir, fname)
                    else:
                        stem = Path(fname).stem
                        out_path = os.path.join(out_dir, stem + "__seamless.png")

                    # Skip if already exists and not overwrite
                    if os.path.exists(out_path) and not overwrite:
                        status += " → déjà corrigé, ignoré"
                        n_skip += 1
                        entry["output"] = out_path
                        entry["was_fixed"] = False  # exists already
                    else:
                        try:
                            out = self.fix(fp, out_path)
                            entry["output"] = out
                            entry["was_fixed"] = True
                            status += f" → corrigé: {Path(out).name}"
                            n_fixed += 1
                        except Exception as exc:
                            logger.error("[seamless_auditor] erreur fix %s: %s", fname, exc)
                            status += f" → ERREUR: {exc}"

            logger.info("[seamless_auditor] %s | %s", fname[:50], status)
            report[fname] = entry

        logger.info(
            "[seamless_auditor] résumé: %d seamless / %d corrigés / %d ignorés / %d total",
            n_ok, n_fixed, n_skip, len(files),
        )
        return report

    def save_report(self, report: Dict[str, dict], output_dir: str = "reports") -> str:
        """Sauvegarde le rapport d'audit seamless en JSON + Markdown."""
        import json
        from datetime import datetime

        os.makedirs(output_dir, exist_ok=True)
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M")

        # JSON
        json_path = os.path.join(output_dir, f"seamless_audit_{ts}.json")
        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump({"generated_at": ts, "threshold_mad": self.threshold, "results": report}, fh, indent=2)

        # Markdown
        md_lines = [
            f"# Rapport Audit Seamless — {ts[:4]}-{ts[4:6]}-{ts[6:8]} {ts[9:11]}:{ts[11:]}\n\n",
            f"Seuil MAD : {self.threshold} | Images auditées : {len(report)}\n\n",
            "| Image | Score MAD | Seamless | Corrigée |\n",
            "|-------|-----------|----------|----------|\n",
        ]
        for fname, entry in sorted(report.items()):
            sc = entry.get("score", -1)
            ok = "✅" if entry.get("is_seamless") else "❌"
            fx = "✅" if entry.get("was_fixed") else ("—" if entry.get("is_seamless") else "⚠️")
            md_lines.append(f"| `{fname[:60]}` | {sc:.1f} | {ok} | {fx} |\n")

        md_path = os.path.join(output_dir, f"seamless_audit_{ts}.md")
        with open(md_path, "w", encoding="utf-8") as fh:
            fh.writelines(md_lines)

        logger.info("[seamless_auditor] rapport → %s", md_path)
        return md_path
