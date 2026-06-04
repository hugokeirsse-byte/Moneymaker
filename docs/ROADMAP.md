# 🧱 Feuille de Route — Brique par Brique

> On avance pas à pas. Objectif immédiat : **premiers produits Spoonflower en vente.**

## ✅ Fait

- [x] Moteur de détection de tendances (Gemini 3.x + Google Search, auto-découverte du modèle)
- [x] Arbre de niches (159 nœuds) + normalisation
- [x] Scoring d'opportunité **explicable** (6 composantes) + **confiance** + provenance MESURÉ/HEURISTIQUE
- [x] Ciblage anti-saturation (demande × rareté concurrence), exclusion des génériques
- [x] CdC complets (palette hex, références, images Wikimedia, prompts 120-180 mots + négatif)
- [x] Auto-critique Gemini (2ᵉ passe qui resserre les angles)
- [x] `MarketProfile` scalable (ajouter un marché = ajouter un profil)
- [x] Historique des détections (`HistoryStore`)
- [x] Fallback sans Gemini (Wikipedia + arbre de niches, 0 clé / 0 coût)
- [x] Mode `preview` (0 €) validé sur GitHub Actions
- [x] Documentation / plan directeur (ce dossier)

## 🔜 En cours / prochaine brique (vers la 1re vente)

- [ ] **Brique A — Verrous de dépense + gate d'approbation CdC** *(protège la carte)*
  - plafond dur du nombre d'images (centralisé, infranchissable)
  - aucune génération sans approbation explicite des CdC (manifeste + input `confirm: YES`)
  - estimation de coût affichée avant tout appel payant
- [ ] **Brique B — Audit qualité CdC & prompts** (rejet auto de ce qui est faible)
- [ ] **Brique C — Génération image (Runware) + audit image** (5 images, top niches)
- [ ] **Brique D — Variantes couleurs Spoonflower** (un motif → plusieurs colorways)
- [ ] **Brique E — Upscaling + packaging Spoonflower** (PNG 300 DPI, 4500×4500, sRGB)
- [ ] **Brique F — Génération titre/description/tags** prêts à uploader (upload manuel)
- [ ] → **Première mise en vente manuelle sur Spoonflower**

## 🛠️ Après les premières ventes

- [ ] **Brique G — Result Tracking** : saisie ventes/revenus/délai 1re vente
- [ ] **Brique H — Knowledge Base** : boucle ventes → score (le moteur apprend)
- [ ] **Brique I — Bot d'intelligence plateforme** : analyse auto des specs/best-sellers d'un site
- [ ] **Brique J — Détection de gaps + collections + différenciation visuelle**
- [ ] **Brique K — Extension multi-plateformes** (Etsy, Creative Market, KDP…)

## Règle de progression

Chaque brique est : **construite → testée → validée par Hugo → commitée → seulement ensuite la suivante.**
