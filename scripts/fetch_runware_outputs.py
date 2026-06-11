#!/usr/bin/env python3
"""
fetch_runware_outputs.py — récupère des images finales depuis leurs URLs Runware.

Cas d'usage : un run de génération a réussi côté Runware (URLs dans les logs)
mais la sauvegarde locale a échoué. On retélécharge les images SANS regénérer
(0 € de génération), on vérifie la qualité réelle, on packe en PNG 300 DPI.

Usage:
    python scripts/fetch_runware_outputs.py --mapping data/recovery/xxx_urls.json \
        --dest produits/worldcup2026_flag_patches [--min-px 4000]

Le mapping est un JSON {"nom": "https://im.runware.ai/...png", ...}.
Toute image plus petite que --min-px est REFUSÉE (pas d'upscale factice).
"""
import argparse
import io
import json
import os
import sys
import time

import requests
from PIL import Image


def fetch(url: str, retries: int = 3, timeout: int = 120) -> bytes:
    last = None
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            return r.content
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError(f"téléchargement échoué après {retries} essais: {last}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mapping", required=True)
    ap.add_argument("--dest", required=True)
    ap.add_argument("--min-px", type=int, default=4000)
    args = ap.parse_args()

    mapping = json.load(open(args.mapping, encoding="utf-8"))
    os.makedirs(args.dest, exist_ok=True)

    ok, ko = 0, []
    for name, url in mapping.items():
        out = os.path.join(args.dest, f"{name}.png")
        if os.path.exists(out):
            print(f"= {name}: déjà présent, ignoré")
            ok += 1
            continue
        try:
            raw = fetch(url)
            img = Image.open(io.BytesIO(raw))
            w, h = img.size
            if min(w, h) < args.min_px:
                ko.append((name, f"résolution {w}x{h} < {args.min_px}px — refusée (pas d'agrandissement factice)"))
                continue
            if img.mode != "RGB":
                img = img.convert("RGB")
            img.save(out, format="PNG", dpi=(300, 300), optimize=False)
            print(f"+ {name}: {w}x{h} 300DPI → {out}")
            ok += 1
        except Exception as exc:  # noqa: BLE001
            ko.append((name, str(exc)))

    print(f"\n{ok}/{len(mapping)} images récupérées → {args.dest}")
    for name, err in ko:
        print(f"  ❌ {name}: {err}")
    return 0 if not ko else 1


if __name__ == "__main__":
    sys.exit(main())
