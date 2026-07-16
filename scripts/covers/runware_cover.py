#!/usr/bin/env python3
"""
Génère les images d'art (face) des 3 concepts de couverture « CYCLE 404 »
via Runware FLUX.1 Dev, puis upscale IA ×4. Sauvegarde des PNG dans --out.

Nécessite RUNWARE_API_KEY (secret GitHub Actions).

Usage :
  RUNWARE_API_KEY=... python runware_cover.py --out art --concepts chambre404,reflet,standby
"""
from __future__ import annotations

import argparse
import os
import sys
import time
import uuid

import requests

RUNWARE_URL = "https://api.runware.ai/v1"
MODEL = os.getenv("RUNWARE_MODEL", "runware:101@1")  # FLUX.1 Dev
CFG = 4.0
STEPS = 28
GEN_W, GEN_H = 832, 1344  # portrait ~5:8, divisibles par 64
UPSCALE = 4

# 4 prompts du brief : 2 directions (A cinématographique, B graphique) × 2 concepts.
# Texte repris tel quel (l'illustration EST le sujet — pas d'aplat noir).
CONCEPTS = {
    # --- Direction A — Cinématographique (photoréaliste stylisé) ---
    "decor_dechire": (
        "Cinematic book cover illustration, dystopian psychological thriller. A woman in a "
        "long coat seen from behind, standing in a hospital corridor bathed in cold fluorescent "
        "light, facing a door numbered 404. The corridor wall on one side is torn open like "
        "theater scenery, revealing behind it a vast dark film studio: scaffolding, spotlights "
        "on rigs, thick cables, and one small red recording light glowing in the blackness. "
        "Dramatic contrast, teal and amber grade, volumetric light, fine film grain, painterly "
        "photorealism, ultra detailed, no text, no letters. Vertical 5:8 composition, upper "
        "third kept darker and simpler for the title."),
    "chambre_plateau": (
        "Cinematic book cover illustration. A hospital room seen from above at a slight angle: "
        "a woman sits on the edge of the bed in pale morning light — but the walls of the room "
        "stop like stage-set panels, and beyond them stretches an immense dark soundstage with "
        "camera cranes and silhouetted technicians watching her. She is the only lit element. "
        "Oppressive scale, cold light inside the set, warm darkness outside, hyper-detailed, no "
        "text. Vertical 5:8, negative space at the top for the title."),
    # --- Direction B — Graphique / illustrée (style affiche) ---
    "saul_bass": (
        "Modern graphic thriller book cover, bold flat illustration style inspired by Saul Bass "
        "and contemporary noir covers. A woman's silhouette walks inside the giant red digits "
        "\"404\" shaped like corridors seen in cross-section; tiny surveillance camera shapes "
        "hidden in the negative space. Limited palette: deep black, blood red, off-white. Strong "
        "shapes, screen-print texture, high contrast, no text, no letters, vertical 5:8."),
    "oeil_ecran": (
        "Striking graphic book cover illustration: a woman's profile face merging into a wall of "
        "hundreds of tiny glowing television screens, each screen showing a fragment of an "
        "ordinary life; one screen is blood red. Duotone palette (near-black blue and warm "
        "off-white, single red accent), grainy risograph texture, bold poster composition, no "
        "text, vertical 5:8."),
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


def generate(session, prompt):
    uid = str(uuid.uuid4())
    task = {
        "taskType": "imageInference", "taskUUID": uid, "model": MODEL,
        "positivePrompt": prompt, "width": GEN_W, "height": GEN_H,
        "steps": STEPS, "CFGScale": CFG, "numberResults": 1,
        "outputType": ["URL"], "outputFormat": "PNG",
        "checkNSFW": False, "includeCost": True, "tiling": False,
    }
    resp = post(session, [task])
    res = find(resp, uid, "imageInference")
    if not res or not res.get("imageURL"):
        raise RuntimeError(f"génération échouée: {res}")
    return res["imageURL"], res.get("cost")


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
            gen_url, c1 = generate(session, prompt)
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
    ap.add_argument("--concepts", default="decor_dechire,chambre_plateau,saul_bass,oeil_ecran")
    a = ap.parse_args()

    key = os.getenv("RUNWARE_API_KEY", "")
    if not key:
        print("RUNWARE_API_KEY absente — impossible de générer.", file=sys.stderr)
        sys.exit(2)

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
