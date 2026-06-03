# 🏭 Moneymaker

Usine automatisée de détection d'opportunités commerciales pour le print-on-demand
et les produits numériques (Spoonflower, RedBubble, Etsy, KDP, B2B…).

Objectif : détecter automatiquement **les niches qui rapportent vraiment**, sur
**les bonnes plateformes**, avec **les bons produits** — sur la base de **vraies
données de marché**, jamais d'estimations déguisées.

---

## 🧭 Principe fondamental : zéro donnée inventée

Le système **ne déguise jamais une estimation en mesure réelle**.

Chaque valeur numérique est tracée (`trend_discovery/provenance.py`) :

| Nature | Signification |
|--------|---------------|
| 🟢 `MEASURED` | Vraie donnée issue d'une source réelle (API officielle) |
| 🟡 `HEURISTIC` | Estimation basée sur une règle interne |
| 🔴 `UNAVAILABLE` | Donnée non disponible (aucune source) |

Chaque rapport affiche un **score de fiabilité** : la part du résultat qui
repose sur de vraies recherches. Sans clés API, le système le dit clairement
au lieu de produire des scores au hasard.

---

## 🔑 Clés API — quoi mettre et pourquoi

Configure tes clés dans **`.env`** (local) ou dans
**GitHub → Settings → Secrets and variables → Actions** (automatisation).

### Source principale — vraie demande (PAYANT, pay-as-you-go)

| Clé | Donne | Coût | Obtenir |
|-----|-------|------|---------|
| `DATAFORSEO_LOGIN` + `DATAFORSEO_PASSWORD` | **Vrais volumes de recherche Google mensuels + compétition réelle + CPC** | ~0,05 $ / 1000 mots-clés (pas d'abonnement) | [app.dataforseo.com/register](https://app.dataforseo.com/register) |

> C'est **la** clé qui transforme le système d'estimations en vraies valeurs de
> marché. Le système met les résultats en cache pour ne payer qu'une fois par
> mot-clé.

### Sources gratuites SANS aucune clé (actives par défaut)

| Source | Donne | Config |
|--------|-------|--------|
| **Wikipedia Pageviews** | **Vues réelles de pages = demande + croissance + saisonnalité mesurées** | ✅ aucune (auto) |
| **Wikipedia/MediaWiki** | Découverte de sous-niches réelles (liens, catégories) | ✅ aucune (auto) |
| **DuckDuckGo Autocomplete** | Expansion de sous-niches recherchées | ✅ aucune (auto) |

> **Budget 0 € :** le système tourne déjà sur de vraies données grâce à
> Wikipedia, sans aucune clé. Ajoute les clés gratuites ci-dessous pour
> enrichir (compétition marché, buzz, demande vidéo).

### Sources gratuites — vrai marché & signal social (inscription requise)

| Clé | Donne | Coût | Obtenir |
|-----|-------|------|---------|
| `ETSY_API_KEY` | Nombre réel de listings actifs, tags réels, prix réels (= vraie compétition POD/numérique) | **Gratuit** | [etsy.com/developers/register](https://www.etsy.com/developers/register) |
| `REDDIT_CLIENT_ID` + `REDDIT_CLIENT_SECRET` | Vrai buzz communautaire (upvotes, commentaires) | **Gratuit** | [reddit.com/prefs/apps](https://www.reddit.com/prefs/apps) → app type *script* |
| `YOUTUBE_API_KEY` | Vraies vues de tutoriels = intérêt réel pour une niche | **Gratuit** (10 000 u/jour) | [console.cloud.google.com](https://console.cloud.google.com) → activer *YouTube Data API v3* |

### Pour les modules futurs (génération d'images)

| Clé | Usage |
|-----|-------|
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Analyse avancée, génération (modules ultérieurs) |

> **Recommandation budget 0 € :** le système fonctionne déjà sur de vraies
> données via **Wikipedia** (sans clé). Ajoute ensuite les clés **gratuites**
> Etsy + Reddit + YouTube pour la compétition marché et le buzz. **DataForSEO**
> (payant) reste optionnel : il n'apporte que les volumes de recherche Google
> absolus, que Wikipedia approxime gratuitement.

---

## 🏗️ Architecture

```
trend_discovery/
├── provenance.py            # Traçabilité : MEASURED / HEURISTIC / UNAVAILABLE
├── providers/               # Connecteurs vers les VRAIES sources (APIs officielles)
│   ├── dataforseo_provider.py   # volumes de recherche Google réels
│   ├── etsy_provider.py         # compétition marché réelle
│   ├── reddit_provider.py       # buzz communautaire réel
│   ├── youtube_provider.py      # demande vidéo réelle
│   ├── provider_registry.py     # détecte les clés dispo
│   └── real_data_collector.py   # collecte + trace les métriques
├── normalizer/              # Phase 2-3 : normalisation + arbre de niches
│   ├── concept_merger.py        # fusion synonymes → niches canoniques
│   └── niche_tree_builder.py    # arbre hiérarchique (160 nœuds)
├── analyzers/               # Phase 4-5 : scoring
│   ├── opportunity_scorer.py    # formule multi-critères
│   ├── hybrid_scorer.py         # combinaisons de niches
│   ├── trend_scorer.py
│   └── feasibility_scorer.py
├── platform_router/         # MODULE 02 : allocation multi-plateformes
│   ├── platform_profiles.py     # profils des 13 plateformes
│   ├── compatibility_matrix.py  # score niche × plateforme
│   ├── product_recommender.py   # produits recommandés/déconseillés
│   ├── economic_estimator.py    # potentiel économique
│   └── allocator.py             # recommandation stratégique finale
├── database/                # Phase 6-7 : base + mémoire historique
│   ├── opportunity_store.py     # SQLite des opportunités
│   └── history_tracker.py       # évolution des scores
├── reporters/               # génération de rapports
└── main.py                  # orchestrateur du pipeline
```

---

## 🚀 Utilisation

```bash
# Installer les dépendances
pip install -r requirements.txt

# Configurer les clés
cp .env.example .env   # puis remplir

# Lancer le pipeline complet
python -m trend_discovery.main

# Mode rapide (sources principales uniquement)
python -m trend_discovery.main --fast

# Cibler des niches
python -m trend_discovery.main --keywords "botanical,medieval herbs" --depth 2
```

Les rapports sont écrits dans `reports/` (Markdown + JSON, plus `latest_report.md`).

---

## 🤖 Automatisation (GitHub Actions)

Le workflow `.github/workflows/trend_discovery.yml` tourne **2× par jour**
(06h et 18h UTC) et après chaque déclenchement manuel. Il :
1. lance le pipeline,
2. commit les rapports dans `reports/`,
3. conserve la base SQLite entre les runs (cache) pour la mémoire historique.

Ajoute tes clés dans les **Secrets** du repo pour qu'il utilise les vraies données.

---

## 📦 Modules

- **Module 01 — Détection de tendances** ✅ : collecte → normalisation → arbre de
  niches → hybridation → scoring → base → mémoire historique.
- **Module 02 — Allocation multi-plateformes** ✅ : pour chaque opportunité,
  score par plateforme + produits recommandés + priorité de publication.
- **Modules suivants** (à venir) : génération d'images, création de collections,
  publication automatisée.
