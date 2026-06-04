# 🧵 Intelligence Plateforme — Spoonflower

> Tout ce qu'on sait des spécificités Spoonflower pour en tirer le meilleur parti.
> À enrichir en continu (idéalement par un bot d'analyse auto — voir BACKLOG).

## Specs techniques d'export

| Paramètre | Valeur |
|-----------|--------|
| Format | PNG |
| Résolution | **300 DPI** |
| Taille mini | **4500 × 4500 px** (= 15″ × 15″ à 300 DPI) |
| Profil couleur | sRGB |
| Poids max | ~40 MB |
| Motif | **seamless** (tuile parfaite, sans couture visible) |

## Produits vendus (un design → plusieurs produits)

- Tissu : quilting cotton, apparel fabric
- **Papier peint** (vendu **par panneau**, ex. 129 $/panneau — fort ticket)
- Gift wrap (papier cadeau)
- Home decor : rideaux, linge de table, literie
- Bébé / nursery

## ⭐ Spécificité clé : les VARIANTES DE COULEUR (colorways)

Un même motif peut être proposé en **plusieurs versions de couleur** sur une seule
fiche produit (sélecteur « COLOR »). Exemple observé : un papier peint feuillage
botanique décliné en **3 colorways** — vert sombre, mauve/brun fané, terracotta.

**Implication produit** → notre **Variant Engine** (Module 9) doit générer
automatiquement les déclinaisons couleurs les plus pertinentes d'un motif
(ex : sauge, terracotta, crème, bleu marine, noir & or). Une idée = plusieurs
opportunités de vente sans recommencer le design.

## Ce qui marche sur Spoonflower (à valider/enrichir par données)

- Motifs **seamless** propres, à l'échelle adaptée au produit (petite échelle = quilting/apparel, plus grande = papier peint)
- Esthétiques déco maison & couture (botanique, vintage, cottagecore, grandmillennial…)
- Cohérence de **collection** (plusieurs motifs assortis) favorisée par la plateforme
- Variations de couleurs (cf. ci-dessus)

## À surveiller / signaux à rechercher

- **Spoonflower Design Challenges** (thèmes hebdo) → révèlent ce que la marketplace pousse
- Tris « popular » / « newest », bestsellers, tags trending
- Densité visuelle moyenne, tailles de répétition fréquentes
- Tendances déco/mode externes (sites tendances papier peint & maison) qui influencent les acheteurs

## ⚠️ Points d'attention

- Ne pas surcharger une niche déjà saturée (le scoring pénalise déjà la concurrence)
- Respecter strictement les specs (sinon rendu/impression dégradés)
- Vérifier la tuile (pas de couture visible) avant publication → audit qualité (Module 10)

## TODO intelligence plateforme

- [ ] Bot d'analyse automatique des specs & best-sellers Spoonflower (rapport complet réutilisé par le BriefGenerator)
- [ ] Recherche des motifs « du moment » / top vendeurs pour s'en inspirer (sans copier)
- [ ] Mapper chaque niche → meilleurs produits Spoonflower + colorways recommandés
