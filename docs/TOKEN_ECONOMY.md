# 💸 Économie de Tokens & Délégation

> Claude Code est cher. On l'utilise avec parcimonie. La plupart du travail doit être
> fait par du **code Python classique** ou **délégué** (agents / Gemini).

## Ne JAMAIS utiliser Claude pour

- scraper / collecter des données
- stocker / filtrer / dédupliquer
- calculer des scores simples ou des statistiques
- générer des rapports à partir de données déjà structurées

→ Tout ça = **code Python**, exécuté gratuitement dans le CI.

## Utiliser Claude UNIQUEMENT pour

- raisonnement complexe & architecture
- interprétation, hybridation conceptuelle
- création de taxonomies / briefs
- revue de code et décisions

## Pipeline économe (règle d'or)

```
MAUVAIS :  10 000 données → Claude

BON :      10 000 données → Python (filtre) → Top 20 → IA
```

L'IA ne voit que le **strict nécessaire** (le top filtré), jamais le brut.

## Délégation

- **Agents qui codent** : Claude écrit une spec précise, un agent implémente, Claude revoit/teste/commit.
  C'est le **mode de fonctionnement principal**.
- **Gemini** (quota journalier élevé) : déléguer
  - la génération des CdC et prompts
  - l'aide au code / refactors simples
  - la recherche de repos GitHub open-source utiles
  - la recherche web des tendances par plateforme

## Tâches planifiées (plus tard)

Certaines analyses tourneront en cron (heure/jour/semaine) en **Python pur**,
sans appeler d'IA en continu. Crons réactivés seulement après validation du système.
