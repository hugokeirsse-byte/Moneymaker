#!/usr/bin/env python3
"""
fetch_portraits.py — télécharge les portraits (domaine public) des auteurs.

À lancer dans un environnement où Wikimedia est accessible (l'environnement
d'exécution distant le bloque). Remplit assets/portraits/<slug>.jpg ; le
générateur gen_fake_quotes.py détecte alors automatiquement la photo et la place
en médaillon.

Usage : python scripts/fetch_portraits.py
"""
import os
import urllib.parse
import urllib.request

# slug (= celui de gen_fake_quotes.py) -> titre de la page Wikipedia (en)
AUTHORS = {
    "victor_hugo": "Victor Hugo",
    "descartes": "René Descartes",
    "napoleon": "Napoleon",
    "voltaire": "Voltaire",
    "moliere": "Molière",
    "shakespeare": "William Shakespeare",
    "poe": "Edgar Allan Poe",
    "darwin": "Charles Darwin",
    "nietzsche": "Friedrich Nietzsche",
    "beethoven": "Ludwig van Beethoven",
}

UA = ("MoneymakerBot/1.0 (https://github.com/hugokeirsse-byte/moneymaker; "
      "contact@example.com) python-urllib")
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "assets", "portraits")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=30)


def main():
    os.makedirs(OUT, exist_ok=True)
    import json
    ok = 0
    for slug, title in AUTHORS.items():
        try:
            api = ("https://en.wikipedia.org/api/rest_v1/page/summary/"
                   + urllib.parse.quote(title.replace(" ", "_")))
            data = json.load(get(api))
            img = (data.get("originalimage", {}).get("source")
                   or data.get("thumbnail", {}).get("source"))
            if not img:
                print("  pas d'image :", slug)
                continue
            ext = os.path.splitext(img.split("?")[0])[1].lower() or ".jpg"
            path = os.path.join(OUT, f"{slug}{ext}")
            with open(path, "wb") as f:
                f.write(get(img).read())
            print("  ok :", slug, os.path.getsize(path), "o")
            ok += 1
        except Exception as e:
            print("  échec :", slug, e)
    print(f"\n{ok}/{len(AUTHORS)} portraits -> {OUT}")
    print("Relance ensuite : python scripts/gen_fake_quotes.py --out produits/fake_quotes")


if __name__ == "__main__":
    main()
