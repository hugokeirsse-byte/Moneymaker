# 📥 Backlog — Idées d'Évolution & Pistes

> Réservoir d'idées validées comme pertinentes mais **pas encore prioritaires**.
> On les fera brique par brique, après les premiers produits Spoonflower en vente.
>
> **Principe clé :** les données externes (repos, APIs, signaux marché) ne sont pas juste
> des outils listés ici — elles doivent entrer dans le **calcul de scoring** et les **CdC**.
> Chaque nouvelle source = une nouvelle `Metric` MEASURED qui améliore la confiance.

---

## 🏗️ Roadmap stratégique — ordre de priorité

> Validé juin 2026. Source : analyse convergente (ChatGPT + sessions précédentes).

### Phase actuelle : Validation Spoonflower
Priorité absolue : valider qu'un pipeline complet produit des ventes réelles.
Détection → CdC → Image → Publication → Résultat. Tout le reste est secondaire.

### Ordre de construction recommandé

| # | Brique | Quand | Priorité |
|---|--------|-------|----------|
| 1 | **Result Tracking Engine** (Sales DNA) | Dès première publication | ★★★★★ |
| 2 | **Seasonal Engine** | Dès le pipeline stabilisé | ★★★★★ |
| 3 | **Platform Intelligence Engine** | Après validation Spoonflower | ★★★★★ |
| 4 | **Knowledge Base** | Progressivement dès maintenant | ★★★★★ |
| 5 | **Tool Intelligence Engine** | Après validation | ★★★★☆ |
| 6 | **Business Opportunity Engine** | Après validation d'au moins 1 business | ★★★★★ |
| 7 | **Expansion multi-plateformes** | Après ROI Spoonflower prouvé | ★★★☆☆ |

---

## 💾 BRIQUE 1 — Result Tracking Engine (Sales DNA)

> **Implémenter maintenant** — c'est la brique dont les données prendront de la valeur
> avec le temps. Chaque jour sans tracking = données perdues pour toujours.

### Schéma de la table principale (`opportunity_lifecycle`)

**Colonnes identité :**
- `opportunity_id` — identifiant unique format `OPP-YYYYMMDD-NNN` (ex: `OPP-20260604-001`)
- `detected_at` — timestamp de détection
- `niche` — niche principale
- `sub_niche` — sous-niche
- `market` — plateforme cible (spoonflower, etsy, society6…)

**Colonnes scoring :**
- `trend_score` — score global (/100)
- `confidence_pct` — % données MEASURED
- `score_breakdown` — JSON {demand, growth, competition, visual, reusability, platform}
- `sources_used` — JSON liste des sources

**Colonnes création :**
- `prompt` — positive_prompt utilisé
- `palette_json` — JSON {primary: [], accent: [], bg: ""}
- `style` — style visuel
- `variant_label` — "Base" / "Sub: Rocking Horse" / "Style: Dark Moody" / "Fusion: × Terrarium"
- `collection` — nom de collection éventuelle

**Colonnes coûts :**
- `cost_gemini_eur` — coût appel Gemini
- `cost_runware_eur` — coût génération image
- `generation_time_s` — durée génération

**Colonnes fichier :**
- `image_path` — chemin local PNG
- `image_url` — URL plateforme après upload

**Colonnes résultats (à remplir plus tard) :**
- `published_at` — date publication
- `product_url` — URL du produit sur la plateforme
- `views` — vues
- `favorites` — favoris
- `sales_count` — ventes
- `revenue_eur` — CA
- `first_sale_at` — date première vente
- `days_to_first_sale` — délai avant première vente

### Valeur stratégique

Cette table deviendra probablement l'actif le plus précieux du projet.
Chaque ligne = une expérience réelle qui améliore les décisions futures.

---

## 📅 BRIQUE 2 — Seasonal Engine

> Spoonflower est **très saisonnier**. Le moteur actuel analyse des tendances générales.
> Il doit aussi pousser les niches adaptées au bon moment (J-90 avant Halloween, J-120 avant Noël).

### Calendrier Spoonflower (délais de production recommandés)

| Événement | Lancement designs | Début publication | Peak |
|-----------|------------------|-------------------|------|
| Halloween (31 oct) | J-120 (fin juin) | J-90 (fin juillet) | oct |
| Noël / Hiver (déc) | J-120 (août) | J-90 (sept) | nov-déc |
| Saint-Valentin (14 fév) | J-90 (nov) | J-60 (déc) | janv-fév |
| Printemps / Pâques | J-60 (fév) | J-45 (mars) | mars-avr |
| Mariages (mai-juin) | J-90 (fév) | J-60 (mars) | avr-mai |
| Fête des mères (mai) | J-60 (mars) | J-45 (avr) | mai |
| Été / Plein air | J-60 (avr) | J-45 (mai) | juin-juil |
| Rentrée scolaire | J-60 (juin) | J-45 (juil) | août |
| Fête des pères (juin) | J-45 (avr) | J-30 (mai) | juin |

### Implémentation cible

