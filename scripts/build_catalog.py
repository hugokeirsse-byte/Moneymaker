#!/usr/bin/env python3
"""
build_catalog.py — cataloguer UNIVERSEL : couvre TOUS les designs de produits/
(typos récentes + anciens dossiers), trie par thème et génère les fiches POD
complètes (titre SEO + description + tags) pour upload en masse.

Source = `git ls-files produits/*.png` (couvre même les fichiers hors sparse-checkout).
Texte = data/*.json quand l'id correspond, sinon déduit du nom de fichier.

Sorties (catalog/) :
  pod_all.csv, by_theme/<theme>.csv, by_collection/<coll>.csv, SUMMARY.md

Usage : python scripts/build_catalog.py
"""
import csv
import json
import os
import re
import subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "catalog")
LANGS = ("en", "fr", "es", "de", "it", "pt", "ie", "nz", "au", "uk", "us", "xx")
LANG_LABEL = {"en": "English", "fr": "French", "es": "Spanish", "de": "German",
              "it": "Italian", "pt": "Portuguese", "ie": "English", "nz": "English",
              "au": "English", "uk": "English"}
GENERIC = ["funny shirt", "typography", "minimalist", "aesthetic", "gift idea",
           "trendy design", "statement tee", "for men", "for women"]
STRIP = re.compile(r"[*]")

