# 🏗️ Architecture Globale

## Pipeline cible

```
COLLECTORS            (sources marché : Gemini+web, Wikipedia, Reddit, Etsy…)
   ↓
NORMALIZER            (fusion synonymes, taxonomie, arbre de niches)
   ↓
TREND ENGINE          (niches qui montent, signaux faibles)
   ↓
HYBRIDATION ENGINE    (combinaisons rares & cohérentes)
   ↓
SCORING ENGINE        (score d'opportunité explicable + confiance)
   ↓
PLATFORM INTELLIGENCE (specs & codes de CHAQUE plateforme)
   ↓
BRIEF GENERATOR       (cahier des charges complet + prompts prêts)
   ↓
IMAGE GENERATOR       (Runware) + VARIANT ENGINE (déclinaisons couleurs)
   ↓
QUALITY CONTROL       (audit auto : netteté, seamless, défauts)
   ↓
UPSCALING             (résolution/format selon plateforme & usage)
   ↓
EXPORT / PUBLICATION  (fichier + titre + description + tags prêts)
   ↓
RESULT TRACKING       (ventes, revenus, délai 1re vente…)
   ↓
KNOWLEDGE BASE        (mémoire : hypothèses → résultats réels)
```

## État des 14 modules

Légende : ✅ fait · 🟡 partiel · ⬜ à faire

| # | Module | État | Notes |
|---|--------|------|-------|
| 1 | Collectors | 🟡 | Gemini+Google Search ✅, Wikipedia ✅, Wikimedia ✅. Reddit/YouTube/Etsy/DataForSEO = optionnels (clés). Scrapers anonymes bloqués (403 datacenter). |
| 2 | Normalizer | ✅ | Arbre de niches (159 nœuds, anglais) + fusion de concepts. |
| 3 | Trend Engine | ✅ | Gemini 3.x (auto-découverte modèle) + Google Search. Niches d'opportunité, anti-saturation. |
| 4 | Hybridation Engine | 🟡 | Phase 4 existante dans Module 01. À reconnecter au nouveau moteur. |
| 5 | Scoring Engine | ✅ | `OpportunityValidator` : score 6 composantes explicable + confiance + provenance MESURÉ/HEURISTIQUE. |
| 6 | Platform Intelligence | 🟡 | Pilier `MarketProfile` (déclaratif, scalable). Profil Spoonflower ✅. Bot d'analyse auto des specs d'un site = ⬜. |
| 7 | Brief Generator | ✅ | CdC complets : direction visuelle, palette hex, références, images Wikimedia, prompts 120-180 mots + négatif, SEO seeds. |
| 8 | Image Generation | 🟡 | `RunwareGenerator` existe. **Verrous dépense + gate d'approbation = à finaliser avant tout run payant.** |
| 9 | Variant Engine | ⬜ | Déclinaisons couleurs (spécificité Spoonflower : un motif = plusieurs colorways). |
| 10 | Quality Control | ⬜ | Audit auto des images (netteté, seamless, défauts) — « que je n'aie pas à trier des merdes ». |
| 11 | Upscaling | 🟡 | `RunwareGenerator.upscale` ×4 existe. Upscaling « intelligent » (selon plateforme) = ⬜. |
| 12 | Publication | ⬜ | Génération titre/description/tags prêts à uploader (upload manuel au début). |
| 13 | Result Tracking | 🟡 | `HistoryStore` (détections) ✅. Tracking ventes/revenus = ⬜ (saisie manuelle d'abord). |
| 14 | Knowledge Base | ⬜ | Boucle d'apprentissage ventes → score. Cœur stratégique long terme. |

## Modules transverses prévus (backlog)

- **Détection des gaps de marché** (demandé mais sous-offert)
- **Moteur de collections** (l'unité stratégique = la collection, pas l'image)
- **Différenciation visuelle** (éviter les rendus IA génériques)
- **Moteur de prédiction** (comparer une niche aux cas historiques)
- **Allocation des ressources** (combien de variantes/collections par opportunité)

Voir [BACKLOG.md](BACKLOG.md) pour le détail.

## Implémentation actuelle (code)

- `trend_discovery/markets/` — MarketProfile (scalabilité multi-plateforme)
- `trend_discovery/providers/` — Gemini, Wikipedia, Wikimedia, Reddit, YouTube, Etsy, DataForSEO
- `trend_discovery/research/` — OpportunityValidator (scoring explicable), HistoryStore
- `trend_discovery/generators/` — BriefGenerator/ProductionBrief, PromptBuilder, RunwareGenerator, SpoonflowerPackager, GenerationPipeline
- `trend_discovery/normalizer/` — NicheTree, ConceptMerger
- `trend_discovery/provenance.py` — Metric / ProvenanceLedger (zéro donnée inventée)
- `trend_discovery/main.py` — orchestration + mode `--preview-trends`
