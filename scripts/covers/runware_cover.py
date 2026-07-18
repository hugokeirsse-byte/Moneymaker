#!/usr/bin/env python3
"""
Génère les images d'art (face) des concepts de couverture « CYCLE 404 »
via Runware, puis upscale IA (best-effort). Sauvegarde des PNG dans --out.

Qualité maximale : essaie d'abord un modèle photo premium (FLUX 1.1 Pro,
puis FLUX.1 Pro) et retombe automatiquement sur FLUX.1 Dev si le compte n'y
a pas accès. L'upscale est best-effort : si le service Runware expire, on
conserve l'image générée (pas d'échec du run).

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
    "plateau_salon": (
        "Dystopian psychological thriller book cover, cinematic photograph. A warm, perfect"
        " provincial living room at night — old stone walls, a lit table lamp, framed family"
        " photographs, a worn armchair — but the entire back wall of the room is a theatrical set"
        " flat that stops in mid-air like stage scenery, revealing behind it a vast dark film"
        " soundstage: steel scaffolding, a professional camera on a crane, thick cables coiled on"
        " the floor, and the silhouettes of a hidden film crew quietly watching. One small red"
        " recording light glows in the darkness. The cosy room is the only warmly lit element; the"
        " studio behind is cold and immense. Photorealistic, cinematic teal-and-amber grade,"
        " volumetric light, fine film grain, unsettling. Dark uncluttered upper area reserved for"
        " the title. No text, no letters, no logo. Vertical 5:8."),
    "fils_marionnette": (
        "Dystopian psychological thriller book cover, cinematic photograph. A woman in a pale"
        " dress stands alone in the middle of the empty main street of a quiet, slightly too-"
        "perfect provincial town at dusk, seen from a low three-quarter angle. From her shoulders,"
        " wrists and head rise thin, almost invisible marionette strings that climb high and"
        " vanish into the dark sky above, where a faint wooden control cross is barely suggested"
        " in shadow. The town is immaculate, symmetrical and deserted, unnaturally staged and"
        " still. One tiny red light glows on a distant rooftop. Photorealistic, muted cold palette"
        " with a single red accent, soft volumetric dusk light, fine film grain, eerie and"
        " melancholic. Dark uncluttered sky in the upper area reserved for the title. No text, no"
        " letters, no logo. Vertical 5:8."),
    # v3 — blouse d'hôpital + fils FUSIONNÉS à la peau et aux vêtements, ciel nuageux dégagé.
    "marionnette_hopital": (
        "Dystopian psychological thriller book cover, cinematic photograph. A woman seen from"
        " behind, standing alone in the exact middle of the empty main street of a quiet, too-"
        "perfect symmetrical provincial suburb at cold winter dusk, thin snow on the verges, low"
        " three-quarter angle. Cold desaturated STEEL-BLUE and slate-grey palette (not green, not"
        " teal). She is clearly a HOSPITAL PATIENT: a plain pale blue-grey thin wrinkled hospital"
        " gown open at the back, a white hospital identification wristband on her wrist, barefoot"
        " on the cold asphalt, an amnesiac patient. Thin pale marionette strings EMERGE SEAMLESSLY"
        " FROM HER BODY — they grow directly out of the skin of her shoulders, her upper back, the"
        " backs of her hands and the crown of her head, and out of the fabric of her gown, with no"
        " visible knots or hooks, as if the strings are fused into her skin and clothes; the"
        " strings then rise straight up and dissolve softly into the overcast cloudy sky. Faint,"
        " thin, barely visible pale strings also descend from the sky onto the rooftops of the"
        " identical houses on both sides. Two tiny red lights glow far down the street. A soft band"
        " of pale grey clouds fills the upper third of the sky, kept relatively open and"
        " uncluttered for a title. Soft volumetric dusk light, fine film grain, eerie and"
        " melancholic. No text, no letters, no logo. Vertical 5:8."),
    "mur_enfants": (
        "Dystopian psychological thriller book cover, cinematic photograph. Intimate close shot of"
        " a woman in profile pressing her cheek and open palm against an old flowered wallpaper"
        " wall inside a stone house, eyes closed, listening intently. Through fine cracks and a"
        " peeling corner of the wallpaper, warm golden light escapes and the faint ghostly"
        " silhouettes of two small children playing are barely visible, as if trapped inside the"
        " wall; behind the peeled strip the wall is revealed to be a painted stage backdrop on"
        " plywood. Melancholic and uncanny, warm amber light against cold blue shadow, one small"
        " red glow deep inside a crack. Photorealistic, real skin texture, fine film grain. Dark"
        " uncluttered upper area reserved for the title. No text, no letters, no logo. Vertical"
        " 5:8."),
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