# thème : (key, label, base_tags, keywords, who_en, who_fr)
THEMES = [
 ("feminism","Feminist",["feminist","feminism","girl power","smash patriarchy","women rights","equal rights"],
  ["feminist","féminist","patriarcat","patriarchy","women","femme","sororit","girls","bossy","sexism","sexisme","mon corps","my body","misogyn"],
  "feminists and women who fight for equality","les féministes et celles qui défendent l'égalité"),
 ("lgbtq","LGBTQ Pride",["pride","lgbtq","queer","trans rights","love is love","ally","rainbow"],
  ["pride","lgbtq","queer","trans","homophob","(wo)men","(s)he","pronoun","love is love","thembo","rainbow","gay"],
  "the LGBTQ+ community and allies","la communauté LGBTQ+ et ses allié·es"),
 ("climate","Climate & Ecology",["climate change","save the planet","ecology","environment","climate activist","eco friendly"],
  ["climat","climate","planet","planète","écolog","ecolog","carbon","co2","pollution","deforest","déforest","greenwash","extinction","asteroid","comète","earth","abeille","bee","ocean","océan","pêche","overfishing","pétrole"],
  "climate activists and eco-conscious people","les militant·es écolo"),
 ("animals","Animal Rights & Vegan",["vegan","animal rights","vegan gift","save animals","plant based","cruelty free"],
  ["vegan","végan","corrida","steak","cadavre","élevage","abattoir","fourrure","spécisme","cruelty","not food","cage"],
  "vegans and animal lovers","les vegans et défenseur·ses des animaux"),
 ("antiracism","Anti-Racism & Juneteenth",["anti racism","human rights","social justice","equality","juneteenth","solidarity"],
  ["racis","racism","antiracis","bigot","facho","fascis","xénophob","migrant","immigrant","babylon","juneteenth","black history","civil rights"],
  "anti-racists and human-rights advocates","les antiracistes"),
 ("politics","Activist & Leftist",["activist","eat the rich","anti capitalist","leftist","protest","revolution"],
  ["capitalism","capitalisme","antifa","milliardaire","billionaire","eat the rich","riches","lobbies","révolution","revolution","resist","grève","union","taxe","peuple","insurg","pavés","interdire","impossible","élites","elite","patron","système","marre des","against","tired of","free of","zone sans","allergic"],
  "activists and the politically loud","les militant·es et engagé·es"),
 ("mental_health","Mental Health & Neurodivergent",["mental health","neurodivergent","adhd","autism","anxiety","introvert","self care"],
  ["adhd","tdah","autis","anxi","anxious","introvert","neuro","dyslex","dyscalcul","dyspraxi","overthink","schizophr","instable","hypersensible","burnout","burn-out","mental","stim","spicy","empath","lunaire","lunatique"],
  "the neurodivergent and mental-health aware","les neuroatypiques"),
 ("family","Family & Dad/Mom",["dad gift","mom gift","fathers day","mothers day","family","grandma"],
  ["dad","papa","père","father","mom","mother","mère","family","famille","grandma","mamie","grandpa","papy","parent","fete des peres","fathers"],
  "dads, moms and families","les papas, mamans et familles"),
 ("professions","Jobs & Professions",["nurse gift","teacher gift","coworker gift","job humor","profession"],
  ["nurse","infirmi","teacher","prof ","welder","soudeur","mécano","mechanic","farmer","fermier","chef","baker","boulang","barista","firefighter","pompier","electric","plumber","engineer","ingénieur","developer","coder","programmer","doctor","médecin","trucker"],
  "people proud of their job","celles et ceux qui assument leur métier"),
 ("food_drink","Food & Drink",["foodie gift","coffee lover","food humor","caffeine","brunch"],
  ["coffee","café","caféine","caffeine"," tea","matcha","wine","beer","pizza","taco","cheese","chocolate","kebab","brownie","snack","brunch","foodie","sourdough","pickle","mushroom","champi"],
  "foodies and caffeine addicts","les gourmand·es et accros au café"),
 ("fitness_sport","Sport & Fitness",["gym gift","fitness","running","yoga","sport","football"],
  ["gym","running","trail","yoga","climb","grimpe","cycling","crossfit","lifting","marathon","surf","skate","soccer","foot","runner","scuba","world cup","coupe du monde","worldcup"],
  "sports and fitness lovers","les sportif·ves"),
 ("gaming_geek","Gaming & Geek",["gamer gift","gaming","nerd","geek","anime","dnd"],
  ["gamer","gaming","d&d","dnd","anime","manga","nerd","geek","retro game","console","8-bit","sci-fi","geek"],
  "gamers, nerds and geeks","les gamers et geeks"),
 ("hobbies_craft","Hobbies & Crafts",["hobby gift","craft lover","reading","crochet","fishing","camping"],
  ["knit","crochet","sewing","pottery","fishing","pêcheur","angler","hiking","randonn","camping","camp","reading","bookworm","book","livre","romantasy","tarot","crystal","vinyl","photography","chess","birder","disc golf","puzzle","diy","guitar"],
  "hobbyists and makers","les passionné·es"),
 ("plants_garden","Plants & Garden",["plant lover","plant mom","gardening","botanical","succulent"],
  ["plant","plante","garden","jardin","succulent","monstera","botanical","fleur"],
  "plant parents and gardeners","les accros aux plantes"),
 ("travel","Travel & Places",["travel gift","wanderlust","adventure","usa states","outdoors"],
  ["travel","voyage","wanderlust","mountain","montagne","beach","plage","road trip","adventure","state","texas","california","florida","york","états","ireland","irlande","france","zealand","australia"],
  "travelers and locals","les voyageur·ses"),
 ("cats","Cats",["cat lover","cat mom","cat dad","cat lady","crazy cat","kitten"],
  ["cat ","cat,","cat_","chat","gato","gatti","katzen","kitten","cat mom","cat dad","cat lady","feral cat"],
  "cat people","les fous et folles de chats"),
 ("pets","Pets & Dog Lovers",["dog mom","pet lover","dog dad","reptile","animal parent"],
  ["dog","chien","gecko","snake","reptile","ferret","axolotl","bunny","hamster","parrot","horse","frog","rat dad","dragon","perro","hund","malinois"],
  "pet parents and animal lovers","les maîtres d'animaux"),
 ("stoner","Stoner & Festival",["420","weed","stoner","cannabis","festival","high vibes"],
  ["420","weed","stoner","brownie","baked","blaze","high","rasta","trip","munchies"],
  "stoners and festival-goers","les stoners et festivalier·es"),
 ("work","Work & Office Humor",["office humor","work shirt","coworker gift","monday","sarcastic work"],
  ["meeting","réunion","boss","patron","lundi","monday","boulot","overtime","office","telework","télétravail","loyer","rent","quitting","démission","manager","9 to 5"],
  "tired employees","les salarié·es fatigué·es"),
 ("relationship","Relationship & Single",["single","dating","anti valentine","divorce","relationship humor"],
  ["single","célibataire","soltera","divorced","taken","valentine","unavailable","couple","future ex"],
  "singles and the relationship-weary","les célibataires"),
 ("solidarity","Solidarity & Kindness",["be kind","you matter","solidarity","anti bullying","kindness"],
  ["lonely","seul","talk to me","speak to me","you matter","tu comptes","safe","harcèlement","harassment","be kind","gentil","kindness","not alone","tiens bon"],
  "kind people and allies","les bienveillant·es"),
 ("adult_humor","Adult & Rude Humor",["rude shirt","offensive gift","sarcastic","adult humor","insult"],
  ["insult","insulte","swear","juron","rude","crude","nsfw","humour adulte","trash","con","connard","putain","merde","fuck","shit","bitch"],
  "fans of rude, no-filter humor","les amateur·ices d'humour cru"),
 ("existential","Existential & Dark Humor",["existential","nihilism","dark humor","philosophy","absurd"],
  ["existential","néant","nihil","poussière","atoms","void","vide","rien n'a","nothing matters","tout passe","doomed","quoi bon","sers-je","ouïe-je","cogito","veni vidi","mortifère","absurde","absurd","comète"],
  "lovers of dark humor and the absurd","les amateur·ices d'humour noir"),
 ("humor","Funny & Sarcastic",["funny saying","sarcastic","sarcasm","humor","meme shirt","funny quote","relatable"],
  [],
  "anyone with a sense of humor","tous ceux qui ont de l'humour"),
]
THEME_BY_KEY = {t[0]: t for t in THEMES}