```python
# À construire dans trend_discovery/analyzers/seasonal_scorer.py
seasonal_score = SeasonalScorer().score(niche_name, date=today)
# → {"score": 85, "peak_in_days": 47, "season": "Halloween", "urgency": "HIGH"}
```

Le `seasonal_score` s'ajoute comme 7ème composante du score global.

---

## 🧠 BRIQUE 3 — Platform Intelligence Engine

> Actuellement le moteur détecte des tendances générales.
> Il doit détecter des tendances **spécifiquement performantes sur Spoonflower**.

### Ce qu'il faut apprendre sur Spoonflower

- Palettes populaires (par catégorie, par saison)
- Densité des motifs préférée (dense vs aéré)
- Tailles de repeat performantes
- Catégories les plus vendues (quilting cotton vs apparel vs wallpaper…)
- Styles visuels dominants (watercolor, vector, hand-drawn…)
- Fréquence des colorways dans les collections qui vendent

### Platform Fit Score (à ajouter au scoring)

```
Trend Score actuel : 84/100
+ Platform Fit Score Spoonflower : /20
= Score final : /120 (normalisé /100)
```

Une même niche peut scorer différemment selon la plateforme :
- Dark Academia Herbarium → Spoonflower 95 | Etsy SVG 71 | Society6 Art Print 88

---

## 🏢 BRIQUE 4 — Business Opportunity Engine

> Différence fondamentale :
> - Trend Engine → "Que produire dans un business existant ?"
> - Business Opportunity Engine → "Quel nouveau business lancer ?"

### Marchés à surveiller

Assets jeux vidéo (Godot, Unity), découpe laser (SVG), templates professionnels (Canva, Notion),
ressources créatives (brushes, polices), printables Etsy, ressources VRChat/VTubing.

### Architecture cible (long terme)

```
                    Knowledge Base
                          │
  ┌───────────────────────┼───────────────────────┐
  │                       │                       │
Trend Engine      Platform Engine      Business Engine
  │                       │                       │
"Que produire ?"   "Comment le vendre ?"   "Quel marché lancer ?"
```

---

## Vision multi-agents

Le système n'est pas un seul agent IA mais plusieurs agents spécialisés qui coexistent :

| Agent | Rôle actuel / futur |
|-------|---------------------|
| **NicheIntelligenceAgent** | ✅ Actif — Détecte tendances, score niches, génère CdC |
| **ToolIntelligenceAgent** | ⬜ À construire — Monitore GitHub/PyPI/HN pour trouver de nouveaux outils utiles au business, évalue leur intégration, propose des améliorations |
| **BusinessIntelligenceAgent** | ⬜ À construire — Identifie de nouveaux marchés, plateformes, formats (KDP, B2B licences, packs SVG…) |
| **PlatformIntelligenceAgent** | ⬜ À construire — Analyse automatiquement les specs, best-sellers, codes promo, tendances d'une plateforme avant lancement |
| **CollectionEngine** | ⬜ À construire — Stratégie de collection : quels motifs grouper, ordre de publication, variantes couleur à prioriser |

> Ces agents partagent tous la même base de connaissances (`HistoryStore` → `KnowledgeBase`)
> et leurs sorties alimentent le scoring central.

## Moteurs à construire (au-delà de la détection)

| Idée | Description |
|------|-------------|
| **Variant Engine** | 1 concept → N variantes couleurs optimisées (sauge, terracotta, crème, marine, noir & or). Spécificité Spoonflower (colorways). |
| **Réutilisation maximale** | Chaque création analysée pour TOUS ses marchés exploitables (Spoonflower, Etsy, Creative Market, KDP, packs PNG/SVG, affiches, licences B2B). |
| **Détection de gaps** | Chercher ce qui est *demandé mais sous-offert*, pas seulement ce qui est populaire. Trouver les opportunités avant les autres. |
| **Hybridation avancée** | Combinaisons rares + cohérentes + historiquement performantes (ex : Botanique + Cartographie ancienne + Cabinet de curiosités). |
| **Moteur de collections** | L'unité stratégique devient la collection (principale, complémentaire, saisonnière), pas l'image isolée. |
| **Différenciation visuelle** | Éviter les rendus IA génériques : styles rares, mélanges de références, palettes peu utilisées, compositions atypiques. |
| **Quality Control** | Audit auto des images : netteté, cohérence, qualité seamless, densité, défauts. Filtrer les productions faibles. |
| **Upscaling intelligent** | Choisir résolution/traitement/export selon plateforme + produit + usage. |
| **Result Tracking** | Enregistrer ventes, revenus, vues, clics, délai 1re vente par création. |
| **Knowledge Base** | Mémoire hypothèses → résultats réels. Le cœur de valeur long terme. |
| **Moteur de prédiction** | Comparer une nouvelle niche à des centaines de cas historiques (« ressemble à 37 niches performantes »). |
| **Allocation des ressources** | Décider combien de variantes/collections produire, quels marchés cibler, quelles niches abandonner. |
| **Platform Intelligence Bot** | Analyse auto des specs/codes/best-sellers de CHAQUE site avant d'y lancer un business. |

