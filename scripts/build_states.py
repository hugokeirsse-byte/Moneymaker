#!/usr/bin/env python3
"""
build_states.py — génère les word-shapes des États US depuis data/states/.

Pour chaque État : version COULEUR (1re couleur représentative de _meta.json)
+ version NOIR & BLANC. Patch blanc + bordure, police Anton, 4000 px,
fond transparent.

Usage :
    python scripts/build_states.py                # tous les États
    python scripts/build_states.py texas florida  # une sélection
"""
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
META = json.load(open(os.path.join(ROOT, "data/states/_meta.json"), encoding="utf-8"))
FONT = os.path.join(ROOT, "assets/fonts/Anton.ttf")
OUT = os.path.join(ROOT, "produits/us_states")


def gen(state, colors_arg, suffix):
    name = f"state_{state}_{suffix}"
    cmd = [sys.executable, os.path.join(ROOT, "scripts/gen_wordcloud.py"),
           "--freq-file", os.path.join(ROOT, f"data/states/{state}.json"),
           "--mask", f"usstate:{state}", "--colors", colors_arg,
           "--size", "4000", "--font-path", FONT, "--prefer-horizontal", "0.62",
           "--border", "12", "--fill", "#ffffff", "--out", OUT, "--name", name]
    subprocess.run(cmd, check=True)


def main():
    sel = sys.argv[1:] or list(META.keys())
    for st in sel:
        if st not in META:
            print(f"  (inconnu, ignoré : {st})")
            continue
        rep = META[st]["colors"][0]
        gen(st, rep, "color")
        gen(st, "bw", "bw")
    print(f"\n{len(sel)} états × 2 variantes → {OUT}")


if __name__ == "__main__":
    main()