COLLECTION_DEFAULT = {
    "neuro": "mental_health", "lunaire": "mental_health", "stoner": "stoner",
    "solidaire": "solidarity", "speak_to_me": "solidarity", "pride": "lgbtq",
    "fetes_de_juin": "lgbtq", "juneteenth": "antiracism", "warning": "politics",
    "anti": "politics", "revendications": "politics", "corrige": "feminism",
    "punchlines": "existential", "phrases_absurdes": "existential",
    "coupe_du_monde": "fitness_sport", "us_states": "travel",
    "geek_phrases": "gaming_geek", "fete_des_peres": "family",
    "humour_adulte": "adult_humor", "insult_posters": "adult_humor",
    "insults_multilang": "adult_humor", "relatable": "humor", "trendy": "humor",
    "typographies": "humor", "teepublic": "humor", "identite": "humor",
    "heart": "humor", "proverbes": "humor", "ironique": "humor", "arrow": "humor",
    "niches": "humor", "trending": "humor", "formats": "humor",
    "humour_patchs": "humor", "announcements": "humor", "childish": "humor",
    "word_shapes": "humor", "visual_puns": "humor", "fake_quotes": "humor",
    "effets_typo": "humor",
}


def clean(s):
    return STRIP.sub("", str(s)).replace("  ", " ").strip()


def entry_text(e):
    if "lines" in e:
        return clean(" ".join(e["lines"]))
    if "post" in e:
        t = f"{e.get('pre','I')} love {clean(e['post'])}"
        if e.get("replacement"):
            t = f"{e.get('pre','I')} love {e['replacement']} not {clean(e['post'])}"
        return clean(t)
    if "struck" in e:
        return clean(" ".join(e.get("kept", [])) + f" {e['struck']} → {e['replacement']}")
    if "items" in e:
        return clean(e.get("head", "") + " " + " ".join(e["items"][:6]))
    if "text" in e:
        bits = [e.get("head", ""), e.get("title", ""), e.get("text", ""), e.get("sub", "")]
        return clean(" ".join(b for b in bits if b))
    # schéma inconnu : on ramasse les valeurs texte
    out = []
    for k, v in e.items():
        if k in ("id", "lang", "niche", "format", "dir", "color", "ornament"):
            continue
        if isinstance(v, str):
            out.append(v)
        elif isinstance(v, list):
            out += [x for x in v if isinstance(x, str)]
    return clean(" ".join(out))


