#!/usr/bin/env python3
"""
build_catalog.py — trie tous les designs par thème et génère les métadonnées
Redbubble (titre + tags) pour des uploads en masse à mots-clés quasi constants.

Sorties (dossier catalog/) :
  redbubble_all.csv        — 1 ligne par design (id, collection, thème, langue,
                             titre, tags, fichiers dark/light)
  by_theme/<theme>.csv     — même chose mais 1 fichier par thème (upload par lot,
                             tags quasi identiques dans un même fichier)
  SUMMARY.md               — compte par thème et par collection

Usage : python scripts/build_catalog.py
"""
import csv
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "catalog")

# data file -> (collection dir, type)
COLLECTIONS = {
    "trending_100.json": ("trending", "lines"),
    "niches_funny.json": ("niches", "lines"),
    "revendications.json": ("revendications", "lines"),
    "proverbes.json": ("proverbes", "lines"),
    "ironique.json": ("ironique", "lines"),
    "solidaire.json": ("solidaire", "lines"),
    "neuro.json": ("neuro", "lines"),
    "stoner.json": ("stoner", "lines"),
    "punchlines.json": ("punchlines", "lines"),
    "identite.json": ("identite", "lines"),
    "arrow.json": ("arrow", "lines"),
    "anti.json": ("anti", "anti"),
    "heart.json": ("heart", "heart"),
    "corrige.json": ("corrige", "corrige"),
    "warning.json": ("warning", "warning"),
    "formats.json": ("formats", "formats"),
}

LANG_LABEL = {"en": "English", "fr": "French", "es": "Spanish", "de": "German",
              "it": "Italian", "pt": "Portuguese", "xx": ""}

GENERIC = ["funny shirt", "typography", "minimalist", "aesthetic", "gift idea",
           "trendy", "statement tee"]

