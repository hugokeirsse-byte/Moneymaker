# 🧭 Journal des Décisions

> Le « pourquoi » derrière chaque choix. Ordre chronologique.

## Stratégie & garde-fous

- **Lancement manuel uniquement** — crons désactivés tant que le système n'est pas validé.
  Évite toute exécution surprise.
- **Aucune dépense Runware sans accord explicite** — peur d'un débit carte automatique.
  → plafond d'images + gate d'approbation des CdC obligatoires avant tout run payant.
  Note : le wallet Runware est **prépayé** (pas de débit au-delà du solde), mais on verrouille quand même.
- **Spoonflower d'abord** — un seul marché validé avant d'étendre.
- **5 images par run** au départ (top niches), pour tester à coût minime (~0,03 €).

## Données & fiabilité

- **Zéro donnée inventée** — chaque métrique est un objet `Metric` tagué
  `MEASURED` / `HEURISTIC` / `UNAVAILABLE`, agrégé par `ProvenanceLedger`.
  Raison : pouvoir auditer chaque score et ne jamais déguiser une estimation en mesure.
- **Score d'opportunité explicable** — 6 composantes (demande, croissance, concurrence,
  potentiel visuel, réutilisabilité, compat. plateforme) + **indice de confiance** distinct du score.
- **Validation par sources gratuites sans clé** — Wikipedia Pageviews (fiable en datacenter)
  + Wikimedia. Les scrapers anonymes (Google/Reddit/DuckDuckGo) renvoient 403 en datacenter → non fiables.

## Choix techniques

- **2 clés suffisent** : `GEMINI_API_KEY` (découverte web, gratuit/peu cher) + `RUNWARE_API_KEY` (génération).
- **Gemini + Google Search grounding** remplace les scrapers anonymes (bloqués 403).
- **Auto-découverte du modèle Gemini** — le code liste les modèles dispo de la clé et
  choisit le meilleur `flash` (robuste face aux dépréciations). A résolu le passage
  forcé à `gemini-3.x` en 2026 quand les `2.0` n'avaient plus de quota.
- **Billing Gemini activé** (juin 2026) — le free tier était à `limit:0` (compte UE).
  Coût réel pour ~quelques requêtes/run : négligeable.
- **MarketProfile déclaratif** — tout le savoir d'un marché dans un profil ;
  ajouter une plateforme = ajouter un profil, zéro autre code (scalabilité).
- **Prompts 120-180 mots, structure 7 parties** (sujet → layout/repeat → style/medium →
  trait → palette hex → éclairage → fond + suffixe seamless) pour viser l'image parfaite
  en une génération avant upscale.

## Méthode de travail

- **Agents qui codent = mode principal** — Claude orchestre/architecture/teste/commit ;
  les agents écrivent le code. Économise les tokens.
- **Déléguer à Gemini** — pas seulement les CdC, aussi l'aide au code et la recherche de
  repos open-source utiles (quota journalier élevé).
- **Python pour le lourd, IA pour le raisonnement** (voir TOKEN_ECONOMY.md).
- **Doc tenue à jour** — partagée à ChatGPT/Gemini pour avis externes.
