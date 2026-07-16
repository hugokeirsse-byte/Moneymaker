#!/usr/bin/env python3
"""
Génère les images d'art (face) des concepts de couverture « CYCLE 404 »
via Runware FLUX.1 Dev, puis upscale IA ×4. Sauvegarde des PNG dans --out.

Nécessite RUNWARE_API_KEY (secret GitHub Actions).

Usage :
  RUNWARE_API_KEY=... python runware_cover.py --out art \
     --concepts ecran_profil,ecran_face,ecran_oeil,ecran_spectatrice
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
CFG = 3.5
STEPS = 34
GEN_W, GEN_H = 832, 1344  # portrait ~5:8, divisibles par 64
UPSCALE = 4

# Suffixe commun : impose le rendu PHOTOréaliste (pas illustré) et réserve le
# tiers supérieur sombre pour le titre. Une grille d'écrans NETTE et ORGANISÉE.
COMMON = (
    " Shot on a full-frame cinema camera, 85mm lens, photorealistic, hyper-detailed real"
    " human skin with pores and fine texture, natural catchlights in the eyes, shallow depth"
    " of field. Cold teal shadows and warm amber screen glow, cinematic color grade, subtle"
    " film grain. The wall of screens is an ORDERLY rectangular grid of identical old CRT"
    " monitors, each screen sharp and legible, NOT random noise. The upper third of the frame"
    " is kept dark and uncluttered for a title. No text, no letters, no captions, no logo,"
    " no watermark. Vertical 5:8 book-cover composition."
)

# 4 variations issues du concept « visage + mur d'écrans » (oeil_ecran),
# mais VISAGE RÉALISTE et écrans COHÉRENTS (fragments de la vie de l'héroïne).
CONCEPTS = {
    # 1 — Profil : l'arrière du crâne se dissout dans la grille d'écrans.
    "ecran_profil": (
        "Dystopian psychological thriller book cover, cinematic photograph. Realistic close side"
        " profile of a pensive woman in her early forties, calm expression, soft dramatic side"
        " lighting on real skin. The back of her head and neck gradually dissolve into a neat"
        " rectangular grid of old cathode-ray television monitors. Each screen clearly shows a"
        " coherent quiet moment of HER OWN life — a child laughing, a kitchen at breakfast, a"
        " hospital bed, a suburban living room, a wedding photo — as if her whole existence is"
        " being broadcast. One single screen in the grid glows blood red." + COMMON),
    # 2 — Face : le vrai visage apparaît DERRIÈRE un mur d'écrans, prisonnière.
    "ecran_face": (
        "Dystopian psychological thriller book cover, cinematic photograph. A realistic woman's"
        " face seen looking straight at the viewer through the narrow gaps of a large orderly"
        " wall of glowing old television screens, as if she is trapped behind the monitors. Her"
        " real eyes and part of her face are visible between the screens. Every surrounding"
        " screen shows a calm ordinary moment of the SAME woman's life, arranged in a clean grid;"
        " one screen flickers red. Moody surveillance atmosphere, volumetric light." + COMMON),
    # 3 — Œil macro : la grille d'écrans se reflète dans l'iris.
    "ecran_oeil": (
        "Dystopian psychological thriller book cover, cinematic photograph. Extreme realistic"
        " macro close-up of a single human eye, hyper-detailed iris and eyelashes, real skin"
        " around it in shadow. Reflected sharply and in miniature inside the iris: an orderly"
        " wall of surveillance monitors, each tiny screen showing a coherent scene of the same"
        " woman's daily life, and a hidden film crew filming her. One reflected screen glows"
        " red. The rest of the frame falls into deep shadow." + COMMON),
    # 4 — Spectatrice : de dos face au mur d'écrans qui diffuse sa propre vie.
    "ecran_spectatrice": (
        "Dystopian psychological thriller book cover, cinematic photograph. A realistic woman"
        " seen from behind, sitting alone in a dark room, her shoulders and hair softly lit by"
        " the glow of an enormous orderly wall of television screens that fills the frame in"
        " front of her. Every screen shows a coherent moment of her own life and her own face at"
        " different ages, turning her into the spectator of her fabricated existence. A single"
        " screen burns red. Cold blue rim light on her silhouette." + COMMON),
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
    ap.add_argument("--concepts",
                    default="ecran_profil,ecran_face,ecran_oeil,ecran_spectatrice")
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
