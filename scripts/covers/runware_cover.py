#!/usr/bin/env python3
"""
Génère les images d'art (face) des concepts de couverture « CYCLE 404 »
via Runware, puis upscale IA (best-effort). Sauvegarde des PNG dans --out.

Nécessite RUNWARE_API_KEY (secret GitHub Actions).

Usage :
  RUNWARE_API_KEY=... python runware_cover.py --out art --concepts marionnette_hopital
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import uuid

import requests

RUNWARE_URL = "https://api.runware.ai/v1"

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
GEN_W, GEN_H = 832, 1344
UPSCALE = 2

CONCEPTS = {
    "fenetre_auditorium": (
        "Cinematic book cover illustration, dystopian psychological thriller, vertical 5:8"
        " composition. A woman in a pale hospital gown, seen from behind at three-quarter angle,"
        " standing at a tall window in soft cold morning light. On the window ledge four small"
        " round grey pebbles: three grouped, one apart. In the glass, the faint ghostly"
        " reflection of a vast dark auditorium of silhouetted spectators watching her. A tiny red"
        " LED reflected in the upper corner. Cold teal shadows, pale amber light, one red accent."
        " Painterly photorealism, film grain. Dark uncluttered top for the title. No text."),
    # v4 — 404 brodé dans le dos + fils partout descendant du ciel jusqu'en haut.
    "marionnette_hopital": (
        "Dystopian psychological thriller book cover, cinematic photograph, vertical 5:8. A woman"
        " seen from behind, standing alone in the exact middle of an empty, too-perfect"
        " symmetrical provincial suburban street at cold winter dusk, thin snow on the verges,"
        " barefoot on the cold asphalt. She wears a pale blue-grey thin wrinkled HOSPITAL GOWN"
        " open at the back, a white hospital identification wristband on her wrist; an amnesiac"
        " patient. MANY thin pale puppet strings descend from all across the sky and fill the"
        " whole upper part of the frame, rising and softly dissolving into the clouds at the very"
        " top edge of the image, never abruptly cut. The most pronounced strings attach to her"
        " body as if sewn directly into the fabric of her gown and fused into the skin of her"
        " shoulders, upper back, arms and the crown of her head. Other fainter, barely"
        " distinguishable strings descend onto the rooftops and facades of the identical houses on"
        " both sides, gently hooking the whole set. On the back of her hospital gown, the number"
        " '404' is embroidered in pale stitched thread, neat and clearly legible, matching the"
        " muted style. Cold steel-blue palette, one small distant red light far down the street,"
        " soft volumetric dusk light, fine film grain, eerie and melancholic. No other text, no"
        " letters anywhere except the embroidered 404 on the gown, no logo."),
    "plateau_salon": (
        "Dystopian psychological thriller book cover, cinematic photograph. A warm perfect"
        " provincial living room at night whose entire back wall is a theatrical set flat that"
        " stops in mid-air, revealing a vast dark film soundstage: scaffolding, a camera on a"
        " crane, cables, silhouettes of a hidden crew. One small red recording light glows. Cosy"
        " warm room, cold immense studio behind. Photorealistic, teal-and-amber grade, film grain."
        " Dark uncluttered top for the title. No text. Vertical 5:8."),
    "mur_enfants": (
        "Dystopian psychological thriller book cover, cinematic photograph. Close shot of a woman"
        " in profile pressing her cheek and palm against an old flowered wallpaper wall, eyes"
        " closed. Through cracks and a peeling corner, warm light escapes and the faint"
        " silhouettes of two children playing show, as if trapped inside the wall; behind the peel"
        " the wall is a painted stage backdrop on plywood. Warm amber against cold blue, one small"
        " red glow in a crack. Photorealistic, film grain. Dark uncluttered top. No text. 5:8."),
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
    gen_url = None
    for attempt in range(retries + 1):
        try:
            if attempt:
                time.sleep(2 ** attempt)
            gen_url, c1, model = generate_best(session, prompt)
            print(f"[{key}] généré (cost={c1}, modèle={model})")
            break
        except Exception as exc:
            print(f"[{key}] génération tentative {attempt+1} échouée: {exc}", file=sys.stderr)
    if not gen_url:
        print(f"[{key}] ÉCHEC génération", file=sys.stderr)
        return None

    final_url = gen_url
    for attempt in range(2):
        try:
            if attempt:
                time.sleep(2 ** attempt)
            final_url, _ = upscale(session, gen_url)
            print(f"[{key}] upscale ×{UPSCALE} OK")
            break
        except Exception as exc:
            print(f"[{key}] upscale tentative {attempt+1} échouée (on garde l'original): {exc}",
                  file=sys.stderr)
            final_url = gen_url

    path = os.path.join(out, f"{key}.png")
    n = download(final_url, path)
    print(f"[{key}] OK {path} ({n // 1024} Ko)")
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="art")
    ap.add_argument("--concepts", default="marionnette_hopital")
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
