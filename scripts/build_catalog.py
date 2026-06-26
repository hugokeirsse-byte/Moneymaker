#!/usr/bin/env python3
"""
build_catalog.py — trie tous les designs par thème fin et génère les métadonnées
POD complètes (titre SEO + description + tags) pour upload en masse.

Sorties (catalog/) :
  pod_all.csv              — 1 ligne/design : id, collection, theme, subniche, lang,
                             title, description, tags, file_dark, file_light
  by_theme/<theme>.csv     — 1 fichier/thème (tags quasi identiques → upload par lot)
  by_collection/<coll>.csv
  SUMMARY.md               — comptes + plateformes gratuites

Usage : python scripts/build_catalog.py
"""
import csv
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "catalog")

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
           "trendy design", "statement tee", "for men", "for women"]

# thème : (label, tags de base, mots-clés, who_en, who_fr)
THEMES = [
 ("feminism","Feminist",["feminist","feminism","girl power","smash patriarchy","women rights","equal rights","feminist gift"],
  ["feminist","féminist","patriarcat","patriarchy","women","femme","sororit","girls","bossy","sexism","sexisme","mon corps","my body","she said","misogyn"],
  "feminists and women who fight for equality","les féministes et celles qui défendent l'égalité"),
 ("lgbtq","LGBTQ Pride",["pride","lgbtq","queer","trans rights","love is love","ally","rainbow"],
  ["pride","lgbtq","queer","trans","homophobi","(wo)men","(s)he","pronoun","love is love","thembo"],
  "the LGBTQ+ community and proud allies","la communauté LGBTQ+ et ses allié·es"),
 ("climate","Climate & Ecology",["climate change","save the planet","ecology","environment","climate activist","earth day","eco friendly"],
  ["climat","climate","planet","planète","écolog","ecolog","carbon","co2","pollution","deforest","déforest","greenwash","anthropocène","extinction","asteroid","comète","earth","abeille","bee","ocean","océan","pêche","overfishing","pétrole","forêt"],
  "climate activists and eco-conscious people","les militant·es écolo et les éco-conscient·es"),
 ("animals","Animal Rights & Vegan",["vegan","animal rights","vegan gift","save animals","plant based","cruelty free","animal lover"],
  ["vegan","végan","corrida","steak","cadavre","élevage","abattoir","fourrure","spécisme","cruelty","not food","leur peau","cage"],
  "vegans and animal lovers","les vegans et les défenseur·ses des animaux"),
 ("antiracism","Anti-Racism",["anti racism","human rights","social justice","equality","no racism","solidarity"],
  ["racis","racism","antiracis","bigot","facho","fascis","xénophob","migrant","immigrant","babylon","babylone"],
  "anti-racists and human-rights advocates","les antiracistes et les défenseur·ses des droits humains"),
 ("politics","Activist & Leftist",["activist","eat the rich","anti capitalist","leftist","protest","revolution","class war"],
  ["capitalism","capitalisme","antifa","milliardaire","billionaire","ultra-rich","eat the rich","riches","lobbies","révolution","revolution","resist","grève","union","taxe","tax the rich","peuple","insurg","suppliciés","pavés","interdire","impossible","élites","elite","patron","système","system","marre des","against","tired of","free of","zone sans","allergic","mai 68","situationist"],
  "activists, leftists and the politically loud","les militant·es et les engagé·es politiquement"),
 ("mental_health","Mental Health & Neurodivergent",["mental health","neurodivergent","adhd","autism","anxiety","introvert","self care","neurospicy"],
  ["adhd","tdah","autis","anxi","anxious","introvert","neuro","dyslex","dyscalcul","dyspraxi","overthink","surpenseur","schizophr","instable","hypersensible","burn-out","burnout","santé mentale","mental","stim","spicy","empath"],
  "the neurodivergent and mental-health aware","les neuroatypiques et les concerné·es par la santé mentale"),
 ("professions","Jobs & Professions",["nurse gift","teacher gift","coworker gift","job humor","profession","work pride"],
  ["nurse","infirmi","teacher","prof ","welder","soudeur","mécano","mechanic","farmer","fermier","chef","baker","boulang","barista","firefighter","pompier","electric","plumber","engineer","ingénieur","developer","coder","programmer","doctor","médecin","trucker"],
  "people proud of their job","celles et ceux qui assument leur métier"),
 ("food_drink","Food & Drink",["foodie gift","coffee lover","food humor","caffeine","brunch","snack lover"],
  ["coffee","café","caféine","caffeine","tea","matcha","wine","beer","pizza","taco","cheese","chocolate","kebab","brownie","snack","brunch","foodie","sourdough","bread"],
  "foodies and caffeine addicts","les gourmand·es et accros au café"),
 ("fitness_sport","Fitness & Sport",["gym gift","fitness","running","yoga","workout","sport"],
  ["gym","running","trail","yoga","climb","grimpe","cycling","crossfit","lifting","marathon","surf","skate","soccer","foot","runner"],
  "gym-goers and sports lovers","les sportif·ves et accros à la salle"),
 ("gaming_geek","Gaming & Geek",["gamer gift","gaming","nerd","geek","anime","dnd"],
  ["gamer","gaming","d&d","dnd","anime","manga","nerd","geek","retro game","console","8-bit","sci-fi"],
  "gamers, nerds and geeks","les gamers, nerds et geeks"),
 ("hobbies_craft","Hobbies & Crafts",["hobby gift","craft lover","reading","crochet","fishing","hobby"],
  ["knit","crochet","sewing","pottery","fishing","pêcheur","angler","hiking","randonn","camping","reading","bookworm","book","livre","romantasy","tarot","crystal","vinyl","photography","chess","birder","disc golf","puzzle","diy"],
  "hobbyists and makers","les passionné·es et créatif·ves"),
 ("plants_garden","Plants & Garden",["plant lover","plant mom","gardening","botanical","succulent"],
  ["plant","plante","garden","jardin","succulent","monstera","botanical","fleur","greens"],
  "plant parents and gardeners","les accros aux plantes et au jardinage"),
 ("music","Music & Festival",["music lover","festival","band tee","vinyl","concert"],
  ["music","musique","guitar","drummer","band","festival","dj","vinyl","concert","rave"],
  "music and festival lovers","les amoureux·ses de musique et de festivals"),
 ("travel","Travel & Outdoors",["travel gift","wanderlust","adventure","mountains","outdoors"],
  ["travel","voyage","wanderlust","mountain","montagne","beach","plage","road trip","adventure","explore","outdoor"],
  "travelers and adventurers","les voyageur·ses et aventurier·es"),
 ("cats","Cats",["cat lover","cat mom","cat dad","cat lady","crazy cat","kitten"],
  ["cat ","cat,","chat","gato","gatti","katzen","kitten","cat mom","cat dad","cat lady","feral cat","maman poule"],
  "cat people","les fous et folles de chats"),
 ("pets","Pets & Animal Lovers",["dog mom","pet lover","dog dad","reptile","animal parent"],
  ["dog","chien","gecko","snake","reptile","ferret","axolotl","bunny","hamster","parrot","horse","frog","rat dad","dragon","perro","hund"],
  "pet parents and animal lovers","les maîtres d'animaux et amoureux·ses des bêtes"),
 ("stoner","Stoner & Festival",["420","weed","stoner","cannabis","festival","high vibes"],
  ["420","weed","stoner","champi","brownie","herbe","jardinage","baked","blaze","high","rasta","trip","munchies"],
  "stoners and festival-goers","les stoners et festivalier·es"),
 ("work","Work & Office Humor",["office humor","work shirt","coworker gift","monday","sarcastic work"],
  ["meeting","réunion","boss","patron","lundi","monday","boulot","overtime","office","telework","télétravail","loyer","rent","quitting","démission","surdiplômé","underpaid","manager","9 to 5"],
  "tired employees and office workers","les salarié·es fatigué·es et accros au bureau"),
 ("relationship","Relationship & Single",["single","dating","anti valentine","divorce","relationship humor"],
  ["single","célibataire","soltera","divorced","taken","valentine","unavailable","couple","future ex"],
  "singles and the relationship-weary","les célibataires et désabusé·es de l'amour"),
 ("solidarity","Solidarity & Kindness",["be kind","you matter","solidarity","anti bullying","kindness"],
  ["lonely","seul","talk to me","you matter","tu comptes","safe","harcèlement","harassment","be kind","gentil","kindness","not alone","tiens bon"],
  "kind people and allies","les bienveillant·es et allié·es"),
 ("existential","Existential & Dark Humor",["existential","nihilism","dark humor","philosophy","absurd"],
  ["existential","néant","nihil","poussière","atoms","void","vide","rien n'a","nothing matters","tout passe","doomed","quoi bon","sers-je","ouïe-je","cogito","veni vidi","tout ça pour ça","mortifère","anthropocène","comète"],
  "lovers of dark humor and the absurd","les amateur·ices d'humour noir et d'absurde"),
 ("humor","Funny & Sarcastic",["funny saying","sarcastic","sarcasm","humor","meme shirt","funny quote"],
  [],
  "anyone with a sense of humor","tous ceux qui ont de l'humour"),
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


def text_of(ctype, e):
    if ctype == "lines":
        return clean(" ".join(e["lines"]))
    if ctype == "heart":
        t = f"{e.get('pre','I')} love {clean(e['post'])}"
        if e.get("replacement"):
            t = f"{e.get('pre','I')} love {e['replacement']} not {clean(e['post'])}"
        return clean(t)
    if ctype == "corrige":
        return clean(" ".join(e.get("kept", [])) + f" {e['struck']} → {e['replacement']}")
    if ctype == "warning":
        return clean(e["text"] + (" " + e.get("sub", "") if e.get("sub") else ""))
    if ctype == "anti":
        return clean(e.get("head", "Anti") + " " + " ".join(e["items"][:6]))
    if ctype == "formats":
        bits = [e.get("head", ""), e.get("title", ""), e.get("text", "")] + e.get("items", [])
        bits += [r[0] for r in e.get("rows", [])]
        return clean(" ".join(b for b in bits if b))
    return ""


def classify(text, coll, eid, sub):
    hay = (text + " " + eid + " " + coll + " " + sub).lower()
    best = None
    for key, label, tags, kws, who_en, who_fr in THEMES:
        score = sum(1 for k in kws if k in hay)
        if score and (best is None or score > best[1]):
            best = (key, score)
    return best[0] if best else COLLECTION_DEFAULT.get(coll, "humor")


def word_tags(text):
    words = re.findall(r"[A-Za-zÀ-ÿ']{4,}", text.lower())
    stop = {"avec", "pour", "dans", "cette", "tout", "mais", "plus", "with", "your",
            "this", "that", "they", "from", "have", "just", "like", "only", "sont",
            "nous", "vous", "leur", "être", "fait", "what", "when", "will", "qu'on"}
    seen, out = set(), []
    for w in words:
        w = w.strip("'")
        if len(w) >= 4 and w not in stop and w not in seen:
            seen.add(w); out.append(w)
    return out[:5]


def make_title(phrase, label, ll):
    base = f"{phrase} - {label} Typography Design"
    if ll and ll not in ("English",):
        base = f"{phrase} - {label} ({ll}) Design"
    return base[:140]


def make_desc(phrase, theme, label, lang, who_en, who_fr):
    if lang == "fr":
        return (f"« {phrase} » en typographie or et noir, minimaliste et percutante. "
                f"Un design pour {who_fr}. Idée cadeau parfaite, à porter ou offrir. "
                f"Disponible sur t-shirt, sweat, sticker, mug, tote bag, poster et plus. "
                f"#{theme} #typographie")
    return (f"\"{phrase}\" in clean gold-and-black minimalist typography. "
            f"A statement design for {who_en}. Makes a perfect gift to wear or give. "
            f"Available on tees, hoodies, stickers, mugs, tote bags, posters and more. "
            f"#{theme} #typography")


def build():
    os.makedirs(os.path.join(OUT, "by_theme"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "by_collection"), exist_ok=True)
    rows = []
    for fn, (coll, ctype) in COLLECTIONS.items():
        path = os.path.join(DATA, fn)
        if not os.path.isfile(path):
            continue
        data = json.load(open(path, encoding="utf-8"))
        for e in data["entries"]:
            eid = e["id"]; lang = e.get("lang", "")
            text = text_of(ctype, e)
            sub = e.get("niche", "") or e.get("format", "")
            theme = classify(text, coll, eid, sub)
            _, label, base_tags, _kws, who_en, who_fr = THEME_BY_KEY[theme]
            ll = LANG_LABEL.get(lang, "")
            title = make_title(text, label, ll)
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
                "tags": ", ".join(tags[:25]),
                "file_dark": f"produits/{coll}/{eid}__dark.png",
                "file_light": f"produits/{coll}/{eid}__light.png",
            })

    cols = ["id", "collection", "theme", "theme_label", "subniche", "lang", "title",
            "description", "tags", "file_dark", "file_light"]
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

    plats = ("Redbubble, TeePublic, Amazon Merch on Demand, Spreadshirt, Spring, "
             "Threadless, Zazzle, Society6, Displate, Fine Art America")
    with open(os.path.join(OUT, "SUMMARY.md"), "w", encoding="utf-8") as fh:
        fh.write("# Catalogue POD — titres, descriptions & tags prêts\n\n")
        fh.write(f"**{len(rows)} designs** ({len(rows)*2} fichiers dark+light), "
                 f"{len(by)} thèmes.\n\n")
        fh.write(f"Plateformes gratuites visées : {plats}.\n\n")
        fh.write("`pod_all.csv` = tout. `by_theme/` et `by_collection/` = lots à "
                 "mots-clés quasi constants pour upload en masse.\n\n## Par thème\n\n")
        for theme in sorted(by, key=lambda t: -len(by[t])):
            label = THEME_BY_KEY[theme][1]
            base = ", ".join(THEME_BY_KEY[theme][2])
            fh.write(f"### {label} (`{theme}`) — {len(by[theme])} designs\n")
            fh.write(f"Tags de base : `{base}`\n\n")
        fh.write("## Par collection\n\n")
        cc = {}
        for r in rows:
            cc[r["collection"]] = cc.get(r["collection"], 0) + 1
        for c in sorted(cc, key=lambda x: -cc[x]):
            fh.write(f"- **{c}** : {cc[c]}\n")

    print(f"{len(rows)} designs, {len(by)} thèmes")
    for theme in sorted(by, key=lambda t: -len(by[t])):
        print(f"  {theme:16} {len(by[theme])}")


if __name__ == "__main__":
    build()
