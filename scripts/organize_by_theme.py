#!/usr/bin/env python3
"""
organize_by_theme.py — range tous les designs par CATÉGORIE sur ta machine.

À lancer UNE fois après `git pull`. Lit catalog/by_theme/*.csv et copie les
images PNG correspondantes (depuis produits/) dans :

    catalog/by_theme_images/<theme>/images/*.png
    catalog/by_theme_images/<theme>/<theme>_a-copier-coller.txt   (les fiches)

→ tu obtiens un dossier par catégorie, prêt pour l'upload, sans rien télécharger
par morceaux.

Usage : python scripts/organize_by_theme.py
"""
import csv
import os
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BYTH = os.path.join(ROOT, "catalog", "by_theme")
ENC = os.path.join(ROOT, "catalog", "encarts")
OUT = os.path.join(ROOT, "catalog", "by_theme_images")


def main():
    if not os.path.isdir(BYTH):
        print("catalog/by_theme manquant — lance d'abord scripts/build_catalog.py")
        return
    total, miss = 0, 0
    for fn in sorted(os.listdir(BYTH)):
        if not fn.endswith(".csv"):
            continue
        theme = fn[:-4]
        dst = os.path.join(OUT, theme, "images")
        os.makedirs(dst, exist_ok=True)
        enc = os.path.join(ENC, f"{theme}.txt")
        if os.path.isfile(enc):
            shutil.copy2(enc, os.path.join(OUT, theme, f"{theme}_a-copier-coller.txt"))
        n, m = 0, 0
        for r in csv.DictReader(open(os.path.join(BYTH, fn), encoding="utf-8")):
            for f in r["files"].split(" | "):
                f = f.strip()
                src = os.path.join(ROOT, f)
                if os.path.isfile(src):
                    shutil.copy2(src, os.path.join(dst, os.path.basename(f)))
                    n += 1
                else:
                    m += 1
        total += n; miss += m
        print(f"{theme:16} {n} images copiées" + (f"  ({m} absentes)" if m else ""))
    print(f"\nTOTAL : {total} images rangées dans catalog/by_theme_images/")
    if miss:
        print(f"⚠ {miss} absentes en local — fais un clone complet "
              "(`git sparse-checkout disable`) si tu veux toutes les images.")


if __name__ == "__main__":
    main()
