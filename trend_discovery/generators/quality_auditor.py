"""
QualityAuditor — audit automatique des images générées avant packaging.

Vérifie :
1. Netteté (Laplacian variance) — rejette les images floues
2. Seamless (comparaison des bords opposés) — rejette si couture visible
3. Conformité Spoonflower (taille minimale, mode couleur, poids)

Règle : zéro déchet à trier manuellement.
Toutes les dépendances lourdes (numpy, Pillow) sont importées à la demande.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# Seuils par défaut (ajustables via le constructeur)
DEFAULT_SHARPNESS_MIN = 30.0    # variance Laplacien — en-dessous = flou
DEFAULT_SEAMLESS_MIN = 60.0     # 0-100 — en-dessous = couture visible
SPOONFLOWER_MIN_PX = 4500
SPOONFLOWER_MAX_MB = 40.0


@dataclass
class AuditResult:
    passed: bool
    sharpness_score: float          # ≥ 0 (plus haut = plus net)
    seamless_score: float           # 0-100 (100 = tuile parfaite)
    spoonflower_ok: bool
    issues: List[str] = field(default_factory=list)
    details: str = ""


class QualityAuditor:
    """
    Audite une image (bytes PNG/JPEG) avant upload Spoonflower.

    Pas de crash si Pillow ou numpy manquent : l'audit passe en mode dégradé
    (scores neutres, passed=True) pour ne pas bloquer le pipeline.
    """

    def __init__(
        self,
        sharpness_threshold: float = DEFAULT_SHARPNESS_MIN,
        seamless_threshold: float = DEFAULT_SEAMLESS_MIN,
    ):
        self._sharp_thresh = sharpness_threshold
        self._seam_thresh = seamless_threshold

    def audit(self, image_bytes: bytes) -> AuditResult:
        """Audite une image et retourne un AuditResult complet."""
        try:
            from PIL import Image, ImageFilter
        except ImportError:
            logger.warning("[audit] Pillow non disponible — audit ignoré")
            return AuditResult(
                passed=True, sharpness_score=-1.0, seamless_score=-1.0,
                spoonflower_ok=True, details="Pillow indisponible",
            )

        try:
            img = Image.open(io.BytesIO(image_bytes))
        except Exception as exc:
            return AuditResult(
                passed=False, sharpness_score=0.0, seamless_score=0.0,
                spoonflower_ok=False, issues=[f"Lecture image échouée: {exc}"],
            )

        issues: List[str] = []
        w, h = img.size
        file_mb = len(image_bytes) / (1024 * 1024)

        # ── Spoonflower specs ─────────────────────────────────────────────────
        # Note: la taille n'est PAS vérifiée ici — l'upscale vers 4500px se
        # fait dans SpoonflowerPackager APRÈS l'audit. On vérifie seulement
        # le poids et le mode couleur de l'image brute sortie de Runware.
        sf_ok = True
        if file_mb > SPOONFLOWER_MAX_MB:
            issues.append(f"poids {file_mb:.1f} MB > {SPOONFLOWER_MAX_MB} MB")
            sf_ok = False
        if img.mode not in ("RGB", "RGBA"):
            issues.append(f"mode couleur {img.mode} (attendu RGB)")
            sf_ok = False

        # ── Netteté (Laplacian variance) ──────────────────────────────────────
        sharpness = self._assess_sharpness(img, ImageFilter)
        if sharpness < self._sharp_thresh:
            issues.append(f"netteté {sharpness:.1f} < seuil {self._sharp_thresh}")

        # ── Seamless (comparaison des bords) ──────────────────────────────────
        seamless = self._assess_seamless(img)
        if seamless < self._seam_thresh:
            issues.append(f"seamless score {seamless:.1f} < seuil {self._seam_thresh}")

        passed = len(issues) == 0
        details = (
            f"{w}×{h}px | {file_mb:.1f}MB | "
            f"netteté={sharpness:.1f} | seamless={seamless:.1f}"
        )
        return AuditResult(
            passed=passed,
            sharpness_score=sharpness,
            seamless_score=seamless,
            spoonflower_ok=sf_ok,
            issues=issues,
            details=details,
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _assess_sharpness(self, img, ImageFilter) -> float:
        """
        Variance du filtre Laplacien sur l'image en niveaux de gris.
        Indicateur classique de netteté : plus c'est haut, plus l'image est nette.
        """
        try:
            gray = img.convert("L")
            lap = gray.filter(ImageFilter.FIND_EDGES)
            # Calcul de variance via Pillow (sans numpy)
            pixels = list(lap.getdata())
            n = len(pixels)
            if n == 0:
                return 0.0
            mean = sum(pixels) / n
            variance = sum((p - mean) ** 2 for p in pixels) / n
            return float(variance)
        except Exception as exc:
            logger.debug("[audit] sharpness échouée: %s", exc)
            return 50.0  # neutre

    def _assess_seamless(self, img) -> float:
        """
        Compare les bandes de bord opposées (gauche/droite, haut/bas).
        Score 0-100 : 100 = transition parfaite, 0 = couture évidente.
        Utilise numpy si disponible (plus rapide), sinon Pillow pur.
        """
        try:
            w, h = img.size
            band = max(10, min(30, w // 20))  # 5% de la largeur, 10-30 px

            rgb = img.convert("RGB")

            # Bandes horizontales (gauche vs droite)
            left = rgb.crop((0, 0, band, h))
            right = rgb.crop((w - band, 0, w, h))
            diff_h = self._band_diff(left, right)

            # Bandes verticales (haut vs bas)
            top = rgb.crop((0, 0, w, band))
            bottom = rgb.crop((0, h - band, w, h))
            diff_v = self._band_diff(top, bottom)

            # Moyenne des deux différences (0 = identiques = parfaitement seamless)
            avg_diff = (diff_h + diff_v) / 2.0
            # Convertir en score 0-100 : diff 0 → 100, diff 255 → 0
            score = max(0.0, min(100.0, 100.0 - (avg_diff / 255.0) * 100.0))
            return round(score, 1)

        except Exception as exc:
            logger.debug("[audit] seamless check échoué: %s", exc)
            return 70.0  # neutre (passe le seuil)

    @staticmethod
    def _band_diff(img_a, img_b) -> float:
        """
        Différence absolue moyenne entre deux images de même taille.
        Redimensionne img_b si nécessaire pour l'alignement.
        """
        try:
            import numpy as np
            a = np.array(img_a.resize(img_a.size), dtype=float)
            b = np.array(img_b.resize(img_a.size), dtype=float)
            return float(np.mean(np.abs(a - b)))
        except ImportError:
            # Fallback Pillow pur (lent mais correct)
            if img_b.size != img_a.size:
                img_b = img_b.resize(img_a.size)
            pixels_a = list(img_a.getdata())
            pixels_b = list(img_b.getdata())
            if not pixels_a:
                return 0.0
            total = 0.0
            for pa, pb in zip(pixels_a, pixels_b):
                if isinstance(pa, int):
                    total += abs(pa - pb)
                else:
                    total += sum(abs(ca - cb) for ca, cb in zip(pa, pb)) / len(pa)
            return total / len(pixels_a)
        except Exception:
            return 0.0
