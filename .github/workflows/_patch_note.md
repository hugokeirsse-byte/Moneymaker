# Patch checkout shallow
Le checkout full-history (fetch-depth: 0) échoue depuis que le repo dépasse plusieurs Go d'images.
Correction appliquée : fetch-depth: 1 dans trend_discovery.yml.
