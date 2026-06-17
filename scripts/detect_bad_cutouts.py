#!/usr/bin/env python3
"""
detect_bad_cutouts.py — repère les détourages IA qui ont « mangé » le centre.

Un masque ISNet trop agressif laisse soit un TROU transparent au milieu du
sujet (alpha=0 en plein centre), soit ne conserve qu'une fraction minime de
l'image. On scanne les PNG RGBA et on signale :
  - trou central : transparence > `hole_tol` dans le disque central (r<0.45)
  - sujet trop rogné : surface opaque < `min_kept` de l'image

Les fichiers signalés sont ceux à repasser en découpe ronde (`disc`), qui
n'enlève jamais un pixel intérieur.

Usage :
    python scripts/detect_bad_cutouts.py <dossier_transparent> [<dossier2> ...]
Sortie : liste des suspects (un par ligne) + récap, code 0 toujours.
"""
import os
import sys

import numpy as np
from PIL import Image


def is_bad(path: str, hole_tol: float = 0.18, min_kept: float = 0.12) -> tuple[bool, str]:
    img = Image.open(path)
    if img.mode != "RGBA":
        return False, "pas de canal alpha (opaque)"
    a = np.array(img.split()[-1]).astype(float) / 255.0
    h, w = a.shape
    kept = a.mean()
    if kept < min_kept:
        return True, f"sujet trop rogné ({kept*100:.0f}% conservé)"
    yy, xx = np.ogrid[:h, :w]
    dist = np.sqrt((yy - h / 2) ** 2 + (xx - w / 2) ** 2)
    core = dist < min(h, w) / 2 * 0.45  # disque central ~45% du rayon
    core_transp = (a[core] < 0.5).mean()
    if core_transp > hole_tol:
        return True, f"trou au centre ({core_transp*100:.0f}% transparent au cœur)"
    return False, f"ok ({kept*100:.0f}% conservé, cœur plein)"


def main() -> int:
    dirs = sys.argv[1:] or ["."]
    suspects, total = [], 0
    for d in dirs:
        for root, sub, files in os.walk(d):
            sub[:] = [x for x in sub if x != "thumbnails"]
            for f in sorted(files):
                if not f.lower().endswith(".png"):
                    continue
                total += 1
                p = os.path.join(root, f)
                try:
                    bad, why = is_bad(p)
                except Exception as exc:  # noqa: BLE001
                    bad, why = True, f"illisible: {exc}"
                if bad:
                    suspects.append((p, why))
                    print(f"SUSPECT  {p}  →  {why}")
    print(f"\n{len(suspects)}/{total} détourages à reprendre en disque")
    return 0


if __name__ == "__main__":
    sys.exit(main())
