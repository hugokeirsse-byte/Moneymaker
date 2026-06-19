#!/usr/bin/env python3
"""
typo_fonts.py — roster de polices partagé par les scripts de design typo.

Toutes les polices vivent dans assets/fonts/ (téléchargées au runtime / CI).
Chaque clé logique pointe vers un fichier réel ; les polices variables
(Oswald, Playfair, Caveat) sont calées sur un poids gras lisible.

Usage :
    from typo_fonts import load_font, FONT_FILES
    f = load_font("impact", 200)        # ImageFont prêt à dessiner
"""
import os

from PIL import ImageFont

# racine assets/fonts résolue relativement au repo (ce fichier est dans scripts/)
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
FONT_DIR = os.path.join(_ROOT, "assets", "fonts")


# clé logique -> (fichier, poids variable souhaité ou None)
FONT_FILES = {
    "impact":   ("Anton.ttf", None),                 # condensé ultra-gras, remplit les formes
    "block":    ("ArchivoBlack-Regular.ttf", None),  # sans très gras
    "tall":     ("BebasNeue-Regular.ttf", None),     # capitales hautes condensées
    "cond":     ("Oswald-Bold.ttf", 700),            # condensé gras
    "fjalla":   ("FjallaOne-Regular.ttf", None),     # sans medium condensé
    "fatserif": ("AbrilFatface.ttf", None),          # serif gras élégant (didone)
    "elegant":  ("PlayfairDisplay-Bold.ttf", 800),   # serif contrasté chic
    "marker":   ("PermanentMarker.ttf", None),       # marqueur manuscrit
    "hand":     ("Caveat-Bold.ttf", 700),            # manuscrit fluide
    "comic":    ("Bangers-Regular.ttf", None),       # capitales BD punchy
    "script":   ("Pacifico.ttf", None),              # script rond, coulant
    "brush":    ("Kaushan_Script.ttf", None),        # pinceau penché
    "retro":    ("Lobster.ttf", None),               # script rétro enseigne
    "mono":     ("SpaceMono-Bold.ttf", None),        # mono « terminal », clin d'œil geek
    "code":     ("JetBrainsMono-Bold.ttf", 800),     # mono dev moderne
    "geo":      ("Poppins-Bold.ttf", None),          # géométrique rond, épuré tendance
    "sora":     ("Sora-Bold.ttf", 700),              # grotesk moderne épuré
}

# repli système si un fichier manque (ne devrait pas arriver après le download CI)
_FALLBACK = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def font_path(key):
    fn = FONT_FILES.get(key, FONT_FILES["impact"])[0]
    p = os.path.join(FONT_DIR, fn)
    if os.path.isfile(p):
        return p
    for f in _FALLBACK:
        if os.path.isfile(f):
            return f
    return p  # laisse Pillow lever une erreur explicite


def load_font(key, size):
    """ImageFont calé au bon poids (polices variables incluses)."""
    f = ImageFont.truetype(font_path(key), int(size))
    weight = FONT_FILES.get(key, (None, None))[1]
    if weight is not None:
        try:
            axes = f.get_variation_axes()
            names = [(a["name"].decode() if isinstance(a["name"], bytes)
                      else a["name"]) for a in axes]
            vals = []
            for n, a in zip(names, axes):
                if n.lower() == "weight":
                    vals.append(weight)
                else:
                    vals.append(a.get("default", a.get("minimum", 0)))
            f.set_variation_by_axes(vals)
        except Exception:
            pass  # police statique : on garde tel quel
    return f
