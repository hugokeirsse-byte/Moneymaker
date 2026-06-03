"""
Interface commune des providers de données.

Un "provider" est un connecteur vers une source de données RÉELLE
(API officielle ou service de données). Contrairement aux anciens scrapers
anonymes (fragiles, souvent bloqués en 403), un provider :
    - utilise une authentification officielle (clé API)
    - retourne des données mesurées tracées (Metric.measured)
    - déclare proprement son indisponibilité s'il manque la clé,
      au lieu d'inventer des valeurs.

Chaque provider implémente `is_available()` et expose des méthodes
qui retournent soit de vraies données, soit un signal d'indisponibilité.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class DataProvider(ABC):
    """Classe de base pour tous les connecteurs de données réelles."""

    #: identifiant unique du provider (ex: "dataforseo", "etsy")
    key: str = "base"
    #: nom lisible
    name: str = "Base Provider"
    #: variables d'environnement requises pour fonctionner
    required_env: List[str] = []
    #: True si la source produit des données mesurées (vs heuristiques)
    produces_measured_data: bool = True

    def __init__(self):
        self._available: Optional[bool] = None

    @abstractmethod
    def _check_credentials(self) -> bool:
        """Retourne True si toutes les clés nécessaires sont présentes."""
        raise NotImplementedError

    def is_available(self) -> bool:
        """
        Indique si le provider peut être utilisé.
        Mis en cache après le premier appel.
        """
        if self._available is None:
            try:
                self._available = self._check_credentials()
            except Exception as exc:
                logger.warning("[%s] check credentials failed: %s", self.key, exc)
                self._available = False
            if not self._available:
                logger.info(
                    "[%s] indisponible — clés manquantes: %s",
                    self.key, ", ".join(self.required_env) or "(aucune)",
                )
        return self._available

    def status(self) -> Dict:
        """Métadonnées d'état pour les rapports."""
        return {
            "key": self.key,
            "name": self.name,
            "available": self.is_available(),
            "required_env": self.required_env,
            "produces_measured_data": self.produces_measured_data,
        }
