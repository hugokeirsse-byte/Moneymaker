# 📚 Moneymaker — Documentation & Plan Directeur

> **Mémoire vivante du projet.** Ce dossier regroupe la vision, l'architecture, les
> décisions et la feuille de route. Il est mis à jour à chaque évolution importante
> pour ne **rien oublier** et pouvoir être partagé (ChatGPT / Gemini) pour avis.

## Comment lire cette doc

| Fichier | Contenu |
|---------|---------|
| [VISION.md](VISION.md) | Le but réel : une infrastructure d'intelligence commerciale, pas une usine à images |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Les 14 modules du système, le pipeline, et l'état actuel de chacun |
| [ROADMAP.md](ROADMAP.md) | Avancement **brique par brique** — ce qui est fait, ce qui vient |
| [DECISIONS.md](DECISIONS.md) | Journal des décisions (le « pourquoi » de chaque choix) |
| [BACKLOG.md](BACKLOG.md) | Toutes les idées d'amélioration + pistes de repos open-source à étudier |
| [TOKEN_ECONOMY.md](TOKEN_ECONOMY.md) | Règles pour économiser les tokens Claude (Python pour le lourd, IA pour le raisonnement) |
| [platforms/spoonflower.md](platforms/spoonflower.md) | Intelligence plateforme : spécificités Spoonflower |

## Principe directeur

> On avance **pas à pas, brique par brique**. On ne construit pas tout d'un coup.
> Priorité actuelle : **mettre les premiers produits Spoonflower en vente.**
> Le reste vient après, une fois chaque brique validée.

## Règles d'or (non négociables)

1. **Zéro donnée inventée** — chaque chiffre est tagué `MEASURED` / `HEURISTIC` / `UNAVAILABLE`.
2. **Aucune dépense sans accord** — la génération Runware ne tourne jamais sans validation manuelle des CdC + plafond d'images.
3. **Lancement manuel** — crons désactivés tant que le système n'est pas validé.
4. **Économie de tokens** — Python fait le travail lourd ; l'IA ne sert qu'au raisonnement (voir TOKEN_ECONOMY.md).
5. **Pas de poubelle** — code et docs propres, organisés, à jour.
