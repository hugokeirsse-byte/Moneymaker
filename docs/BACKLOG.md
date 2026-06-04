# 📥 Backlog — Idées d'Évolution & Pistes

> Réservoir d'idées validées comme pertinentes mais **pas encore prioritaires**.
> On les fera brique par brique, après les premiers produits Spoonflower en vente.

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

## Repos open-source à étudier (délégable à Gemini)

> Objectif : ne pas réinventer la roue. Faire chercher Gemini.

- **Google Trends** : wrappers/historique (ex. `pytrends` déjà utilisé, chercher alternatives robustes)
- **Keyword research** : keyword clustering, longue traîne, SEO automation
- **Scraping robuste** : Playwright, Crawlee, Scrapy (collecteurs + monitoring)
- **Data storage** : DuckDB / PostgreSQL pour l'historique & analyses
- **Repos d'analyse de trends/niches** : chercher s'il en existe un public exploitable

## Sources marché potentielles (collectors futurs)

Google Trends, Pinterest, Etsy, Spoonflower, Reddit, TikTok, Amazon, Creative Market,
Design Bundles, Creative Fabrica, KDP, Instagram + sites de tendances déco/mode/papier peint.