# thème -> (libellé, tags de base, mots-clés de détection)
THEMES = [
    ("feminism", "Feminist", ["feminist", "feminism", "girl power", "smash patriarchy",
     "women rights", "equal rights", "feminist gift"],
     ["feminist", "féminist", "patriarcat", "patriarchy", "women", "femme", "sororit",
      "girls", "bossy", "sexism", "sexisme", "mon corps", "my body", "she said"]),
    ("lgbtq", "LGBTQ Pride", ["pride", "lgbtq", "queer", "trans rights", "love is love",
     "ally", "rainbow flag"],
     ["pride", "lgbtq", "queer", "trans", "gay", "homophobi", "(wo)men", "(s)he",
      "pronoun", "love is love", "thembo"]),
    ("climate", "Climate & Ecology", ["climate change", "save the planet", "ecology",
     "environment", "climate activist", "earth day", "eco friendly"],
     ["climat", "climate", "planet", "planète", "écolog", "ecolog", "carbon", "co2",
      "pollution", "deforest", "déforest", "greenwash", "anthropocène", "extinction",
      "asteroid", "comète", "earth", "abeille", "bee", "ocean", "océan", "pêche",
      "overfishing"]),
    ("animals", "Animal Rights & Vegan", ["vegan", "animal rights", "vegan gift",
     "save animals", "plant based", "cruelty free", "animal lover"],
     ["vegan", "végan", "corrida", "steak", "cadavre", "élevage", "abattoir", "fourrure",
      "spécisme", "animal", "cruelty", "not food", "leur peau", "cage"]),
    ("antiracism", "Anti-Racism", ["anti racism", "human rights", "social justice",
     "equality", "no racism", "solidarity"],
     ["racis", "racism", "antiracis", "bigot", "facho", "fascis", "xénophob",
      "migrant", "immigrant", "babylon", "babylone"]),
    ("politics", "Activist & Leftist", ["activist", "eat the rich", "anti capitalist",
     "leftist", "protest", "revolution", "socialist", "class war"],
     ["capitalism", "capitalisme", "antifa", "milliardaire", "billionaire", "ultra-rich",
      "eat the rich", "riches", "lobbies", "révolution", "revolution", "resist", "grève",
      "union", "taxe", "tax the rich", "peuple", "insurg", "suppliciés", "pavés",
      "interdire", "impossible", "élites", "elite", "patron", "boss", "système",
      "system", "marre des", "anti", "pour", "against", "tired of", "free of",
      "zone sans", "allergic"]),
    ("mental_health", "Mental Health & Neurodivergent", ["mental health", "neurodivergent",
     "adhd", "autism", "anxiety", "introvert", "self care", "neurospicy"],
     ["adhd", "tdah", "autis", "anxi", "anxious", "introvert", "neuro", "dyslex",
      "dyscalcul", "dyspraxi", "overthink", "surpenseur", "schizophr", "instable",
      "hypersensible", "burn-out", "burnout", "santé mentale", "mental", "stim",
      "spicy", "empath"]),
    ("cats", "Cats", ["cat lover", "cat mom", "cat dad", "cat lady", "crazy cat",
     "kitten", "cat gift"],
     ["cat ", "cat,", "chat", "gato", "gatti", "katzen", "kitten", "cat mom", "cat dad",
      "cat lady", "feral cat", "maman poule"]),
    ("pets", "Pets & Animals Lovers", ["dog mom", "pet lover", "dog dad", "reptile",
     "animal parent", "pet gift"],
     ["dog", "chien", "gecko", "snake", "reptile", "ferret", "axolotl", "bunny",
      "hamster", "parrot", "horse", "frog", "rat dad", "dragon", "perro", "hund"]),
    ("stoner", "Stoner & Festival", ["420", "weed", "stoner", "cannabis", "festival",
     "high vibes", "rasta"],
     ["420", "weed", "stoner", "champi", "brownie", "herbe", "jardinage", "baked",
      "blaze", "high", "rasta", "trip", "festival", "greens", "munchies"]),
    ("work", "Work & Office Humor", ["office humor", "work shirt", "coworker gift",
     "monday", "sarcastic work", "corporate"],
     ["meeting", "réunion", "boss", "patron", "lundi", "monday", "boulot", "overtime",
      "office", "telework", "télétravail", "loyer", "rent", "job", "burnout",
      "quitting", "démission", "surdiplômé", "underpaid", "manager"]),
    ("relationship", "Relationship & Single", ["single", "dating", "anti valentine",
     "divorce", "relationship humor", "couple"],
     ["single", "célibataire", "soltera", "divorced", "taken", "ex", "valentine",
      "unavailable", "couple", "future ex"]),
    ("existential", "Existential & Dark Humor", ["existential", "nihilism", "dark humor",
     "philosophy", "absurd", "deep quote"],
     ["existential", "néant", "nihil", "poussière", "atoms", "void", "vide", "rien n'a",
      "nothing matters", "tout passe", "doomed", "quoi bon", "sers-je", "ouïe-je",
      "cogito", "veni vidi", "tout ça pour ça"]),
    ("solidarity", "Solidarity & Kindness", ["be kind", "you matter", "solidarity",
     "anti bullying", "mental health support", "kindness"],
     ["lonely", "seul", "talk to me", "you matter", "tu comptes", "safe", "harcèlement",
      "harassment", "be kind", "gentil", "kindness", "you're not alone", "tiens bon"]),
    ("humor", "Funny & Sarcastic", ["funny saying", "sarcastic", "sarcasm", "humor",
     "meme shirt", "funny quote", "introvert humor"],
     ["sarcas", "kebab", "mousquetaire", "bof", "nap", "sieste", "coffee", "café",
      "snack", "caffeine", "feral", "menace", "awkward", "grandma", "mamie", "drama"]),
]
THEME_BY_KEY = {t[0]: t for t in THEMES}

COLLECTION_DEFAULT = {
    "neuro": "mental_health", "stoner": "stoner", "solidaire": "solidarity",
    "identite": "humor", "heart": "humor", "warning": "politics",
    "proverbes": "humor", "ironique": "humor", "punchlines": "existential",
    "arrow": "humor", "anti": "politics", "revendications": "politics",
    "corrige": "feminism", "formats": "humor", "niches": "humor", "trending": "humor",
}

STRIP = re.compile(r"[*]")


def clean(s):
    return STRIP.sub("", s).replace("  ", " ").strip()


def text_of(coll_type, e):
    if coll_type == "lines":
        return clean(" ".join(e["lines"]))
    if coll_type == "heart":
        t = f"{e.get('pre','I')} love {clean(e['post'])}"
        if e.get("replacement"):
            t += f" not {clean(e['post'])} but {e['replacement']}"
        return clean(t)
    if coll_type == "corrige":
        return clean(" ".join(e.get("kept", [])) + f" {e['struck']} → {e['replacement']}")
    if coll_type == "warning":
        return clean(e["text"] + (" " + e.get("sub", "") if e.get("sub") else "")) + " kills"
    if coll_type == "anti":
        return clean(e.get("head", "Anti") + " " + " ".join(e["items"][:6]))
    if coll_type == "formats":
        bits = [e.get("head", ""), e.get("title", ""), e.get("text", "")]
        bits += e.get("items", [])
        bits += [r[0] for r in e.get("rows", [])]
        return clean(" ".join(b for b in bits if b))
    return ""


