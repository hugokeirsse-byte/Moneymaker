#!/usr/bin/env python3
"""
reorganize_produits.py — réorganise produits/ en dossiers classés par thème.
Déplacements au niveau de l'index git (mêmes blobs, aucune image retraitée).
À exécuter sur un runner CI (réseau git fiable), suivi de commit+push.
"""
import re
import subprocess

def ls(path):
    out = subprocess.run(["git", "ls-tree", "-r", "-z", "HEAD", path],
                         capture_output=True, text=True).stdout
    files = []
    for line in out.split("\0"):
        m = re.match(r"\d+ blob ([0-9a-f]+)\t(.+)", line, re.S)
        if m:
            files.append((m.group(1), m.group(2)))
    return files

def theme_of(fname):
    pre = fname.split("/")[-1].split("___")[0]
    if pre.startswith("pride"):
        return "pride"
    if pre.startswith("juneteenth"):
        return "juneteenth"
    if pre.startswith(("fathersday", "fathers_day")):
        return "fete_des_peres/scenes"
    if pre.startswith(("dragonboat", "fete_musique", "midsommar")):
        return "fetes_de_juin"
    return None

moves = []

def remap(src, dst):
    for sha, p in ls(src):
        moves.append((sha, p, p.replace(src, dst, 1)))

remap("produits/worldcup2026_flag_patches_transparent", "produits/coupe_du_monde/drapeaux")
remap("produits/worldcup2026_flag_patches", "produits/coupe_du_monde/drapeaux_sur_feutre")
remap("produits/worldcup2026_flag_hexagon_balls_v2_transparent", "produits/coupe_du_monde/ballons")
remap("produits/worldcup2026_flag_hexagon_balls_v2", "produits/coupe_du_monde/ballons_sur_feutre")
remap("produits/fathers_day_patches_transparent", "produits/fete_des_peres/patchs")
remap("produits/visual_puns_words_patches_transparent", "produits/humour_patchs")
remap("produits/visual_puns_adult_embroidery_transparent", "produits/humour_adulte")
for src in ["produits/events_flood_transparent", "produits/events_june_styles_transparent"]:
    for sha, p in ls(src):
        t = theme_of(p)
        if t:
            moves.append((sha, p, f"produits/{t}/" + p.split("/")[-1]))
tp = {"produits/teepublic/worldcup2026_flag_patches": "produits/teepublic/coupe_du_monde/drapeaux",
      "produits/teepublic/worldcup2026_flag_hexagon_balls": "produits/teepublic/coupe_du_monde/ballons",
      "produits/teepublic/fathers_day_patches": "produits/teepublic/fete_des_peres/patchs",
      "produits/teepublic/visual_puns_words_patches": "produits/teepublic/humour_patchs",
      "produits/teepublic/visual_puns_adult_embroidery": "produits/teepublic/humour_adulte"}
for s, d in tp.items():
    remap(s, d)
for src in ["produits/teepublic/events_flood", "produits/teepublic/events_june_styles"]:
    for sha, p in ls(src):
        t = theme_of(p)
        if t:
            moves.append((sha, p, f"produits/teepublic/{t}/" + p.split("/")[-1]))


seen = {}
for sha, old, new in moves:
    seen.setdefault(new, (sha, old))
obsolete = [p for _, p in ls("produits/worldcup2026_flag_hexagon_balls") if "_v2" not in p]
old_paths = sorted({old for _, old, _ in moves} | set(obsolete))
print(f"{len(old_paths)} retraits, {len(seen)} ajouts")

# ── commit via l'API GitHub (zéro pack local : un clone partiel re-télécharge
#    des Go d'objets au push ; l'API référence les blobs existants côté serveur)
import json
import os
import time
import urllib.request

TOKEN = os.environ["GITHUB_TOKEN"]
REPO = os.environ.get("GITHUB_REPOSITORY", "hugokeirsse-byte/Moneymaker")
BRANCH = os.environ.get("GITHUB_REF_NAME") or subprocess.run(
    ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True).stdout.strip()
API = f"https://api.github.com/repos/{REPO}"

def call(method, url, payload=None, retries=4):
    for k in range(retries):
        req = urllib.request.Request(url, method=method,
            data=json.dumps(payload).encode() if payload is not None else None,
            headers={"Authorization": f"Bearer {TOKEN}",
                     "Accept": "application/vnd.github+json",
                     "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except urllib.error.HTTPError as exc:
            if exc.code in (502, 503, 504) and k < retries - 1:
                print(f"{exc.code} sur {url}, retry {k+1}…")
                time.sleep(3 * (k + 1))
                continue
            raise

entries = ([{"path": new, "mode": "100644", "type": "blob", "sha": sha}
            for new, (sha, _) in seen.items()]
           + [{"path": old, "mode": "100644", "type": "blob", "sha": None}
              for old in old_paths])

for attempt in range(4):
    head_ref = call("GET", f"{API}/git/ref/heads/{BRANCH}")
    head_sha = head_ref["object"]["sha"]
    head_commit = call("GET", f"{API}/git/commits/{head_sha}")
    tree = call("POST", f"{API}/git/trees",
                {"base_tree": head_commit["tree"]["sha"], "tree": entries})
    commit = call("POST", f"{API}/git/commits",
                  {"message": "produits: réorganisation en dossiers classés par thème",
                   "tree": tree["sha"], "parents": [head_sha]})
    try:
        call("PATCH", f"{API}/git/refs/heads/{BRANCH}",
             {"sha": commit["sha"], "force": False})
        print(f"commit API publié : {commit['sha'][:9]}")
        break
    except Exception as exc:  # noqa: BLE001 — la branche a avancé, on recommence
        print(f"ref avancée ({exc}), nouvelle tentative…")
        time.sleep(2 ** (attempt + 1))
else:
    raise SystemExit("impossible de publier après 4 tentatives")
