# 🏭 Moneymaker

Moteur d'intelligence commerciale pour le print-on-demand — détecte les niches, génère les motifs, prépare les uploads.

> **Vision :** pas une usine à images, mais une **infrastructure d'intelligence commerciale**
> qui détecte → produit → publie → apprend des résultats réels.
> Les motifs Spoonflower sont le premier cas d'usage. Redbubble, Adobe Stock et Etsy s'y ajoutent.

📚 **Documentation complète** → [`docs/`](docs/) *(mémoire vivante)*

---

## 🎯 Ce qui existe aujourd'hui

### Pipeline opérationnel

```
Gemini 2.5 Flash + Google Search grounding (temps réel)
   ↓
12–20 niches d'opportunité — demande forte × concurrence faible × sous-niches documentées
   ↓
Score 6 composantes MESURÉ/HEURISTIQUE + fiabilité + provenance
   ↓
CdC complets : palette hex, style A–F, images Wikimedia, prompts FLUX 130-180 mots
   ↓
Génération Runware FLUX.1 Dev 1024×1024 → upscale IA ×4 → PNG 4500×4500 300 DPI
   ↓
Colorize automatique — 4 palettes HSV par image
   ↓
Listings prêts : Spoonflower CSV + Adobe Stock keywords + Etsy bundles + Redbubble tags
```

### Plateformes supportées

| Plateforme | Découverte | Génération | Listings | Statut |
|-----------|-----------|-----------|---------|--------|
| **Spoonflower** | ✅ preview | ✅ generate-all | ✅ CSV + Markdown | Actif |
| **Redbubble** | ✅ redbubble-preview | ✅ redbubble-generate | ✅ CSV | Actif |
| **Adobe Stock** | ✅ adobe-stock-preview | ✅ adobe-stock-generate | ✅ 50 keywords CSV | Prêt |
| **Etsy Downloads** | ✅ etsy-preview | ✅ etsy-generate | ✅ Bundle CSV | Prêt |

---

## 🔑 Clés API

Deux clés suffisent pour le pipeline complet :

