#!/usr/bin/env python3
"""
Génère les images d'art (face) des concepts de couverture « CYCLE 404 »
via Runware, puis upscale IA ×4. Sauvegarde des PNG dans --out.

Qualité maximale : essaie d'abord un modèle photo premium (FLUX 1.1 Pro,
puis FLUX.1 Pro) et retombe automatiquement sur FLUX.1 Dev si le compte n'y
a pas accès, pour garantir une sortie.

Nécessite RUNWARE_API_KEY (secret GitHub Actions).

Usage :
  RUNWARE_API_KEY=... python runware_cover.py --out art --concepts fenetre_auditorium
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import uuid

import requests

RUNWARE_URL = "https://api.runware.ai/v1"

# Chaîne de modèles, du plus qualitatif au repli garanti. Surchargable via
# RUNWARE_MODEL (place alors ce modèle en tête de liste).
MODEL_CHAIN = [
    "bfl:2@1",        # FLUX 1.1 [pro] — photo premium
    "bfl:1@1",        # FLUX.1 [pro]
    "runware:101@1",  # FLUX.1 [dev] — repli garanti
]
_override = os.getenv("RUNWARE_MODEL", "").strip()
if _override:
    MODEL_CHAIN = [_override] + [m for m in MODEL_CHAIN if m != _override]

CFG = 3.5
STEPS = 34
GEN_W, GEN_H = 832, 1344  # portrait ~5:8, divisibles par 64
UPSCALE = 4

CONCEPTS = {
    # Femme à la fenêtre, galets sur le rebord, reflet d'auditorium (spectateurs).
    "fenetre_auditorium": (
        "Cinematic book cover illustration, dystopian psychological thriller, vertical 5:8"
        " composition, designed to read clearly as a small thumbnail. A single strong focal"
        " figure: a woman in a pale hospital gown, seen from behind at three-quarter angle,"
        " standing at a tall window in soft cold morning light, her dark silhouette contrasting"
        " against the bright glass. On the window ledge, sharply detailed, four small round grey"
        " pebbles: three grouped together, one placed apart. In the window glass, instead of the"
        " room's reflection, there is the faint ghostly reflection of a vast dark auditorium"
        " filled with rows of silhouetted seated spectators watching her; the reflection must be"
        " subtle, readable only at second glance. A tiny red LED light is reflected in the upper"
        " corner of the glass. Outside the window, a quiet, slightly too-perfect provincial town"
        " under morning haze. Palette: cold teal shadows, pale amber window light, one red accent"
        " only. Painterly photorealism, volumetric light, fine film grain, ultra detailed,"
        " melancholic and unsettling. The wall above the window stays dim and uncluttered for the"
        " title. No text, no letters, no logos anywhere in the image."),

    # --- variations « visage + mur d'écrans » (conservées) ---
    "ecran_profil": (
        "Dystopian psychological thriller book cover, cinematic photograph. Realistic close side"
        " profile of a pensive woman in her early forties, calm expression, soft dramatic side"
        " lighting on real skin. The back of her head and neck gradually dissolve into a neat"
        " rectangular grid of old cathode-ray television monitors. Each screen clearly shows a"
        " coherent quiet moment of HER OWN life. One single screen glows blood red. Shot on a"
        " cinema camera, photorealistic real skin, cold teal and warm amber grade, film grain,"
        " dark uncluttered upper third for the title. No text, no letters. Vertical 5:8."),
    "ecran_face": (
        "Dystopian psychological thriller book cover, cinematic photograph. A realistic woman's"
        " face looking at the viewer through the narrow gaps of an orderly wall of glowing old"
        " television screens, as if trapped behind the monitors. Each surrounding screen shows a"
        " calm ordinary moment of the same woman's life in a clean grid; one screen flickers red."
        " Photorealistic, volumetric light, film grain, dark uncluttered upper third for the"
        " title. No text, no letters. Vertical 5:8."),
    "ecran_spectatrice": (
        "Dystopian psychological thriller book cover, cinematic photograph. A realistic woman seen"
        " from behind, alone in a dark room, softly lit by an enormous orderly wall of television"
        " screens filling the frame before her. Every screen shows a coherent moment of her own"
        " life at different ages. A single screen burns red. Cold blue rim light, photorealistic,"
        " film grain, dark uncluttered upper third for the title. No text, no letters. Vertical"
        " 5:8."),
}


def post(session, tasks, timeout=180):
    r = session.post(RUNWARE_URL, json=tasks, timeout=timeout)
    if r.status_code >= 400:
        print(f"[runware] HTTP {r.status_code}: {r.text[:300]}", file=sys.stderr)
        r.raise_for_status()
    return r.json()


def find(resp, uid, ttype):
    data = (resp or {}).get("data", [])
    for it in data:
        if it.get("taskUUID") == uid:
            return it
    for it in data:
        if it.get("taskType") == ttype:
            return it
    return None


def generate(session, prompt, model):
    uid = str(uuid.uuid4())
    task = {
        "taskType": "imageInference", "taskUUID": uid, "model": model,
        "positivePrompt": prompt, "width": GEN_W, "height": GEN_H,
        "numberResults": 1, "outputType": ["URL"], "outputFormat": "PNG",
        "checkNSFW": False, "includeCost": True,
    }
    # Les modèles BFL (pro) gèrent steps/CFG en interne : on ne les envoie que
    # pour les modèles runware/flux dev afin d'éviter un rejet de paramètres.
    if not model.startswith("bfl:"):
        task["steps"] = STEPS
        task["CFGScale"] = CFG
        task["tiling"] = False
    resp = post(session, [task])
    res = find(resp, uid, "imageInference")
    if not res or not res.get("imageURL"):
        raise RuntimeError(f"génération échouée: {res}")
    return res["imageURL"], res.get("cost")


def generate_best(session, prompt):
    """Essaie chaque modèle de la chaîne jusqu'à succès."""
    last = None
    for model in MODEL_CHAIN:
        try:
            url, cost = generate(session, prompt, model)
            print(f"    ✓ modèle utilisé: {model}")
            return url, cost, model
        except Exception as exc:
            print(f"    ✗ modèle {model} indisponible: {exc}", file=sys.stderr)
            last = exc
    raise RuntimeError(f"aucun modèle disponible: {last}")