def classify(text, coll, eid):
    hay = (text + " " + eid + " " + coll).lower()
    best = None
    for key, label, tags, kws in THEMES:
        score = sum(1 for k in kws if k in hay)
        if score and (best is None or score > best[1]):
            best = (key, score)
    if best:
        return best[0]
    return COLLECTION_DEFAULT.get(coll, "humor")


def word_tags(text):
    words = re.findall(r"[A-Za-zÀ-ÿ']{4,}", text.lower())
    stop = {"avec", "pour", "dans", "este", "cette", "tout", "mais", "plus", "with",
            "your", "this", "that", "they", "from", "have", "just", "like", "only",
            "sont", "êtes", "nous", "vous", "leur", "être", "fait"}
    seen, out = set(), []
    for w in words:
        w = w.strip("'")
        if len(w) >= 4 and w not in stop and w not in seen:
            seen.add(w); out.append(w)
    return out[:5]


def build():
    os.makedirs(os.path.join(OUT, "by_theme"), exist_ok=True)
    rows = []
    for fn, (coll, ctype) in COLLECTIONS.items():
        path = os.path.join(DATA, fn)
        if not os.path.isfile(path):
            continue
        data = json.load(open(path, encoding="utf-8"))
        for e in data["entries"]:
            eid = e["id"]
            lang = e.get("lang", "")
            text = text_of(ctype, e)
            subniche = e.get("niche", "") or e.get("format", "")
            theme = classify(text + " " + subniche, coll, eid)
            label, base_tags = THEME_BY_KEY[theme][1], THEME_BY_KEY[theme][2]
            ll = LANG_LABEL.get(lang, "")
            title = f"{text} | {label} {('('+ll+') ') if ll else ''}Design".strip()
            extra = [subniche.replace("_", " ")] if subniche else []
            tags = []
            for t in base_tags + word_tags(text) + extra + [coll, label.lower()] + GENERIC:
                t = t.lower().strip()
                if t and t not in tags:
                    tags.append(t)
            rows.append({
                "id": eid, "collection": coll, "theme": theme, "theme_label": label,
                "subniche": subniche, "lang": lang, "title": title[:140],
                "tags": ", ".join(tags[:25]),
                "file_dark": f"produits/{coll}/{eid}__dark.png",
                "file_light": f"produits/{coll}/{eid}__light.png",
            })

    cols = ["id", "collection", "theme", "theme_label", "subniche", "lang", "title",
            "tags", "file_dark", "file_light"]
    rows.sort(key=lambda r: (r["theme"], r["collection"], r["id"]))
    with open(os.path.join(OUT, "redbubble_all.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)

    by = {}
    for r in rows:
        by.setdefault(r["theme"], []).append(r)
    for theme, rs in by.items():
        with open(os.path.join(OUT, "by_theme", f"{theme}.csv"), "w", newline="",
                  encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rs)

    os.makedirs(os.path.join(OUT, "by_collection"), exist_ok=True)
    bycoll = {}
    for r in rows:
        bycoll.setdefault(r["collection"], []).append(r)
    for coll, rs in bycoll.items():
        rs.sort(key=lambda r: (r["subniche"], r["id"]))
        with open(os.path.join(OUT, "by_collection", f"{coll}.csv"), "w", newline="",
                  encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rs)

    with open(os.path.join(OUT, "SUMMARY.md"), "w", encoding="utf-8") as fh:
        fh.write("# Catalogue par thème (prêt Redbubble)\n\n")
        fh.write(f"**{len(rows)} designs** ({len(rows)*2} fichiers dark+light), "
                 f"{len(by)} thèmes.\n\n")
        fh.write("Chaque `by_theme/<theme>.csv` regroupe des designs qui partagent "
                 "quasiment les mêmes tags → upload par lot, mots-clés à peine à "
                 "retoucher.\n\n## Par thème\n\n")
        for theme in sorted(by, key=lambda t: -len(by[t])):
            label = THEME_BY_KEY[theme][1]
            base = ", ".join(THEME_BY_KEY[theme][2])
            fh.write(f"### {label} (`{theme}`) — {len(by[theme])} designs\n")
            fh.write(f"Tags de base : `{base}`\n\n")
        fh.write("\n## Par collection\n\n")
        cc = {}
        for r in rows:
            cc[r["collection"]] = cc.get(r["collection"], 0) + 1
        for c in sorted(cc, key=lambda x: -cc[x]):
            fh.write(f"- **{c}** : {cc[c]} designs\n")

    print(f"{len(rows)} designs, {len(by)} thèmes -> {OUT}")
    for theme in sorted(by, key=lambda t: -len(by[t])):
        print(f"  {theme:16} {len(by[theme])}")


if __name__ == "__main__":
    build()
