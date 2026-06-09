"""
Récupère les images déjà upscalées dans un artefact d'un run interrompu.

Contexte : un run upscale-fix a été coupé par le timeout AVANT l'étape commit.
Les images traitées sont dans l'artefact GitHub (téléchargé côté runner où le
réseau passe). On compare chaque image de l'artefact à la version actuelle du
repo : si elle diffère (par hash), c'est qu'elle a été upscalée → on la récupère.

Aucun nouvel appel Runware = zéro coût.

Usage (dans le workflow, après actions/download-artifact) :
    python -m trend_discovery.generators.recover_artifact --artifact-dir ./_recovered
"""
from __future__ import annotations

import argparse
import glob
import hashlib
import json
import os
import shutil

MANIFEST_PATH = os.path.join("reports", "upscaled_manifest.json")


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _load_manifest() -> set:
    try:
        with open(MANIFEST_PATH) as f:
            return set(json.load(f).get("done", []))
    except Exception:
        return set()


def _save_manifest(done: set) -> None:
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump({"done": sorted(done)}, f, indent=2)


def recover(artifact_dir: str, subdirs: list) -> int:
    """
    Pour chaque image de l'artefact qui diffère de la version repo,
    la copie dans le repo et l'ajoute au manifeste.

    Returns: nombre d'images récupérées.
    """
    done = _load_manifest()
    recovered = 0

    for sub in subdirs:
        art_sub = os.path.join(artifact_dir, sub)
        if not os.path.isdir(art_sub):
            print(f"  (absent de l'artefact : {sub})")
            continue

        for art_path in sorted(glob.glob(os.path.join(art_sub, "*.png"))):
            fname = os.path.basename(art_path)
            repo_path = os.path.join(sub, fname)
            manifest_key = "./" + repo_path.replace("\\", "/")

            if not os.path.exists(repo_path):
                continue  # fichier inconnu du repo, on ignore

            try:
                if _sha256(art_path) == _sha256(repo_path):
                    continue  # identique = pas upscalé dans ce run
            except Exception as exc:
                print(f"  [skip] {fname}: {exc}")
                continue

            # Diffère → version upscalée, on la récupère
            shutil.copy2(art_path, repo_path)
            done.add(manifest_key)
            recovered += 1
            size_mb = os.path.getsize(repo_path) / 1024 / 1024
            print(f"  ♻️  récupéré {fname} ({size_mb:.1f} MB)")

    _save_manifest(done)
    print(f"\n✅ {recovered} image(s) récupérée(s) depuis l'artefact — manifeste : {len(done)} faites")
    return recovered


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Récupère les upscales d'un artefact de run interrompu")
    parser.add_argument("--artifact-dir", required=True, help="Dossier où l'artefact est extrait")
    parser.add_argument(
        "--subdirs",
        default="output/spoonflower,output/uploads/base",
        help="Sous-dossiers à comparer (virgule)",
    )
    args = parser.parse_args()

    subdirs = [s.strip() for s in args.subdirs.split(",") if s.strip()]
    recover(args.artifact_dir, subdirs)
