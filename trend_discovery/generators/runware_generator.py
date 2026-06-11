"""
Générateur d'images via Runware API.

Runware est une API d'IA générative rapide et économique.
Elle supporte Stable Diffusion XL, Flux, et de nombreux modèles.

Une seule clé : RUNWARE_API_KEY
Inscription : https://runware.ai

Pipeline pour Spoonflower :
  1. Génère l'image de base (1024×1024)
  2. Upscale ×4 → ~4096×4096
  3. Retourne l'URL de l'image haute résolution

Coût estimé : ~0,003–0,008 $ par image finale (génération + upscale).
"""
from __future__ import annotations

import logging
import os
import time
import uuid
from typing import Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)

RUNWARE_API_KEY = os.getenv("RUNWARE_API_KEY", "")
RUNWARE_BASE_URL = "https://api.runware.ai/v1"

# Modèle par défaut : FLUX.1 Dev (runware:101@1) — meilleure qualité pour seamless patterns.
# FLUX.1 Dev comprend les phrases naturelles, sweet spot CFG ~3.5–4.5, ~28 steps.
# Alternatives : "runware:100@1" = FLUX.1 Schnell (rapide, CFG ignoré, 4 steps, moins fin).
# Voir https://runware.ai/models pour la liste complète.
DEFAULT_MODEL = os.getenv("RUNWARE_MODEL", "runware:101@1")

# CFG par défaut adapté à FLUX.1 Dev (au-delà de ~5 l'image se crispe / se déforme)
DEFAULT_CFG = 4.0

# Taille de génération initiale (sera upscalée ensuite)
GENERATION_SIZE = 1024  # px (carré — optimal pour seamless patterns)


