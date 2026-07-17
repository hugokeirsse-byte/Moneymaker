#!/usr/bin/env python3
"""
Édite une image existante via FLUX Kontext (Runware) selon une instruction,
en ne modifiant QUE ce qui est demandé (le reste de l'image est préservé).

Entrée : --in <png>  |  Sortie : --out <png>  |  Instruction : --prompt "..."

FLUX Kontext n'accepte qu'une liste fixe de dimensions : on snappe donc sur
celle dont le ratio est le plus proche de l'image source. L'image est envoyée
en base64 (data URI) comme referenceImage ; la composition finale ré-upscale.

Nécessite RUNWARE_API_KEY.
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
import time
import uuid
from io import BytesIO

import requests
from PIL import Image

RUNWARE_URL = "https://api.runware.ai/v1"

# Modèles d'édition, du plus capable au repli.
MODEL_CHAIN = [
    "bfl:4@1",  # FLUX.1 Kontext [max]
    "bfl:3@1",  # FLUX.1 Kontext [pro]
]
_ov = os.getenv("RUNWARE_KONTEXT_MODEL", "").strip()
if _ov:
    MODEL_CHAIN = [_ov] + [m for m in MODEL_CHAIN if m != _ov]

# Dimensions acceptées par FLUX Kontext (largeur, hauteur).
KONTEXT_DIMS = [
    (1568, 672), (1392, 752), (1184, 880), (1248, 832), (1024, 1024),
    (832, 1248), (880, 1184), (752, 1392), (672, 1568),
]


def snap_dims(w, h):
    """Choisit la dimension Kontext dont le ratio est le plus proche."""
    r = w / float(h)
    return min(KONTEXT_DIMS, key=lambda d: abs(d[0] / float(d[1]) - r))


def post(session, tasks, timeout=180):
    r = session.post(RUNWARE_URL, json=tasks, timeout=timeout)
    if r.status_code >= 400:
        print(f"[runware] HTTP {r.status_code}: {r.text[:400]}", file=sys.stderr)
        r.raise_for_status()
    return r.json()


def find(resp, uid):
    data = (resp or {}).get("data", [])
    for it in data:
        if it.get("taskUUID") == uid:
            return it
    for it in data:
        if it.get("taskType") == "imageInference":
            return it
    return None


def edit(session, data_uri, prompt, w, h, model):
    uid = str(uuid.uuid4())
    task = {
        "taskType": "imageInference", "taskUUID": uid, "model": model,
        "positivePrompt": prompt, "referenceImages": [data_uri],
        "width": w, "height": h, "numberResults": 1,
        "outputType": ["URL"], "outputFormat": "PNG", "includeCost": True,
    }
    resp = post(session, [task])
    res = find(resp, uid)
    if not res or not res.get("imageURL"):
        raise RuntimeError(f"édition échouée: {res}")
    return res["imageURL"], res.get("cost")


def download(url, path, timeout=120):
    r = requests.get(url, timeout=timeout)
    r.raise_for_status()
    with open(path, "wb") as f:
        f.write(r.content)
    return len(r.content)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", dest="out", required=True)
    ap.add_argument("--prompt", required=True)
    a = ap.parse_args()

    key = os.getenv("RUNWARE_API_KEY", "")
    if not key:
        print("RUNWARE_API_KEY absente — impossible d'éditer.", file=sys.stderr)
        sys.exit(2)

    im = Image.open(a.inp).convert("RGB")
    tw, th = snap_dims(im.width, im.height)
    im = im.resize((tw, th), Image.LANCZOS)
    buf = BytesIO()
    im.save(buf, "PNG")
    data_uri = "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

    session = requests.Session()
    session.headers.update({"Authorization": f"Bearer {key}",
                            "Content-Type": "application/json"})

    print(f"Édition Kontext {tw}x{th} — chaîne: {' → '.join(MODEL_CHAIN)}")
    print(f"Instruction: {a.prompt}")
    last = None
    for model in MODEL_CHAIN:
        for attempt in range(2):
            try:
                if attempt:
                    time.sleep(2 ** attempt)
                url, cost = edit(session, data_uri, a.prompt, tw, th, model)
                n = download(url, a.out)
                print(f"OK {a.out} ({n // 1024} Ko, modèle={model}, cost={cost})")
                sys.exit(0)
            except Exception as exc:
                print(f"[{model}] tentative {attempt+1} échouée: {exc}", file=sys.stderr)
                last = exc
    print(f"ÉCHEC édition définitif: {last}", file=sys.stderr)
    sys.exit(1)


if __name__ == "__main__":
    main()
