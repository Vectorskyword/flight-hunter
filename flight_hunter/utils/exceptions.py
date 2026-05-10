"""
Exceptions personnalisées pour Flight Hunter.
Permet de différencier les types d'erreurs (réseau, données, configuration)
et d'avoir des messages clairs pour l'utilisateur final.
"""


class FlightHunterError(Exception):
    """Exception de base pour toutes les erreurs de l'application."""


class APIConfigurationError(FlightHunterError):
    """Clés API manquantes, invalides ou expirées."""


class APIRateLimitError(FlightHunterError):
    """Quota API dépassé."""


class NoFlightsFoundError(FlightHunterError):
    """Aucun vol n'a été trouvé pour les critères donnés."""


class InvalidLocationError(FlightHunterError):
    """Le code IATA d'aéroport/ville est inconnu ou invalide."""
