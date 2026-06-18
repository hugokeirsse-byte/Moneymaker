#!/usr/bin/env python3
"""
gen_niche_jokes_gemini.py — recherche de niches + blagues + mots-clés par Gemini,
AVEC recherche web (grounding tendances), classées par potentiel commercial.

Comme la détection de tendances du début du projet, mais ciblée « blagues de niche
typographiques » pour POD. Gemini :
  - garde les niches de départ et en propose 10 de plus, sous-exploitées mais
    régulièrement recherchées (tendances actuelles) ;
  - pour chaque niche, 8-12 blagues in-group (FR/EN) que seuls les initiés captent ;
  - pour chacune : mots-clés ciblés, score 0-100, palier S/A/B/C, justification.

CONTRAINTE STRICTE passée au modèle : aucune marque déposée (pas de Pokémon,
Digimon, noms de jeux/persos protégés, marques, célébrités) — fandoms libres
uniquement.

Sortie : reports/niche_jokes_ranked_<date>.json + .md (classement lisible).
"""
import datetime
import json
import os
import re
import sys

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
_client = None
_models = None

SEED_NICHES = [
    "chess (en passant memes, mates, sacrifices)",
    "savage insults proving someone's stupidity",
    "developers / coding / sysadmin",
    "generic tabletop RPG (NO 'D&D' trademark, use generic terms like nat 20)",
]


def client():
    global _client
    if _client is None:
        from google import genai
        _client = genai.Client(api_key=GEMINI_API_KEY)
    return _client


def models():
    global _models
    if _models:
        return _models
    found = []
    try:
        for m in client().models.list():
            n = (getattr(m, "name", "") or "").replace("models/", "")
            if n and "flash" in n and not any(x in n for x in
                    ("image", "tts", "audio", "embedding", "vision", "live")):
                found.append(n)
    except Exception as e:  # noqa: BLE001
        print(f"[gemini] list: {e}", file=sys.stderr)

    def score(m):
        s = 0.0
        v = re.search(r"(\d+\.\d+)", m)
        if v:
            s += float(v.group(1)) * 10
        if "lite" in m:
            s -= 2
        if "latest" in m:
            s += 1.5
        return s
    r = sorted(set(found), key=score, reverse=True)
    for fb in ("gemini-2.5-flash", "gemini-flash-latest", "gemini-2.0-flash"):
        if fb not in r:
            r.append(fb)
    _models = r
    return r


def ask(prompt):
    from google.genai import types
    c = client()
    for model in models()[:4]:
        for grounding in (True, False):
            try:
                if grounding:
                    cfg = types.GenerateContentConfig(
                        tools=[types.Tool(google_search=types.GoogleSearch())],
                        temperature=0.8)
                else:
                    cfg = types.GenerateContentConfig(temperature=0.8)
                r = c.models.generate_content(model=model, contents=prompt, config=cfg)
                if r.text:
                    print(f"[gemini] OK {model}{'+search' if grounding else ''}")
                    return r.text
            except Exception as e:  # noqa: BLE001
                print(f"[gemini] {model} g={grounding}: {str(e)[:120]}", file=sys.stderr)
    return ""


def extract_json(text):
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1).strip()
    try:
        return json.loads(text)
    except Exception:  # noqa: BLE001
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:  # noqa: BLE001
                return None
    return None


PROMPT = """You are a print-on-demand market researcher (Redbubble, TeePublic, \
Amazon Merch, Etsy). Use up-to-date web knowledge of current 2026 trends.

Goal: build a ranked catalogue of NICHE typographic joke t-shirt designs for \
under-served sub-niches that are nevertheless regularly searched.

Niches to include (keep these):
%s

Then ADD 10 more under-served but regularly-searched niches that are trending \
now (e.g. specific hobbies, professions, fandoms that are NOT trademarked, \
internet micro-cultures). Avoid saturated niches.

HARD RULES:
- Absolutely NO trademarks: no Pokémon, Digimon, brand names, game/character \
names that are protected, no celebrities, no movie/song quotes. Free/public \
culture only (chess theory, generic RPG terms, programming, math, idioms...).
- Jokes must be true in-group jokes: only people in the niche fully get them.

For EACH niche, give 8-12 jokes. For EACH joke return:
- text: the exact phrase to print (keep it short, punchy)
- lang: "en" or "fr"
- keywords: 6-10 targeted POD search keywords (lowercase, under-served)
- score: integer 0-100 = estimated commercial success potential
- tier: "S" | "A" | "B" | "C"
- why: one short sentence justification (demand vs competition)

Return ONLY valid JSON of the form:
{"niches":[{"niche":"...","jokes":[{"text":"...","lang":"en","keywords":["..."],"score":87,"tier":"A","why":"..."}]}]}
""" % "\n".join(f"- {n}" for n in SEED_NICHES)


def main():
    if not GEMINI_API_KEY:
        print("ERREUR: GEMINI_API_KEY manquant", file=sys.stderr)
        return 1
    raw = ask(PROMPT)
    data = extract_json(raw)
    if not data or "niches" not in data:
        print("ERREUR: réponse Gemini non exploitable", file=sys.stderr)
        print(raw[:500], file=sys.stderr)
        return 1

    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M")
    os.makedirs("reports", exist_ok=True)
    jpath = f"reports/niche_jokes_ranked_{ts}.json"
    json.dump(data, open(jpath, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    allj = []
    for n in data["niches"]:
        for j in n.get("jokes", []):
            j["niche"] = n.get("niche", "")
            allj.append(j)
    allj.sort(key=lambda j: j.get("score", 0), reverse=True)
    md = [f"# Blagues de niche classées par potentiel ({len(allj)} idées, {len(data['niches'])} niches)\n"]
    md.append("| Score | Tier | Niche | Phrase | Mots-clés |")
    md.append("|---|---|---|---|---|")
    for j in allj:
        kw = ", ".join(j.get("keywords", [])[:6])
        txt = str(j.get("text", "")).replace("|", "/")
        md.append(f"| {j.get('score','')} | {j.get('tier','')} | {j.get('niche','')[:24]} | {txt} | {kw} |")
    mpath = f"reports/niche_jokes_ranked_{ts}.md"
    open(mpath, "w", encoding="utf-8").write("\n".join(md))
    print(f"{jpath}\n{mpath}\n{len(allj)} blagues sur {len(data['niches'])} niches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