def upscale(session, url, factor=UPSCALE):
    uid = str(uuid.uuid4())
    task = {
        "taskType": "imageUpscale", "taskUUID": uid, "inputImage": url,
        "upscaleFactor": factor, "outputType": ["URL"], "outputFormat": "PNG",
        "includeCost": True,
    }
    resp = post(session, [task])
    res = find(resp, uid, "imageUpscale")
    if not res or not res.get("imageURL"):
        raise RuntimeError(f"upscale échoué: {res}")
    return res["imageURL"], res.get("cost")


def download(url, path, timeout=120):
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)
    return len(r.content)


def run_concept(session, key, prompt, out, retries=2):
    for attempt in range(retries + 1):
        try:
            if attempt:
                time.sleep(2 ** attempt)
            gen_url, c1, model = generate_best(session, prompt)
            print(f"[{key}] généré (cost={c1}) → upscale ×{UPSCALE}")
            up_url, c2 = upscale(session, gen_url)
            path = os.path.join(out, f"{key}.png")
            n = download(up_url, path)
            print(f"[{key}] OK {path} ({n // 1024} Ko, cost total≈{(c1 or 0)+(c2 or 0):.4f})")
            return path
        except Exception as exc:
            print(f"[{key}] tentative {attempt+1} échouée: {exc}", file=sys.stderr)
    print(f"[{key}] ÉCHEC définitif", file=sys.stderr)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="art")
    ap.add_argument("--concepts", default="fenetre_auditorium")
    a = ap.parse_args()

    key = os.getenv("RUNWARE_API_KEY", "")
    if not key:
        print("RUNWARE_API_KEY absente — impossible de générer.", file=sys.stderr)
        sys.exit(2)

    print(f"Chaîne de modèles: {' → '.join(MODEL_CHAIN)}")
    os.makedirs(a.out, exist_ok=True)
    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {key}",
                            "Content-Type": "application/json"})

    ok = 0
    for concept in a.concepts.split(","):
        concept = concept.strip()
        if concept not in CONCEPTS:
            print(f"[{concept}] concept inconnu, ignoré", file=sys.stderr)
            continue
        if run_concept(session, concept, CONCEPTS[concept], a.out):
            ok += 1
    print(f"\n{ok} image(s) générée(s) dans {a.out}/")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