def load_data_index():
    idx = {}
    for fn in os.listdir(DATA):
        if not fn.endswith(".json"):
            continue
        try:
            d = json.load(open(os.path.join(DATA, fn), encoding="utf-8"))
        except Exception:
            continue
        for e in d.get("entries", []) if isinstance(d, dict) else []:
            if isinstance(e, dict) and e.get("id"):
                idx[e["id"]] = (entry_text(e), e.get("lang", ""),
                                e.get("niche", "") or e.get("format", ""))
    return idx


def lang_of(eid):
    m = re.search(r"_([a-z]{2})$", eid)
    return m.group(1) if (m and m.group(1) in LANGS) else ""


def derive_text(eid):
    s = re.sub(r"_([a-z]{2})$", "", eid) if lang_of(eid) else eid
    s = re.sub(r"_(dark|light|white|black|red|gold|mono|bw|wb|noir|blanc|or)$", "", s)
    s = re.sub(r"_(dark|light|white|black|red|gold|mono|bw|wb)$", "", s)
    s = s.replace("_", " ").replace("-", " ").strip()
    return s.title()


def git_designs():
    r = subprocess.run(["git", "ls-files", "-z", "produits"], cwd=ROOT,
                       capture_output=True)
    paths = [p for p in r.stdout.decode("utf-8", "replace").split("\0") if p.endswith(".png")]
    designs = {}
    for p in paths:
        m = re.match(r"produits/([^/\"]+)/(.+)\.png$", p)
        if not m:
            continue
        coll, stem = m.group(1), m.group(2)
        if coll.startswith('"') or "/" in stem:
            continue
        if "__" in stem:
            eid = stem.split("__")[0]
        else:
            eid = stem
        key = (coll, eid)
        designs.setdefault(key, []).append(p)
    return designs


def classify(text, coll, eid, sub):
    hay = (text + " " + eid.replace("_", " ") + " " + coll + " " + sub).lower()
    best = None
    for key, label, tags, kws, *_ in THEMES:
        score = sum(1 for k in kws if k in hay)
        if score and (best is None or score > best[1]):
            best = (key, score)
    return best[0] if best else COLLECTION_DEFAULT.get(coll, "humor")


def word_tags(text):
    words = re.findall(r"[A-Za-zÀ-ÿ']{4,}", text.lower())
    stop = {"avec", "pour", "dans", "cette", "tout", "mais", "plus", "with", "your",
            "this", "that", "they", "from", "have", "just", "like", "only", "sont",
            "nous", "vous", "leur", "être", "fait", "what", "when", "will"}
    seen, out = set(), []
    for w in words:
        w = w.strip("'")
        if len(w) >= 4 and w not in stop and w not in seen:
            seen.add(w); out.append(w)
    return out[:5]


def make_desc(phrase, theme, label, lang, who_en, who_fr):
    if lang == "fr":
        return (f"« {phrase} » en typographie minimaliste et percutante. Un design "
                f"pour {who_fr}. Idée cadeau parfaite, à porter ou offrir. Disponible "
                f"sur t-shirt, sweat, sticker, mug, tote bag, poster et plus. "
                f"#{theme} #typographie")
    return (f"\"{phrase}\" in clean minimalist typography. A statement design for "
            f"{who_en}. Makes a perfect gift to wear or give. Available on tees, "
            f"hoodies, stickers, mugs, tote bags, posters and more. #{theme} #typography")


