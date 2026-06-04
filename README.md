# 🏭 Moneymaker

Moteur d'intelligence commerciale pour le print-on-demand — détecte les niches, génère les motifs, apprend des ventes réelles.

> **Vision :** pas une usine à images, mais une **infrastructure d'intelligence commerciale**
> qui détecte → produit → publie → apprend des résultats réels.
> Les motifs Spoonflower sont le premier cas d'usage. D'autres marchés suivront.

📚 **Documentation complète** → [`docs/`](docs/) *(mémoire vivante, partageable à ChatGPT/Gemini)*

---

## 🎯 Ce qui existe aujourd'hui

### Pipeline opérationnel

```
Gemini 3.x + Google Search (37 signaux)
   ↓
12 niches d'opportunité anti-saturation (demande forte × concurrence faible)
   ↓
Score 6 composantes MESURÉ/HEURISTIQUE + confiance + provenance
   ↓
CdC complets : palette hex, style, images Wikimedia, prompts 120-180 mots
   ↓
Gate d'approbation manuel → 5 images/CdC → audit qualité → PNG 300 DPI Spoonflower
```

### Architecture multi-agents (vision)

| Agent | Rôle | État |
|-------|------|------|
| **NicheIntelligenceAgent** | Détecte tendances + niches + CdC | ✅ Actif |
| **ToolIntelligenceAgent** | Monitore les nouveaux outils/repos utiles | ⬜ Backlog |
| **BusinessIntelligenceAgent** | Identifie nouveaux marchés & débouchés | ⬜ Backlog |
| **PlatformIntelligenceAgent** | Analyse auto specs/best-sellers d'une plateforme | ⬜ Backlog |
| **CollectionEngine** | Stratégie de collection (groupe + variantes couleur) | ⬜ Backlog |

---

## 🔑 Clés API

Deux clés suffisent pour le pipeline complet :

| Clé | Usage | Coût | Obtenir |
|-----|-------|------|---------|
| `GEMINI_API_KEY` | Recherche de tendances + Google Search grounding + CdC | Facturation Google (négligeable) | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) |
| `RUNWARE_API_KEY` | Génération + upscaling d'images | ~0,006 €/image (prépayé, 0 surprise) | [runware.ai](https://runware.ai) |

> ⚠️ `RUNWARE_API_KEY` n'est **jamais** injectée automatiquement — seulement en mode `generate`
> après approbation explicite des CdC. Gate d'approbation obligatoire.

### Sources gratuites complémentaires (sans clé)

- **Wikipedia Pageviews** — demande + croissance MESURÉES. Actif par défaut.
- **Wikimedia Commons** — images de référence domaine public.
- **Google Search via Gemini grounding** — signaux web réels (Etsy, Pinterest, tendances).

### Clés optionnelles pour données supplémentaires

| Clé | Données supplémentaires |
|-----|------------------------|
| `ETSY_API_KEY` | Listing counts officiels Etsy (concurrence MESURÉE) |
| `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` | Buzz communautaire réel |
| `YOUTUBE_API_KEY` | Demande vidéo / tutos |
| `DATAFORSEO_LOGIN` + `DATAFORSEO_PASSWORD` | Volumes Google mensuels absolus |

---

## 🚀 Utilisation

```bash
pip install -r requirements.txt
cp .env.example .env   # GEMINI_API_KEY + RUNWARE_API_KEY

# 1. Découverte + CdC (0 €)
python -m trend_discovery.main preview
# → reports/cahiers_des_charges_YYYYMMDD_HHMM.md
# → data/approvals/pending_RUNID.json  (à éditer)

# 2. Approuver les CdCs
# Ouvrir data/approvals/pending_RUNID.json
# Mettre "approved": true sur les niches choisies

# 3. Générer les images (payant — ~0,03 €/CdC × 5 images)
python -m trend_discovery.main generate --yes
# → output/spoonflower/*.png (PNG 300 DPI, ≥ 4500×4500, sRGB)

# Options avancées
python -m trend_discovery.main preview --niches 8 --exclude "florals" --focus "dark academia"
python -m trend_discovery.main generate --approve "Gothic Cabinet,Heirloom Potager" --images 5
```

---

## 🤖 GitHub Actions

