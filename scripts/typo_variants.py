#!/usr/bin/env python3
"""
typo_variants.py — adaptation des couleurs au fond du maillot.

Deux variantes standard pour tout le catalogue texte :
  "dark"  : encre sombre, pour maillots clairs (rendu tel quel)
  "light" : encre claire, pour maillots foncés

Règle : seules les couleurs NEUTRES sombres (noir, gris foncé) basculent en
clair ; les couleurs saturées (rouge, bleu, vert, prune…) restent identiques —
elles se lisent aussi bien sur clair que sur foncé.
"""

INK_DARK = (30, 30, 34, 255)
INK_LIGHT = (244, 244, 246, 255)
VARIANTS = ("dark", "light")


def adapt(color, variant):
    """Renvoie la couleur adaptée à la variante (RGBA)."""
    a = color[3] if len(color) > 3 else 255
    r, g, b = color[0], color[1], color[2]
    if variant == "dark":
        return (r, g, b, a)
    mx, mn = max(r, g, b), min(r, g, b)
    sat = mx - mn
    lum = 0.299 * r + 0.587 * g + 0.114 * b
    if lum < 140 and sat < 40:        # neutre sombre -> clair
        if lum < 60:
            return (244, 244, 246, a)   # quasi-noir -> blanc
        return (190, 192, 198, a)       # gris foncé -> gris clair
    return (r, g, b, a)                  # couleur saturée -> inchangée