## Données à conserver par création publiée (futur schéma)

**Marché** : niche, sous-niche, score, confiance, signaux utilisés, date détection.
**Créatif** : style, collection, thème, palette, prompt, version du moteur.
**Publication** : plateforme, date mise en ligne, catégorie, mots-clés.
**Résultats** : vues, clics, ventes, CA, délai 1re vente, performance globale.

## Repos open-source identifiés — résultats de recherche (juin 2026)

> Recherche effectuée et vérifiée. Classés par priorité d'intégration.

### ⚠️ Migration urgente

`pytrends` (GeneralMills) a été **archivé en avril 2025** — ne plus l'utiliser.

### 🔴 Priorité HAUTE — intégrer dès que le pipeline de base tourne

| Repo | Stars | Utilité |
|------|-------|---------|
| [trend-pulse](https://github.com/claude-world/trend-pulse) | 40 | **37 sources** agrégées (Google Trends + Reddit + Pinterest + Wikipedia + TikTok…) avec lifecycle prediction EMERGING→PEAK→DECLINING. `pip install trend-pulse`. Remplace 3-4 collectes séparées d'un coup. |
| [pytrends-modern](https://github.com/yiromo/pytrends-modern) | 29 | Remplaçant pytrends avec anti-détection Camoufox, rotation proxies, async. Résout les 403 en datacenter. |
| [trendspyg](https://github.com/flack0x/trendspyg) | 29 | Alternative pytrends async, 125+ pays, `pip install trendspyg[async]`. Activement maintenu mai 2026. |
| [trends-checker](https://github.com/akvise/trends-checker) | 218 | CLI Google Trends avec watch mode + alertes, cookie auth, DataForSEO fallback. |
| [crawlee-python](https://github.com/apify/crawlee-python) | 9 100 | **Couche de scraping universelle.** Anti-détection natif, Playwright intégré, retry/proxy. `pip install crawlee[playwright]`. |
| [etsyv3](https://github.com/anitabyte/etsyv3) | 75 | Client API officielle Etsy v3 (OAuth 2.0, 10k req/jour gratuit). Listing counts propres sans scraping. |
| [wordsy_python](https://github.com/interwebologist/wordsy_python) | 38 | Analyse des tags les plus fréquents sur les bestsellers Etsy — signal direct de demande par niche. |
| [seo-keyword-research-tool](https://github.com/chukhraiartur/seo-keyword-research-tool) | 154 | Google Autocomplete + People Also Ask + Related Searches. 0 clé API. Génère 200+ variantes de longue traîne depuis un seed keyword. |

### 🟡 Priorité MOYENNE — enrichissement futur

| Repo | Stars | Utilité |
|------|-------|---------|
| [pinscrape](https://github.com/iamatulsingh/pinscrape) | 142 | Scraper Pinterest par mot-clé ou board. Signaux visuels de demande. |
| [pinterest-scrapy-scraper](https://github.com/Simple-Python-Scrapy-Scrapers/pinterest-scrapy-scraper) | 7 | 60+ champs par pin (engagement, shopping data). Mesure du nombre de repins = proxy demande. |
| [keyword-clustering](https://github.com/dartseoengineer/keyword-clustering) | ~50 | Clustering de mots-clés par similarité d'URLs (Jaccard). Structure automatique des niches candidates. |
| [keyword_clustering_easy_demo](https://github.com/evemilano/keyword_clustering_easy_demo) | ~30 | Clustering sémantique NLP avec SentenceTransformer + BERTopic. Détection de micro-niches émergentes. |
| [invisible_playwright](https://github.com/feder-cr/invisible_playwright) | 1 200 | Drop-in Playwright avec anti-détection C++ (reCAPTCHA v3 score 0.90). Quand crawlee ne suffit pas. |
| [anofox-forecast](https://github.com/DataZooDE/anofox-forecast) | 34 | Extension DuckDB pour forecasting séries temporelles en pur SQL — AutoETS, AutoARIMA, 32 modèles. |
| [Etsy_Scraper](https://github.com/anastasiabizyayeva/Etsy_Scraper) | 30 | Scraper Selenium : listing count exact, prix, rating, nombre de ventes par niche. |

### 🟢 Priorité FAIBLE / à surveiller

| Repo | Note |
|------|------|
| [URS Reddit Scraper](https://github.com/JosephLai241/URS) | 995 ⭐ mais dernière maj mai 2023. PRAW seul suffit pour un usage basique. |
| Spoonflower API | Pas d'API publique officielle. Scraping custom avec crawlee = meilleure approche. |

### Note DuckDB

Pas besoin d'un repo dédié — `pip install duckdb` + extension `anofox-forecast` activable en SQL.
Bon choix pour stocker et analyser les séries temporelles de trends sans infrastructure.

## Sources marché potentielles (collectors futurs)

Google Trends, Pinterest, Etsy, Spoonflower, Reddit, TikTok, Amazon, Creative Market,
Design Bundles, Creative Fabrica, KDP, Instagram + sites de tendances déco/mode/papier peint.
