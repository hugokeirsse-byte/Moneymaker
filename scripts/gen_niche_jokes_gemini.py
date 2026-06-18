#!/usr/bin/env python3
"""
gen_niche_jokes_gemini.py — niches + blagues (Gemini, web grounding) PUIS classement
sur de VRAIES données de recherche (DataForSEO : volume mensuel réel + compétition).

Pipeline 2 étages :
  1) Gemini (recherche web activée) propose des niches sous-exploitées tendances et,
     pour chacune, des blagues IN-GROUP, INNOVANTES et PERCUTANTES (jamais de
     clichés sur-utilisés), avec des mots-clés candidats ciblés ;
  2) DataForSEO renvoie le VRAI volume de recherche mensuel + la compétition de tous
     ces mots-clés ; on classe chaque blague sur ces données réelles (demande forte,
     compétition faible), pas sur un score inventé.

Aucune marque déposée (fandoms libres uniquement).
Sortie : reports/niche_jokes_ranked_<date>.json + .md (classé par volume RÉEL).
"""
import base64
import datetime
import json
import os
import re
import sys
import urllib.request

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
DFS_LOGIN = os.environ.get("DATAFORSEO_LOGIN", "")
DFS_PASSWORD = os.environ.get("DATAFORSEO_PASSWORD", "")
_client = None
_models = None

SEED_NICHES = [
    "chess (en passant memes, theory, sacrifices, clock slap)",
    "savage insults proving someone's stupidity",
    "developers / coding / sysadmin",
    "generic tabletop RPG (NO 'D&D' trademark; use nat 20, crit fail, loot, boss fight)",
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

    def sc(m):
        s = 0.0
        v = re.search(r"(\d+\.\d+)", m)
        if v:
            s += float(v.group(1)) * 10
        if "lite" in m:
            s -= 2
        if "latest" in m:
            s += 1.5
        return s
    r = sorted(set(found), key=sc, reverse=True)
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
                cfg = types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())] if grounding else None,
                    temperature=0.85)
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


def dfs_volumes(keywords):
    """Vrais volumes mensuels + compétition via DataForSEO. {} si indispo."""
    if not (DFS_LOGIN and DFS_PASSWORD) or not keywords:
        return {}
    auth = base64.b64encode(f"{DFS_LOGIN}:{DFS_PASSWORD}".encode()).decode()
    url = "https://api.dataforseo.com/v3/keywords_data/google_ads/search_volume/live"
    out = {}
    uniq = sorted({k.lower().strip() for k in keywords if k.strip()})
    for i in range(0, len(uniq), 700):
        chunk = uniq[i:i + 700]
        payload = [{"keywords": chunk, "location_code": 2840, "language_code": "en"}]
        req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                     headers={"Authorization": f"Basic {auth}",
                                              "Content-Type": "application/json"})
        try:
            d = json.load(urllib.request.urlopen(req, timeout=120))
            for task in d.get("tasks", []):
                for it in (task.get("result") or []):
                    kw = (it.get("keyword") or "").lower().strip()
                    if kw:
                        out[kw] = {
                            "vol": it.get("search_volume") or 0,
                            "comp": (it.get("competition_index") or 0) / 100.0,
                        }
            print(f"[dataforseo] {len(out)} mots-clés réels récupérés")
        except Exception as e:  # noqa: BLE001
            print(f"[dataforseo] erreur: {str(e)[:160]}", file=sys.stderr)
    return out


