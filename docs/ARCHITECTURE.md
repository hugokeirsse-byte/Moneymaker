# 🏗️ Architecture Globale

## Vision : une infrastructure d'intelligence, pas un générateur d'images

Le projet est structuré en **trois couches d'intelligence** qui s'alimentent mutuellement :

```
┌─────────────────────────────────────────────────────────────────┐
│  COUCHE 1 — INTELLIGENCE MARCHÉ                                  │
│  Détecte les opportunités AVANT les autres                       │
│  (Niche Intelligence Agent)                                      │
├─────────────────────────────────────────────────────────────────┤
│  COUCHE 2 — PRODUCTION                                           │
│  Transforme les opportunités en actifs commerciaux              │
│  (Image generation, quality control, platform packaging)        │
├─────────────────────────────────────────────────────────────────┤
│  COUCHE 3 — APPRENTISSAGE                                        │
│  Ferme la boucle : résultats réels → améliore la détection       │
│  (Result tracking, knowledge base, prediction engine)           │
└─────────────────────────────────────────────────────────────────┘
```

## Architecture multi-agents (vision)

Le système n'est pas un seul agent mais **plusieurs agents spécialisés** qui coexistent :

| Agent | Rôle | État |
|-------|------|------|
| **NicheIntelligenceAgent** | Détecte les tendances, niches, sous-niches ; score d'opportunité ; CdC complets | ✅ En prod |
| **ToolIntelligenceAgent** | Monitore les nouveaux outils/repos open-source utiles au business (GitHub, PyPI, HN…) et évalue leur intégration | ⬜ Backlog |
| **BusinessIntelligenceAgent** | Identifie de nouveaux débouchés commerciaux (nouvelles plateformes, nouveaux formats, marchés B2B) | ⬜ Backlog |
| **PlatformIntelligenceAgent** | Analyse automatiquement les specs, best-sellers et tendances d'une plateforme avant lancement | ⬜ Backlog |
| **CollectionEngine** | Stratégie de collection : quels motifs grouper, dans quel ordre, avec quelles variantes couleur | ⬜ Backlog |

> **Principe :** chaque agent produit des données structurées qui alimentent le **scoring** et les **CdC**. Pas juste des rapports — des données intégrées dans le calcul.

## Pipeline de production (Couche 2)

```
COLLECTORS            Gemini+Google Search ✅  Wikipedia ✅  Wikimedia ✅
                      trend-pulse (37 sources) 🔜  etsyv3 🔜  trendspyg 🔜
   ↓                  → données MESURÉES qui alimentent le scoring
NORMALIZER            fusion synonymes, taxonomie, arbre de niches ✅
   ↓
TREND ENGINE          Gemini 3.x auto-découverte + anti-saturation ✅
                      WebSignalFetcher (grounding Etsy + signaux web) ✅
   ↓
HYBRIDATION ENGINE    combinaisons rares & cohérentes 🟡
   ↓
SCORING ENGINE        OpportunityValidator : 6 composantes + confiance ✅
                      Metric MESURÉ / HEURISTIQUE / UNAVAILABLE ✅
   ↓
PLATFORM INTELLIGENCE MarketProfile déclaratif ✅  Bot auto ⬜
   ↓
BRIEF GENERATOR       CdC complets + prompts 120-180 mots + Wikimedia ✅
                      ApprovalGate (manifest JSON + persistance briefs) ✅
   ↓
IMAGE GENERATOR       RunwareGenerator (génération + upscale ×4) ✅
                      run_brief() : N images par CdC approuvée ✅
   ↓
QUALITY CONTROL       QualityAuditor : netteté + seamless + specs SF ✅
   ↓
UPSCALING             Runware ×4 → SpoonflowerPackager (300 DPI, sRGB) ✅
   ↓
VARIANT ENGINE        1 motif → N colorways Spoonflower ⬜
   ↓
EXPORT / PUBLICATION  titre + description + tags SEO ⬜
   ↓
RESULT TRACKING       HistoryStore (détections) ✅  ventes/revenus ⬜
   ↓
KNOWLEDGE BASE        boucle ventes → score ⬜  (cœur de valeur long terme)
```

## État des modules

Légende : ✅ fait · 🟡 partiel · ⬜ à faire

