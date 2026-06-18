#!/usr/bin/env python3
"""
gen_listings_gemini.py — métadonnées POD générées par Gemini (titres, descriptions,
mots-clés) pour Redbubble / TeePublic / Amazon Merch / Etsy.

But : déléguer la rédaction SEO à Gemini (clé GEMINI_API_KEY) plutôt que de la
coder à la main. Sortie : un CSV par groupe sous reports/listings/, colonnes
fichier,titre_fr,titre_en,description,mots_cles — directement importable.

Sources de designs :
  --corpus data/typo_collection.json   (les phrases : contexte = texte+langue)
  --produits                           (scan git ls-tree produits/ : contexte = thème déduit du chemin)

Aucune marque déposée dans les tags (consigne donnée au modèle).

Usage :
    GEMINI_API_KEY=... python scripts/gen_listings_gemini.py --corpus data/typo_collection.json
    GEMINI_API_KEY=... python scripts/gen_listings_gemini.py --produits
"""
import argparse
import csv
import json
import os
import re
import subprocess
import sys

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_client = None
_models_cache = None


def get_client():
    global _client
    if _client is not None:
        return _client
    from google import genai
    _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def ranked_models():
    global _models_cache
    if _models_cache:
        return _models_cache
    c = get_client()
    found = []
    try:
        for m in c.models.list():
            n = (getattr(m, "name", "") or "").replace("models/", "")
            if n and "flash" in n and not any(x in n for x in
                    ("image", "tts", "audio", "embedding", "vision", "live")):
                found.append(n)
    except Exception as e:  # noqa: BLE001
        print(f"[gemini] list models: {e}", file=sys.stderr)
    def score(m):
        s = 0.0
        v = re.search(r"(\d+\.\d+)", m)
        if v: s += float(v.group(1)) * 10
        if "lite" in m: s -= 2
        if "latest" in m: s += 1.5
        if "preview" in m or "exp" in m: s -= 1
        return s
    ranked = sorted(set(found), key=score, reverse=True)
    for fb in ("gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash", "gemini-2.5-flash-lite"):
        if fb not in ranked:
            ranked.append(fb)
    _models_cache = ranked
    return ranked


def call_json(prompt):
    """Appelle Gemini, renvoie le 1er tableau JSON trouvé (ou [])."""
    from google.genai import types
    c = get_client()
    for model in ranked_models()[:4]:
        try:
            cfg = types.GenerateContentConfig(
                temperature=0.7, response_mime_type="application/json")
            r = c.models.generate_content(model=model, contents=prompt, config=cfg)
            txt = r.text or ""
            arr = extract_json(txt)
            if arr:
                print(f"[gemini] OK via {model}")
                return arr
        except Exception as e:  # noqa: BLE001
            print(f"[gemini] {model} échec: {str(e)[:140]}", file=sys.stderr)
    return []


def extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        d = json.loads(text)
        return d if isinstance(d, list) else d.get("designs") or d.get("items") or []
    except Exception:  # noqa: BLE001
        m = re.search(r"\[.*\]", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:  # noqa: BLE001
                return []
    return []


PROMPT_HEAD = """You are a print-on-demand SEO expert for Redbubble, TeePublic, \
Amazon Merch and Etsy. For EACH design below, write optimized, sales-driving \
metadata. Constraints:
- title_en: <= 60 chars, catchy and keyword-rich (no ALL CAPS spam).
- title_fr: French version, <= 60 chars.
- description: 2-3 sentences, French, naturally mentions products (t-shirt, \
sticker, mug, tote bag, poster) and the vibe; no hashtags.
- tags: 22-28 items, a mix of English and French search keywords, lowercase, \
each 1-3 words, ordered most relevant first, NO trademarks, NO brand names, \
NO celebrity names. Include audience/occasion/style keywords.
Return ONLY a JSON array; one object per design with keys: \
id, title_en, title_fr, description, tags (array of strings).

DESIGNS:
"""


def batched(seq, n):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


def write_csv(path, rows):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["fichier", "titre_fr", "titre_en", "description", "mots_cles"])
        w.writeheader()
        w.writerows(rows)
    print(f"{path} : {len(rows)} listings")


