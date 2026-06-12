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

# doublons fixes : drapeaux/ballons "_sur_feutre" mappés deux fois (transparent
# remap a déjà pris les non-transparents ?) — dédoublonnage par chemin cible
seen = {}
for sha, old, new in moves:
    seen.setdefault(new, (sha, old))
obsolete = [p for _, p in ls("produits/worldcup2026_flag_hexagon_balls") if "_v2" not in p]
old_paths = sorted({old for _, old, _ in moves} | set(obsolete))

print(f"{len(old_paths)} retraits, {len(seen)} ajouts")
with open("/tmp/rm.nul", "w") as fh:
    fh.write("\0".join(old_paths))
subprocess.run(["git", "rm", "-q", "--cached", "--sparse",
                "--pathspec-from-file=/tmp/rm.nul", "--pathspec-file-nul"], check=True)
info = "".join(f"100644 {sha}\t{new}\0" for new, (sha, _) in seen.items())
subprocess.run(["git", "update-index", "--add", "-z", "--index-info"],
               input=info, text=True, check=True)
print("index réorganisé — prêt à committer")