| # | Module | État | Notes |
|---|--------|------|-------|
| 1 | Collectors | 🟡 | Gemini+Google Search ✅, Wikipedia ✅, Wikimedia ✅, WebSignalFetcher ✅. trend-pulse / etsyv3 / trendspyg = prochaines intégrations pour données MESURÉES. |
| 2 | Normalizer | ✅ | Arbre de niches (159 nœuds, anglais) + fusion de concepts. |
| 3 | Trend Engine | ✅ | Gemini 3.x auto-découverte + Google Search. Anti-saturation, exclusion des génériques. |
| 4 | Hybridation Engine | 🟡 | Phase 4 existante. À reconnecter au nouveau moteur Gemini. |
| 5 | Scoring Engine | ✅ | `OpportunityValidator` : score 6 composantes explicable + confiance + provenance. WebSignalFetcher → MEASURED si grounding confirmé. |
| 6 | Platform Intelligence | 🟡 | `MarketProfile` déclaratif et scalable ✅. Profil Spoonflower ✅. Bot d'analyse auto = ⬜. |
| 7 | Brief Generator | ✅ | CdC complets : direction visuelle, palette hex, références Wikimedia, prompts 120-180 mots, SEO seeds, `ApprovalGate` ✅. |
| 8 | Image Generation | ✅ | `RunwareGenerator` + `run_brief()` (N images/CdC) ✅. Gate d'approbation + coût estimé avant run ✅. |
| 9 | Variant Engine | ⬜ | Un motif → plusieurs colorways Spoonflower (sauge, terracotta, crème, marine, noir & or). |
| 10 | Quality Control | ✅ | `QualityAuditor` : netteté (Laplacian), seamless (comparaison bords), specs Spoonflower. Retry auto. |
| 11 | Upscaling | ✅ | Runware ×4 + `SpoonflowerPackager` (PNG 300 DPI, 4500×4500 min, sRGB, ≤ 40 MB). |
| 12 | Publication | ⬜ | Génération titre/description/tags prêts à uploader. Upload manuel pour commencer. |
| 13 | Result Tracking | 🟡 | `HistoryStore` (détections) ✅. Ventes/revenus = ⬜ (saisie manuelle d'abord, puis automatisation). |
| 14 | Knowledge Base | ⬜ | Boucle ventes → score. Chaque publication = expérience. Cœur stratégique long terme. |

## Intégration des repos open-source dans le pipeline

> Les repos ne sont pas que des outils listés dans le backlog — ils doivent **alimenter le scoring** et les **CdC** avec des données MESURÉES.

| Repo | Intégration cible | Composante scoring |
|------|-------------------|--------------------|
| [trend-pulse](https://github.com/claude-world/trend-pulse) | Nouveau Collector → lifecycle EMERGING/PEAK/DECLINING | `growth_metric` MEASURED |
| [etsyv3](https://github.com/anitabyte/etsyv3) | Competitor data → listing count par niche | `competition_metric` MEASURED |
| [wordsy_python](https://github.com/interwebologist/wordsy_python) | Tag frequency → demand evidence réelle | `demand_metric` MEASURED |
| [trendspyg](https://github.com/flack0x/trendspyg) | Remplaçant pytrends → Google Trends scores | `demand_metric` MEASURED |
| [seo-keyword-research-tool](https://github.com/chukhraiartur/seo-keyword-research-tool) | Expansion mots-clés → enrichit les prompts CdC | `seo_keywords` dans brief |
| [crawlee-python](https://github.com/apify/crawlee-python) | Couche scraping anti-403 pour Etsy + Pinterest | Remplace scrapers bloqués |

## Implémentation actuelle (code)

- `trend_discovery/markets/` — MarketProfile (scalabilité multi-plateforme)
- `trend_discovery/providers/` — Gemini, Wikipedia, Wikimedia, Reddit, YouTube, Etsy, DataForSEO
- `trend_discovery/research/` — OpportunityValidator, WebSignalFetcher, HistoryStore
- `trend_discovery/generators/` — BriefGenerator, ProductionBrief, PromptBuilder, RunwareGenerator, SpoonflowerPackager, GenerationPipeline, QualityAuditor, ApprovalGate
- `trend_discovery/normalizer/` — NicheTree, ConceptMerger
- `trend_discovery/provenance.py` — Metric / ProvenanceLedger (zéro donnée inventée)
- `trend_discovery/main.py` — CLI : sous-commandes `preview` et `generate`
