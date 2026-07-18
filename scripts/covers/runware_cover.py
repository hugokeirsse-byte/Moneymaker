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
    # v6 — vrais fils mats qui accrochent AUSSI les bras/mains ; AUCUN 404 dans le prompt
    # (le 404 brodé est ajouté ensuite par compositing). Dos de la blouse laissé vierge.
    "marionnette_hopital": (
        "Dystopian psychological thriller book cover, cinematic photograph, vertical 5:8. A woman"
        " seen from behind, standing in the middle of an empty, too-perfect symmetrical suburban"
        " street at cold winter dusk, thin snow on the verges, barefoot on the asphalt. She wears"
        " a pale blue-grey wrinkled hospital gown and a white hospital wristband; an amnesiac"
        " patient. She is controlled like a MARIONETTE: about eight distinct, taut, thin puppet"
        " strings — real pale matte cords, clearly readable as strings with small hooks and knots"
        " where they attach, NOT glowing light, NOT rain — descend from high above and hook into"
        " her body. Several attach to the tops of her shoulders and the back of her head, and"
        " importantly several run down and hook onto her ARMS, the backs of her hands and her"
        " wrists, and into the fabric of her gown, visibly tugging and lifting parts of her: one"
        " arm and hand are pulled slightly upward, a sleeve and a fold of the gown are pinched and"
        " raised into small peaks where the strings pull, as if a hidden puppeteer high above"
        " manipulates her body. The taut strings rise straight up, converging high overhead and"
        " dissolving softly into the low clouds at the very top edge of the frame, never abruptly"
        " cut. In the blurred background, only a few much fainter thin strings hang down over the"
        " distant houses on both sides. Cold steel-blue palette, one small distant red light far"
        " down the street, soft volumetric dusk light, fine film grain, eerie and melancholic. The"
        " back of her hospital gown is plain and clean. No text, no numbers anywhere, no"
        " typography, no logo."),
    "fenetre_auditorium": (
        "Cinematic book cover illustration, dystopian psychological thriller, vertical 5:8. A woman"
        " in a pale hospital gown, seen from behind, standing at a tall window in cold morning"
        " light. On the ledge four small pebbles: three grouped, one apart. In the glass the faint"
        " reflection of a dark auditorium of silhouetted spectators. A tiny red LED in the upper"
        " corner. Cold teal, one red accent. Painterly photorealism, film grain. Dark top. No text."),
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