Lancement **manuel uniquement** (crons désactivés tant que le système n'est pas validé) :

```
Actions → Module 01 → Run workflow
  mode: preview    → CdC + manifest (0 €)
  mode: generate   → images des CdCs approuvées (RUNWARE_API_KEY requise)
```

Les rapports + manifest + images sont commités automatiquement dans la branche.

---

## 🏗️ Modules (état juin 2026)

| # | Module | État |
|---|--------|------|
| 1 | Collectors | 🟡 Gemini+Search ✅, Wikipedia ✅, WebSignalFetcher ✅. trend-pulse/etsyv3 = prochaine intégration |
| 2 | Normalizer | ✅ Arbre 159 nœuds + fusion synonymes |
| 3 | Trend Engine | ✅ Gemini 3.x auto-découverte + anti-saturation |
| 4 | Hybridation | 🟡 Existant, à reconnecter |
| 5 | Scoring | ✅ 6 composantes + confiance + MEASURED/HEURISTIC/UNAVAILABLE |
| 6 | Platform Intelligence | 🟡 MarketProfile Spoonflower ✅, bot auto ⬜ |
| 7 | Brief Generator | ✅ CdC complets + ApprovalGate + persistance briefs |
| 8 | Image Generation | ✅ run_brief() N images/CdC + gate d'approbation |
| 9 | Variant Engine | ⬜ 1 motif → N colorways Spoonflower |
| 10 | Quality Control | ✅ QualityAuditor : netteté + seamless + specs |
| 11 | Upscaling | ✅ Runware ×4 + SpoonflowerPackager 300 DPI |
| 12 | Publication | ⬜ Titre/description/tags SEO (prochaine brique) |
| 13 | Result Tracking | 🟡 HistoryStore détections ✅, ventes ⬜ |
| 14 | Knowledge Base | ⬜ Boucle ventes → score (long terme) |

---

## 🧭 Principe fondamental : zéro donnée inventée

| Tag | Signification |
|-----|---------------|
| 🟢 `MEASURED` | Vraie source externe (API, scraping avec grounding confirmé) |
| 🟡 `HEURISTIC` | Estimation basée sur règle interne ou opinion Gemini |
| 🔴 `UNAVAILABLE` | Donnée non disponible — le système le dit explicitement |

Le **score de fiabilité** de chaque CdC = % du score basé sur des données MEASURED.
Cible : maximum de MEASURED, minimum de HEURISTIC. L'intégration de repos open-source
(trend-pulse, etsyv3, trendspyg) est le levier principal pour y arriver.

---

## 📦 Repos open-source intégrés / à intégrer

Le principe : **ne pas réinventer la roue**. Si un repo public existe et est maintenu,
on l'utilise plutôt que de recoder.

| Priorité | Repo | Ce qu'il apporte |
|----------|------|-----------------|
| 🔴 Urgent | [trendspyg](https://github.com/flack0x/trendspyg) | Remplace pytrends (archivé avril 2025) |
| 🔴 Urgent | [trend-pulse](https://github.com/claude-world/trend-pulse) | 37 sources agrégées + lifecycle EMERGING→DECLINING |
| 🟡 Court terme | [etsyv3](https://github.com/anitabyte/etsyv3) | API officielle Etsy → listing counts MEASURED |
| 🟡 Court terme | [crawlee-python](https://github.com/apify/crawlee-python) | Scraping anti-détection universel (9k ⭐) |
| 🟡 Court terme | [seo-keyword-research-tool](https://github.com/chukhraiartur/seo-keyword-research-tool) | Google Autocomplete → longue traîne sans clé |

Voir [docs/BACKLOG.md](docs/BACKLOG.md) pour la liste complète et le plan d'intégration.

---

## 📁 Structure du code

```
trend_discovery/
├── provenance.py            # Metric : MEASURED / HEURISTIC / UNAVAILABLE
├── markets/                 # MarketProfile — scalabilité multi-plateforme
├── providers/               # Gemini, Wikipedia, Wikimedia, Reddit, Etsy…
├── research/                # OpportunityValidator, WebSignalFetcher, HistoryStore
├── generators/              # BriefGenerator, RunwareGenerator, GenerationPipeline,
│                            # QualityAuditor, SpoonflowerPackager, ApprovalGate
├── normalizer/              # NicheTree (159 nœuds), ConceptMerger
├── analyzers/               # TrendScorer, HybridScorer, OpportunityScorer
├── platform_router/         # Allocation multi-plateformes
├── database/                # OpportunityStore SQLite, HistoryTracker
└── main.py                  # CLI : preview | generate | (legacy pipeline)
```