PROMPT = """You are a print-on-demand trend researcher (Redbubble, TeePublic, \
Amazon Merch, Etsy). Use real, up-to-date web knowledge (2026).

Build niche TYPOGRAPHIC joke t-shirt ideas for under-served sub-niches that are \
nevertheless regularly searched.

Keep these niches:
%s
Then ADD 12 more under-served-but-searched, currently trending niches (specific \
hobbies, jobs, micro-cultures, NON-trademarked fandoms).

For EACH niche, first research (web): what do people in this community ADORE, and \
what do they keep COMPLAINING is missing / not made for them? \
Summarize as "loves" and "pains" (one short line each). \
Let those pains and loves inspire the most resonant jokes.

QUALITY BAR — this is critical:
- Jokes must be ORIGINAL, INNOVATIVE and PUNCHY. NO tired clichés \
("it works on my machine", "but first coffee", "live laugh love", "I'm silently \
correcting your grammar"). Surprise the reader; be specific and clever; an \
outsider should NOT fully get it.
- Rhymes and wordplay are welcome — e.g. in French: "calvitie précoce, zizi \
féroce"; in English: puns on technical jargon, rule names, move names.
- TRADEMARK-EVOCATIVE BUT FREE words are encouraged: words everyone associates \
with a franchise but nobody can own (e.g. "shiny", "critical hit", "nat 20", \
"speedrun", "respawn", "buff", "nerf", "loot", "boss fight", "aggro", \
"proc", "AoE", "on tilt", "en passant"). Mark evocative=true for these.
- 8 to 12 jokes per niche.

HARD RULES: absolutely NO trademarks (no Pokémon, Digimon, brands, protected \
game/character names, celebrities, song/movie quotes). Free/public culture only.

For each joke also pick the best TYPOGRAPHIC FORMAT from: \
"dictionary" (word + phonetic + origin + rule + definition) | \
"filename" (text as a system filename, e.g. reality.exe has stopped) | \
"error" (Error 404 style message) | \
"strikethrough" (crossed-out word replaced by truth) | \
"censored" (key word blacked out, obvious from context) | \
"repetition" (word repeated with growing weight/caps) | \
"arch_rainbow" (text arched like a rainbow) | \
"word_shape" (letters arranged to form a silhouette) | \
"plain" (clean bold phrase, nothing fancy)

For each joke give: text (short, punchy), lang ("en"/"fr"), format (one of above), \
evocative (true/false), and keywords = 5-8 REAL POD search phrases a buyer would \
type (lowercase, specific, the kind that have actual search volume).

Also propose 8 cross-niche COMBOS (e.g. chess x coding, cat lady x goth, \
tabletop RPG x nursing). Each combo: two niches, 3-5 jokes that only make sense \
if you belong to BOTH.

Return ONLY JSON:
{"niches":[{"niche":"...","loves":"...","pains":"...","jokes":[{"text":"...",\
"lang":"en","format":"plain","evocative":false,"keywords":["..."],"why":"..."}]}],\
"combos":[{"niches":["niche1","niche2"],"jokes":[{"text":"...","lang":"en",\
"format":"plain","evocative":false,"keywords":["..."],"why":"..."}]}]}
""" % "\n".join(f"- {n}" for n in SEED_NICHES)


def main():
    if not GEMINI_API_KEY:
        print("ERREUR: GEMINI_API_KEY manquant", file=sys.stderr)
        return 1
    data = extract_json(ask(PROMPT))
    if not data or "niches" not in data:
        print("ERREUR: réponse Gemini non exploitable", file=sys.stderr)
        return 1

    jokes = []
    for n in data["niches"]:
        for j in n.get("jokes", []):
            j["niche"] = n.get("niche", "")
            jokes.append(j)
    for c in data.get("combos", []):
        label = "COMBO: " + " x ".join(c.get("niches", []))
        for j in c.get("jokes", []):
            j["niche"] = label
            jokes.append(j)

    # vraies données de recherche
    allkw = [k for j in jokes for k in (j.get("keywords") or [])]
    vols = dfs_volumes(allkw)
    real = bool(vols)

    for j in jokes:
        best_kw, best_vol, best_comp = "", 0, 0.0
        for k in (j.get("keywords") or []):
            rec = vols.get(k.lower().strip())
            if rec and rec["vol"] >= best_vol:
                best_kw, best_vol, best_comp = k, rec["vol"], rec["comp"]
        j["real_keyword"] = best_kw
        j["real_volume"] = best_vol
        j["real_competition"] = round(best_comp, 2)
        j["data_score"] = round(best_vol * (1 - 0.45 * best_comp))

    jokes.sort(key=lambda j: (j.get("data_score", 0), j.get("real_volume", 0)), reverse=True)

    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M")
    os.makedirs("reports", exist_ok=True)
    out = {"generated_at": ts, "real_data": real,
           "source": "DataForSEO (US, en)" if real else "estimations",
           "total_jokes": len(jokes), "niches": data["niches"],
           "combos": data.get("combos", []), "ranked": jokes}
    json.dump(out, open(f"reports/niche_jokes_ranked_{ts}.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)

    head = ("VRAIES données DataForSEO (volume mensuel US)" if real
            else "⚠️ pas de données réelles (DataForSEO indispo) — à brancher")
    md = [f"# Blagues de niche classées par DEMANDE RÉELLE — {head}",
          f"{len(jokes)} blagues · {len(data['niches'])} niches + {len(data.get('combos', []))} combos\n",
          "| Vol/mois | Compét. | Niche | Format | Phrase | Mot-clé gagnant |",
          "|---|---|---|---|---|---|"]
    for j in jokes:
        md.append(f"| {j['real_volume']} | {j['real_competition']:.2f} | "
                  f"{j['niche'][:28]} | {j.get('format', 'plain')} | "
                  f"{str(j.get('text', '')).replace('|', '/')} | {j['real_keyword']} |")
    open(f"reports/niche_jokes_ranked_{ts}.md", "w", encoding="utf-8").write("\n".join(md))
    print(f"reports/niche_jokes_ranked_{ts}.md — {len(jokes)} blagues, données réelles={real}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