def build():
    os.makedirs(os.path.join(OUT, "by_theme"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "by_collection"), exist_ok=True)
    idx = load_data_index()
    designs = git_designs()
    rows = []
    for (coll, eid), files in sorted(designs.items()):
        if eid in idx and idx[eid][0]:
            text, lang, sub = idx[eid]
        else:
            text, lang, sub = derive_text(eid), lang_of(eid), ""
        if not lang:
            lang = lang_of(eid)
        theme = classify(text, coll, eid, sub)
        _, label, base_tags, _kws, who_en, who_fr = THEME_BY_KEY[theme]
        ll = LANG_LABEL.get(lang, "")
        title = (f"{text} - {label} Design" if ll in ("English", "")
                 else f"{text} - {label} ({ll}) Design")[:140]
        desc = make_desc(text, theme, label, lang, who_en, who_fr)
        extra = [sub.replace("_", " ")] if sub else []
        tags = []
        for t in base_tags + word_tags(text) + extra + [label.lower()] + GENERIC:
            t = t.lower().strip()
            if t and t not in tags:
                tags.append(t)
        rows.append({
            "id": eid, "collection": coll, "theme": theme, "theme_label": label,
            "subniche": sub, "lang": lang, "title": title, "description": desc,
            "tags": ", ".join(tags[:25]), "files": " | ".join(sorted(files)),
        })

    cols = ["id", "collection", "theme", "theme_label", "subniche", "lang", "title",
            "description", "tags", "files"]
    rows.sort(key=lambda r: (r["theme"], r["collection"], r["id"]))
    with open(os.path.join(OUT, "pod_all.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rows)

    by = {}
    for r in rows:
        by.setdefault(r["theme"], []).append(r)
    for theme, rs in by.items():
        with open(os.path.join(OUT, "by_theme", f"{theme}.csv"), "w", newline="",
                  encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rs)
    bycoll = {}
    for r in rows:
        bycoll.setdefault(r["collection"], []).append(r)
    for coll, rs in bycoll.items():
        rs.sort(key=lambda r: (r["subniche"], r["id"]))
        with open(os.path.join(OUT, "by_collection", f"{coll}.csv"), "w", newline="",
                  encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols); w.writeheader(); w.writerows(rs)

    # ── encarts lisibles (prêts à copier-coller, 1 bloc par design) ──
    os.makedirs(os.path.join(OUT, "encarts"), exist_ok=True)
    SEP = "═" * 64
    for theme, rs in by.items():
        label = THEME_BY_KEY[theme][1]
        lines = [SEP, f"  CATÉGORIE : {label}   ({len(rs)} designs)",
                 "  Pour chaque design : uploade l'IMAGE, puis copie-colle "
                 "TITRE / TAGS / DESCRIPTION.", SEP, ""]
        for i, r in enumerate(rs, 1):
            imgs = [os.path.basename(x) for x in r["files"].split(" | ")]
            lines += [
                f"───── #{i} ─────  ({r['collection']} · {r['lang'] or '—'})",
                f"IMAGE(S) : {', '.join(imgs)}",
                "",
                "TITRE :",
                r["title"],
                "",
                "TAGS :",
                r["tags"],
                "",
                "DESCRIPTION :",
                r["description"],
                "", "",
            ]
        with open(os.path.join(OUT, "encarts", f"{theme}.txt"), "w",
                  encoding="utf-8") as fh:
            fh.write("\n".join(lines))

    plats = ("Redbubble, TeePublic, Amazon Merch on Demand, Spreadshirt, Spring, "
             "Threadless, Zazzle, Society6, Displate, Fine Art America")
    with open(os.path.join(OUT, "SUMMARY.md"), "w", encoding="utf-8") as fh:
        fh.write("# Catalogue POD universel — toutes collections\n\n")
        fh.write(f"**{len(rows)} designs** ({len(designs)} fichiers groupés), "
                 f"{len(by)} thèmes, {len(bycoll)} collections.\n\n")
        fh.write(f"Plateformes gratuites : {plats}.\n\n")
        fh.write("`pod_all.csv` = tout (titre + description + tags + fichiers). "
                 "`by_theme/` & `by_collection/` = lots à mots-clés quasi constants.\n\n")
        fh.write("## Par thème\n\n")
        for theme in sorted(by, key=lambda t: -len(by[t])):
            fh.write(f"- **{THEME_BY_KEY[theme][1]}** (`{theme}`) : {len(by[theme])}\n")
        fh.write("\n## Par collection\n\n")
        for c in sorted(bycoll, key=lambda x: -len(bycoll[x])):
            fh.write(f"- **{c}** : {len(bycoll[c])}\n")

    print(f"{len(rows)} designs, {len(by)} thèmes, {len(bycoll)} collections")
    for theme in sorted(by, key=lambda t: -len(by[t])):
        print(f"  {theme:16} {len(by[theme])}")


if __name__ == "__main__":
    build()