| Clé | Usage | Coût | Obtenir |
|-----|-------|------|---------|
| `GEMINI_API_KEY` | Recherche tendances + Google Search grounding + CdC | Facturation Google (négligeable) | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) |
| `RUNWARE_API_KEY` | Génération FLUX.1 Dev + upscale IA Real-ESRGAN ×4 | ~0,006 €/image finale (prépayé) | [runware.ai](https://runware.ai) |

> ⚠️ `RUNWARE_API_KEY` n'est **jamais** injectée automatiquement — seulement dans les modes
> `generate`, `generate-all`, `generate-best`, `generate-elements`, `redbubble-generate`,
> `adobe-stock-generate`, `etsy-generate`, `upscale-fix`. Aucun coût en preview/audit.

### Sources gratuites (sans clé)

- **Wikipedia Pageviews** — demande MESURÉE. Actif par défaut.
- **Wikimedia Commons** — images de référence domaine public.
- **Google Search via Gemini grounding** — signaux web réels (Etsy, Pinterest, tendances).

### Clés optionnelles

| Clé | Données supplémentaires |
|-----|------------------------|
| `ETSY_API_KEY` | Listing counts officiels Etsy (concurrence MESURÉE) |
| `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` | Buzz communautaire réel |
| `YOUTUBE_API_KEY` | Demande vidéo / tutos |
| `DATAFORSEO_LOGIN` + `DATAFORSEO_PASSWORD` | Volumes Google mensuels absolus |

---

## 🚀 Utilisation locale

```bash
pip install -r requirements.txt
cp .env.example .env   # GEMINI_API_KEY + RUNWARE_API_KEY

# 1. Découverte + CdC Spoonflower (0 €)
python -m trend_discovery.main preview
python -m trend_discovery.main preview --market redbubble --output ./reports/redbubble
python -m trend_discovery.main preview --market adobe_stock --output ./reports/adobe_stock
python -m trend_discovery.main preview --market etsy --output ./reports/etsy

# 2. Générer les images (~0,006 €/image)
python -m trend_discovery.main generate-all --yes
python -m trend_discovery.main generate-all --yes --report reports/redbubble/cahiers_des_charges_*.json --output output/redbubble

# 3. Coloriser (0 €, Pillow)
python -m trend_discovery.main colorize --yes --input output/spoonflower --output output/colorways

# 4. Générer les listings (0 €)
python -m trend_discovery.main listings

# 5. Vignettes navigables (0 €)
python -m trend_discovery.main thumbnails
```

---

## 🤖 GitHub Actions

Lancement **manuel uniquement** (`Actions → Module 01 → Run workflow`) :

| Mode | Description | Coût |
|------|-------------|------|
| `preview` | Gemini trends + CdC Spoonflower | 0 € |
| `redbubble-preview` | CdC standalone Redbubble | 0 € |
| `adobe-stock-preview` | CdC optimisés Adobe Stock | 0 € |
| `etsy-preview` | CdC digital download Etsy | 0 € |
| `generate-all` | 1 image base par CdC Spoonflower | ~0,006 €/img |
| `redbubble-generate` | Images standalone Redbubble | ~0,006 €/img |
| `adobe-stock-generate` | Images pour Adobe Stock | ~0,006 €/img |
| `etsy-generate` | Images pour bundles Etsy | ~0,006 €/img |
| `colorize` | 4 variantes couleur + thumbnails auto | 0 € |
| `listings` | CSVs upload toutes plateformes | 0 € |
| `thumbnails` | Vignettes 600×600 JPEG navigables | 0 € |
| `audit` | Score /100 Gemini Vision par image | 0 € |
| `seamless-audit` | Vérification + correction tuiles | 0 € |
| `upscale-fix` | Re-upscale IA images existantes | ~0,005 €/img |
| `generate-best` | Variantes du meilleur CdC | ~0,05 € |
| `generate-elements` | 10 éléments isolés + assemblage | ~0,06 € |
| `archive` | Archive un CdC + régénère un remplaçant | 0 € |

**Inputs disponibles :**
- `focus` : orientation thématique (ex: `Art Deco animals, no vintage`) — vide = découverte organique
- `niche_count` : override du nombre de niches (ex: `16`)
- `limit` : limite le nombre d'images générées
- `palettes` : palettes colorize (ex: `dark_moody,pastel_soft`) — vide = toutes les 4

---

## 🏗️ Modules (état juin 2026)

| # | Module | État |
|---|--------|------|
| 1 | Collectors | 🟡 Gemini+Search ✅, Wikipedia ✅, WebSignalFetcher ✅ |
| 2 | Normalizer | ✅ Arbre 159 nœuds + fusion synonymes |
| 3 | Trend Engine | ✅ Gemini 2.5 Flash + Google Search grounding + anti-saturation |
| 4 | Hybridation | 🟡 Existant, à reconnecter |
| 5 | Scoring | ✅ 6 composantes + fiabilité + MEASURED/HEURISTIC/UNAVAILABLE |
| 6 | Platform Intelligence | ✅ MarketProfile × 4 (Spoonflower, Redbubble, Adobe Stock, Etsy) |
| 7 | Brief Generator | ✅ CdC complets + sub-niches + ApprovalGate + niche archive |
| 8 | Image Generation | ✅ FLUX.1 Dev 1024→4500px + gate d'approbation |
| 9 | Variant Engine | ✅ Colorize 4 palettes HSV (cool_ocean, earth_autumn, midnight, rose_gold) |
| 10 | Quality Control | ✅ QualityAuditor : netteté + seamless + specs Spoonflower |
| 11 | Upscaling | ✅ Runware Real-ESRGAN ×4 + SpoonflowerPackager 300 DPI |
| 12 | Publication | ✅ ListingGenerator : CSV Spoonflower + Adobe Stock + Etsy + Redbubble |
| 13 | Result Tracking | 🟡 HistoryStore détections ✅, ventes ⬜ |
| 14 | Knowledge Base | ⬜ Boucle ventes → score (long terme) |

---

## 🎨 Styles de génération (A–F)

| Style | Description | Cas d'usage |
|-------|-------------|-------------|
| **A** | Scattered/tossed — éléments isolés sur fond uni | Curiosités, stationery, botaniques épars |
| **B** | Large hero motif — 1-3 formes dominantes, 2-3 couleurs max | Feuille tropicale, fleur oversized, bold repeat |
| **C** | Animal Deco — 1 seul animal centré, Spoonflower mirror crée le motif | Art Deco héron, koi, papillon |
| **D** | Narratif/Humour — animaux anthropomorphisés, trompe-l'œil étagères | Grenouilles sommelières, détectives ratons |
| **E** | Trompe-l'œil réaliste — arche/fenêtre vers paysage photoréaliste | Forêt à travers une arche, jardin japonais |
| **F** | Réaliste épars — spécimens naturalistes sur fond sombre | Terrarium, pierres géologiques, fond marin |

---

## 🧭 Principe fondamental : zéro donnée inventée

| Tag | Signification |
|-----|---------------|
| 🟢 `MEASURED` | Vraie source externe (API, scraping avec grounding confirmé) |
| 🟡 `HEURISTIC` | Estimation basée sur règle interne ou opinion Gemini |
| 🔴 `UNAVAILABLE` | Donnée non disponible — le système le dit explicitement |

Le **score de fiabilité** de chaque CdC = % du score basé sur des données MEASURED.

---

## 📦 Repos open-source intégrés / à intégrer

| Priorité | Repo | Ce qu'il apporte |
|----------|------|-----------------|
| 🔴 Urgent | [trendspyg](https://github.com/flack0x/trendspyg) | Remplace pytrends (archivé avril 2025) |
| 🔴 Urgent | [trend-pulse](https://github.com/claude-world/trend-pulse) | 37 sources agrégées + lifecycle EMERGING→DECLINING |
| 🟡 Court terme | [etsyv3](https://github.com/anitabyte/etsyv3) | API officielle Etsy → listing counts MEASURED |
| 🟡 Court terme | [crawlee-python](https://github.com/apify/crawlee-python) | Scraping anti-détection universel |
| 🟡 Court terme | [seo-keyword-research-tool](https://github.com/chukhraiartur/seo-keyword-research-tool) | Google Autocomplete → longue traîne sans clé |

---

## 📁 Structure du code

```
trend_discovery/
├── provenance.py            # Metric : MEASURED / HEURISTIC / UNAVAILABLE
├── markets/
│   └── market_profile.py    # MarketProfile × 4 plateformes (Spoonflower, Redbubble, Adobe Stock, Etsy)
├── providers/               # GeminiProvider, WikipediaProvider, WikimediaProvider, RedditProvider…
├── research/                # OpportunityValidator, WebSignalFetcher, HistoryStore
├── generators/
│   ├── production_brief.py  # BriefGenerator — CdC complets depuis Gemini
│   ├── listing_generator.py # CSVs upload toutes plateformes (0 €)
│   ├── generation_pipeline.py  # Orchestration génération + upscale
│   ├── runware_generator.py # FLUX.1 Dev 1024px + Real-ESRGAN ×4
│   ├── color_rewriter.py    # Colorize HSV (4 palettes)
│   ├── thumbnail_generator.py  # Vignettes 600×600 JPEG
│   ├── quality_auditor.py   # Netteté + seamless + specs
│   ├── seamless_auditor.py  # Correction tuiles (mirror quad)
│   ├── spoonflower_packager.py  # PNG 4500×4500 300 DPI sRGB
│   └── approval_gate.py     # Gate d'approbation avant génération
├── normalizer/              # NicheTree (159 nœuds), ConceptMerger
├── analyzers/               # TrendScorer, HybridScorer, OpportunityScorer
└── main.py                  # CLI : preview | generate-all | colorize | listings | thumbnails | …
```

### Sorties générées

```
reports/
├── cahiers_des_charges_*.json/.md   # CdC Spoonflower
├── redbubble/cahiers_des_charges_*  # CdC Redbubble
├── adobe_stock/                     # CdC Adobe Stock
├── etsy/                            # CdC Etsy
└── listings/
    ├── spoonflower_upload_priority_*.csv  # Toutes images triées par score
    ├── adobe_stock_keywords_*.csv          # 50 keywords + titre + catégorie
    ├── etsy_bundles_*.csv                  # Bundles digital download
    ├── redbubble_listings_*.csv            # Tags + communautés Redbubble
    └── upload_guide_*.md                   # Résumé top 10 par plateforme

output/
├── spoonflower/   # PNG 4500×4500 base (seamless, tiling=True)
├── redbubble/     # PNG 4500×4500 standalone (tiling=False)
├── adobe_stock/   # PNG 4500×4500 seamless
├── etsy/          # PNG 4500×4500 seamless
├── colorways/     # Variantes HSV Spoonflower (cool_ocean, earth_autumn, midnight, rose_gold)
├── uploads/base/  # Images uploadées manuellement
├── uploads/colorways/
└── thumbnails/    # Vignettes JPEG 600×600 navigables depuis GitHub
```