class RunwareGenerator:
    """
    Client Runware API pour la génération et l'upscaling d'images.

    Utilisé uniquement si RUNWARE_API_KEY est configurée.
    Sans clé : le système ne génère pas d'images mais continue le scoring.
    """

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            "Authorization": f"Bearer {RUNWARE_API_KEY}",
            "Content-Type": "application/json",
        })
        self.last_cost = None  # coût réel du dernier appel (si includeCost)

    def is_available(self) -> bool:
        return bool(RUNWARE_API_KEY)

    def _post(self, tasks: list, timeout: int = 120) -> Optional[Dict]:
        """Envoie un batch de tâches à Runware et retourne la réponse."""
        try:
            resp = self._session.post(
                RUNWARE_BASE_URL,
                json=tasks,
                timeout=timeout,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.HTTPError as exc:
            logger.error(
                "[runware] HTTP %s: %s — %s",
                exc.response.status_code,
                exc.response.text[:200],
                exc,
            )
            return None
        except Exception as exc:
            logger.error("[runware] request failed: %s", exc)
            return None

    def _extract_result(self, response: Dict, task_uuid: str, task_type: str) -> Optional[Dict]:
        """Extrait le résultat d'une tâche spécifique dans la réponse."""
        if not response:
            return None
        data = response.get("data", [])
        for item in data:
            if item.get("taskUUID") == task_uuid:
                return item
        # Fallback : cherche le premier item du bon type
        for item in data:
            if item.get("taskType") == task_type:
                return item
        return None

    def generate(
        self,
        positive_prompt: str,
        negative_prompt: str = "",
        width: int = GENERATION_SIZE,
        height: int = GENERATION_SIZE,
        steps: int = 28,
        cfg_scale: float = DEFAULT_CFG,
        model: str = DEFAULT_MODEL,
        seed: int = -1,
        tiling: bool = True,
        seed_image_url: Optional[str] = None,
        strength: float = 0.25,
    ) -> Optional[str]:
        """
        Génère une image et retourne son URL.

        Args:
            tiling: active la génération seamless native (bords raccordés mathématiquement)
            seed: -1 = aléatoire (clé omise de l'API)
        """
        task_uuid = str(uuid.uuid4())
        task: Dict = {
            "taskType": "imageInference",
            "taskUUID": task_uuid,
            "model": model,
            "positivePrompt": positive_prompt,
            "width": width,
            "height": height,
            "steps": steps,
            "CFGScale": cfg_scale,
            "numberResults": 1,
            "outputType": ["URL"],
            "outputFormat": "PNG",
            "checkNSFW": False,
            "includeCost": False,
            "tiling": tiling,
        }
        # FLUX Dev 2 ignores negative prompts — only include if non-empty (for SDXL compat)
        if negative_prompt:
            task["negativePrompt"] = negative_prompt
        if seed != -1:
            task["seed"] = seed
        if seed_image_url:
            task["seedImage"] = seed_image_url
            task["strength"] = strength
        tasks = [task]

        logger.info("[runware] génération: %s… (%dx%d, model=%s)", positive_prompt[:60], width, height, model)
        response = self._post(tasks, timeout=120)
        result = self._extract_result(response, task_uuid, "imageInference")
        if not result:
            logger.error("[runware] génération échouée — pas de résultat")
            return None

        image_url = result.get("imageURL")
        if not image_url:
            logger.error("[runware] génération échouée — imageURL absent: %s", result)
            return None

        logger.info("[runware] image générée: %s", image_url)
        return image_url

    def upscale(
        self,
        image_url: str,
        upscale_factor: int = 4,
    ) -> Optional[str]:
        """
        Upscale une image ×N via Runware.

        1024×1024 × 4 = 4096×4096 (proche de 4500×4500 Spoonflower 15"@300DPI)

        Args:
            image_url: URL de l'image source (générée par Runware)
            upscale_factor: facteur d'agrandissement (2, 4)

        Returns:
            URL de l'image upscalée, ou None en cas d'erreur.
        """
        task_uuid = str(uuid.uuid4())
        tasks = [{
            "taskType": "imageUpscale",
            "taskUUID": task_uuid,
            "inputImage": image_url,
            "upscaleFactor": upscale_factor,
            "outputType": ["URL"],
            "outputFormat": "PNG",
            "includeCost": True,
        }]

        logger.info("[runware] upscale ×%d: %s", upscale_factor, image_url)
        response = self._post(tasks, timeout=120)
        result = self._extract_result(response, task_uuid, "imageUpscale")
        if not result:
            logger.error("[runware] upscale échoué — pas de résultat")
            return None

        upscaled_url = result.get("imageURL")
        if not upscaled_url:
            logger.error("[runware] upscale échoué — imageURL absent: %s", result)
            return None

        # Coût réel mesuré par Runware (None si non fourni)
        self.last_cost = result.get("cost")

        logger.info("[runware] upscale OK: %s (cost=%s)", upscaled_url, self.last_cost)
        return upscaled_url

    def download(self, url: str, timeout: int = 60) -> Optional[bytes]:
        """Télécharge une image depuis son URL Runware."""
        try:
            resp = requests.get(url, timeout=timeout)
            resp.raise_for_status()
            return resp.content
        except Exception as exc:
            logger.error("[runware] download échoué (%s): %s", url, exc)
            return None

    def generate_and_upscale(
        self,
        positive_prompt: str,
        negative_prompt: str = "",
        upscale_factor: int = 4,
        model: str = DEFAULT_MODEL,
        cfg_scale: float = DEFAULT_CFG,
        retries: int = 2,
        seed_image_url: Optional[str] = None,
        strength: float = 0.25,
        tiling: bool = True,
        width: int = GENERATION_SIZE,
        height: int = GENERATION_SIZE,
        steps: int = 28,
        require_upscale: bool = False,
    ) -> Tuple[Optional[bytes], Optional[str]]:
        """
        Génère une image (1024×1024) puis l'upscale via Runware AI (Real-ESRGAN × 4 → 4096×4096).
        L'upscale IA est obligatoire pour la qualité Spoonflower (sans ça = flou LANCZOS).

        Returns:
            (image_bytes_4096, image_url_original_1024)
        """
        for attempt in range(retries + 1):
            if attempt > 0:
                wait = 2 ** attempt
                logger.info("[runware] retry %d/%d dans %ds", attempt, retries, wait)
                time.sleep(wait)

            # Étape 1 — génération native 1024×1024
            base_url = self.generate(
                positive_prompt=positive_prompt,
                negative_prompt=negative_prompt,
                model=model,
                cfg_scale=cfg_scale,
                seed_image_url=seed_image_url,
                strength=strength,
                tiling=tiling,
                width=width,
                height=height,
                steps=steps,
            )
            if not base_url:
                continue

            # Étape 2 — upscale IA ×4 via Runware (1024 → 4096)
            upscaled_url = self.upscale(base_url, upscale_factor=upscale_factor)
            if upscaled_url:
                image_bytes = self.download(upscaled_url)
                if image_bytes:
                    logger.info("[runware] ✅ image 4096×4096 via upscale IA × %d", upscale_factor)
                    return image_bytes, base_url

            # require_upscale : pas de fallback basse résolution — l'image est
            # rejetée pour être régénérée (sinon le packager l'étirerait en LANCZOS).
            if require_upscale:
                logger.error("[runware] upscale IA échoué et require_upscale=True — image rejetée")
                continue

            # Fallback : si l'upscale échoue, retourne quand même le 1024×1024
            logger.warning("[runware] upscale IA échoué — fallback sur 1024×1024 (qualité réduite)")
            image_bytes = self.download(base_url)
            if image_bytes:
                return image_bytes, base_url

        logger.error("[runware] generate_and_upscale échoué après %d tentatives", retries + 1)
        return None, None
