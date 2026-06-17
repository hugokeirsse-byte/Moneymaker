#!/usr/bin/env python3
"""
cleanup_pride_strays.py — retire les slogans dupliqués à la racine de
produits/pride/.

Une passe de détourage lancée par erreur avec src == dst a aplati les
sous-dossiers slogans/ et slogans_sur_feutre/ : 16 fichiers de slogans se sont
retrouvés copiés à la racine de produits/pride/. Les bons exemplaires restent
dans produits/pride/slogans/. On supprime uniquement les fichiers .png situés
directement dans produits/pride/ dont le nom ne contient pas « ___ » (les 56
designs portent tous ce séparateur ; les slogans non). Suppression pure via
l'API Git de GitHub (un seul commit), aucun blob retraité.
"""
import json
import os
import urllib.request

API = "https://api.github.com/repos/" + os.environ["GITHUB_REPOSITORY"]
BR = os.environ.get("BRANCH", "claude/trend-niche-discovery-i2lkgo")
TOKEN = os.environ["GITHUB_TOKEN"]


def call(method, url, payload=None):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {TOKEN}")
    req.add_header("Accept", "application/vnd.github+json")
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def main():
    ref = call("GET", f"{API}/git/ref/heads/{BR}")
    head = ref["object"]["sha"]
    commit = call("GET", f"{API}/git/commits/{head}")
    base_tree = commit["tree"]["sha"]
    tree = call("GET", f"{API}/git/trees/{base_tree}?recursive=1")

    strays = []
    for e in tree["tree"]:
        p = e["path"]
        if e["type"] != "blob":
            continue
        if not p.startswith("produits/pride/"):
            continue
        rest = p[len("produits/pride/"):]
        if "/" in rest:            # dans un sous-dossier (slogans/, etc.) : on garde
            continue
        if p.lower().endswith(".png") and "___" not in rest:
            strays.append(p)

    if not strays:
        print("Aucun slogan égaré à la racine de produits/pride/.")
        return
    print(f"{len(strays)} fichiers à retirer :")
    for p in strays:
        print(" -", p)

    new_tree = call("POST", f"{API}/git/trees", {
        "base_tree": base_tree,
        "tree": [{"path": p, "mode": "100644", "type": "blob", "sha": None} for p in strays],
    })
    new_commit = call("POST", f"{API}/git/commits", {
        "message": "produits(pride): retire 16 slogans dupliqués à la racine "
                   "(les bons restent dans pride/slogans/)",
        "tree": new_tree["sha"],
        "parents": [head],
    })
    call("PATCH", f"{API}/git/refs/heads/{BR}", {"sha": new_commit["sha"]})
    print("commit :", new_commit["sha"][:9])


if __name__ == "__main__":
    main()
