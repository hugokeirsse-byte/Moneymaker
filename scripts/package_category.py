#!/usr/bin/env python3
"""
package_category.py — construit un paquet ZIP par catégorie : les images PNG du
thème + le CSV (titre/description/tags). Les images sont extraites de git (même
si absentes du sparse-checkout). Découpe en plusieurs parts si > maxmb.

Usage :
    python scripts/package_category.py cats --out /tmp/pkg [--dark] [--maxmb 90]
"""
import argparse
import csv
import os
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def git_blob(path):
    r = subprocess.run(["git", "show", f"HEAD:{path}"], cwd=ROOT, capture_output=True)
    return r.stdout if r.returncode == 0 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("theme")
    ap.add_argument("--out", default="/tmp/pkg")
    ap.add_argument("--dark", action="store_true", help="variantes __dark uniquement")
    ap.add_argument("--maxmb", type=int, default=90)
    args = ap.parse_args()

    csv_path = os.path.join(ROOT, "catalog", "by_theme", f"{args.theme}.csv")
    txt_path = os.path.join(ROOT, "catalog", "encarts", f"{args.theme}.txt")
    if not os.path.isfile(csv_path):
        print("introuvable:", csv_path); sys.exit(1)
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))

    files = []
    for r in rows:
        for f in r["files"].split(" | "):
            f = f.strip()
            if not f:
                continue
            if args.dark and "__" in f and "__dark" not in f:
                continue
            files.append(f)

    os.makedirs(args.out, exist_ok=True)
    cap = args.maxmb * 1024 * 1024
    part, cur, written = 1, 0, []
    zips = []

    def open_zip(n):
        p = os.path.join(args.out, f"{args.theme}_part{n}.zip")
        z = zipfile.ZipFile(p, "w", zipfile.ZIP_STORED)
        # encart lisible (prêt à copier-coller) en priorité, CSV en bonus
        if os.path.isfile(txt_path):
            z.writestr(f"{args.theme}_a-copier-coller.txt", open(txt_path, "rb").read())
        z.writestr(f"{args.theme}.csv", open(csv_path, "rb").read())
        return p, z

    p, z = open_zip(part)
    miss = 0
    for f in files:
        blob = git_blob(f)
        if blob is None:
            miss += 1
            continue
        if cur and cur + len(blob) > cap:
            z.close(); zips.append((p, cur, len(written)))
            part += 1; cur = 0; written = []
            p, z = open_zip(part)
        arc = "images/" + os.path.basename(f)
        z.writestr(arc, blob)
        cur += len(blob); written.append(f)
    z.close(); zips.append((p, cur, len(written)))

    tot = sum(s for _, s, _ in zips)
    print(f"{args.theme}: {len(files)} fichiers visés, {miss} manquants, "
          f"{tot//1024//1024} MB, {len(zips)} part(s)")
    for p, s, n in zips:
        print(f"  {p}  ({s//1024//1024} MB, {n} images)")


if __name__ == "__main__":
    main()
