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
- [x] **Brique A — Gate d'approbation + garde-fou dépense** : `ApprovalGate`, manifest JSON, coût estimé affiché, `--yes` pour CI
- [x] **Brique B — Validation externe** : `WebSignalFetcher` (2 appels Gemini batchés, grounding Etsy + signaux web) → MEASURED si grounding confirmé
- [x] **Brique C — Génération image** : `GenerationPipeline.run_brief()` — N images depuis le prompt du CdC directement
- [x] **Brique D — Audit qualité** : `QualityAuditor` (netteté Laplacian + seamless bords + specs Spoonflower, retry auto 2×)
- [x] **Brique E — Upscaling + packaging Spoonflower** : Runware ×4 + `SpoonflowerPackager` (PNG 300 DPI, 4500×4500, sRGB, ≤ 40 MB)
- [x] Persistance briefs (prompts sauvegardés en JSON) — `generate` ne relance pas Gemini
- [x] Repos open-source identifiés et vérifiés (voir BACKLOG.md)

## 🔜 Prochaine brique (vers la 1re vente)

- [ ] **Brique F — Génération titre/description/tags SEO** prêts à uploader (upload manuel)
  - `title_seeds` et `seo_keywords` déjà dans les CdCs, à formatter
  - Titre Spoonflower ≤ 60 chars, description ~200 mots, 10-15 tags
  - → **Première mise en vente manuelle sur Spoonflower**

## 🛠️ Après les premières ventes

- [ ] **Brique G — Intégration repos** : `trend-pulse` (37 sources → `growth_metric` MEASURED), `etsyv3` (listing counts → `competition_metric` MEASURED), `trendspyg` (remplace pytrends archivé)
- [ ] **Brique H — Result Tracking** : saisie ventes/revenus/délai 1re vente → retour dans `HistoryStore`
- [ ] **Brique I — Variant Engine** : 1 motif → N colorways Spoonflower (sauge, terracotta, crème, marine…)
- [ ] **Brique J — Knowledge Base** : boucle ventes → score. Chaque publication = expérience. Moteur de prédiction.
- [ ] **Brique K — Collection Engine** : unité stratégique = collection (principale + complémentaires + saisonnière), pas l'image isolée
- [ ] **Brique L — Platform Intelligence Bot** : analyse auto des specs/best-sellers d'une plateforme avant lancement
- [ ] **Brique M — Business Intelligence Agent** : identifie de nouveaux débouchés (nouvelles plateformes, KDP, B2B licences…)
- [ ] **Brique N — Tool Intelligence Agent** : monitore les nouveaux repos/APIs utiles au business
- [ ] **Brique O — Extension multi-plateformes** (Etsy listings, Creative Market, KDP…)

## Règle de progression

Chaque brique est : **construite → testée → validée par Hugo → commitée → seulement ensuite la suivante.**