def process(targets, out_csv):
    """targets: liste de dicts {id, context, lang}. Écrit out_csv."""
    by_id = {t["id"]: t for t in targets}
    rows = []
    for batch in batched(targets, 10):
        payload = [{"id": t["id"], "design": t["context"], "language": t["lang"]} for t in batch]
        prompt = PROMPT_HEAD + json.dumps(payload, ensure_ascii=False, indent=1)
        res = call_json(prompt)
        got = {r.get("id"): r for r in res if isinstance(r, dict)}
        for t in batch:
            r = got.get(t["id"], {})
            tags = r.get("tags") or []
            if isinstance(tags, str):
                tags = [x.strip() for x in tags.split(",") if x.strip()]
            rows.append({
                "fichier": t["id"],
                "titre_fr": (r.get("title_fr") or "").strip(),
                "titre_en": (r.get("title_en") or "").strip(),
                "description": (r.get("description") or "").strip(),
                "mots_cles": ", ".join(tags[:28]),
            })
    write_csv(out_csv, rows)
    return rows


def from_corpus(path):
    data = json.load(open(path, encoding="utf-8"))
    parts = {
        "p1": "vintage dictionary / aesthetic typographic quote with public-domain art",
        "p2": "digital burnout / post-AI humour typographic statement",
        "p3": "selective introversion humour typographic statement",
        "p4": "fake 'untranslatable word' dictionary-style design",
        "p5": "corporate cynicism / economic realism humour statement",
        "p6": "chaos / sarcasm modern-aesthetic statement",
    }
    return [{"id": it["id"],
             "context": f'Typographic POD design. Phrase: "{it["text"]}". '
                        f'Theme: {parts.get(it["part"], "humour")}. '
                        f'Paired with a vintage public-domain illustration.',
             "lang": it["lang"]} for it in data["items"]]


THEME_CTX = {
    "coupe_du_monde/drapeaux": ("embroidered national flag patch, soccer 2026 supporter", "fr"),
    "coupe_du_monde/ballons": ("embroidered soccer ball patch with a national flag, 2026", "fr"),
    "fete_des_peres/patchs": ("funny embroidered patch for Father's Day", "fr"),
    "fete_des_peres/scenes": ("tender father-and-child illustration for Father's Day", "fr"),
    "fete_des_peres/slogans": ("funny Father's Day slogan embroidered patch", "fr"),
    "pride": ("LGBTQ pride rainbow design", "fr"),
    "pride/slogans": ("LGBTQ pride slogan embroidered patch, pride all year", "en"),
    "juneteenth": ("Juneteenth freedom celebration design", "en"),
    "fetes_de_juin": ("June seasonal festival design", "fr"),
    "humour_patchs": ("funny embroidered pun patch", "fr"),
    "humour_adulte": ("adult humour embroidered patch", "fr"),
}


def from_produits():
    out = subprocess.run(["git", "ls-tree", "-r", "--name-only", "HEAD", "produits/"],
                         capture_output=True, text=True).stdout.split("\n")
    targets = []
    for p in out:
        if not p.lower().endswith(".png") or "/thumbnails/" in p or "teepublic" in p:
            continue
        rel = p[len("produits/"):]
        theme = None
        for key in sorted(THEME_CTX, key=len, reverse=True):
            if rel.startswith(key + "/"):
                theme = key
                break
        if not theme:
            continue
        ctx, lang = THEME_CTX[theme]
        name = os.path.splitext(os.path.basename(p))[0]
        targets.append({"id": p, "context": f"{ctx}. design id: {name}", "lang": lang,
                        "_folder": theme})
    return targets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="")
    ap.add_argument("--produits", action="store_true")
    args = ap.parse_args()
    if not GEMINI_API_KEY:
        print("ERREUR: GEMINI_API_KEY manquant", file=sys.stderr)
        return 1

    if args.corpus:
        targets = from_corpus(args.corpus)
        process(targets, "reports/listings/typo_collection_gemini.csv")
    if args.produits:
        targets = from_produits()
        # un CSV par dossier thématique
        from collections import defaultdict
        groups = defaultdict(list)
        for t in targets:
            groups[t["_folder"]].append(t)
        for folder, items in groups.items():
            safe = folder.replace("/", "__")
            process(items, f"reports/listings/produits__{safe}_gemini.csv")
    if not args.corpus and not args.produits:
        print("Rien à faire : --corpus <json> et/ou --produits")
    return 0


if __name__ == "__main__":
    sys.exit(main())
