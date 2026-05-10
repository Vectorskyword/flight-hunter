"""
Module de configuration.
Charge les clés API et paramètres depuis le fichier .env.
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

# Charge les variables du fichier .env à la racine du projet
load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Conteneur immuable pour la configuration de l'application."""
    serpapi_key: str
    default_currency: str
    default_country: str
    default_language: str

    def validate(self) -> None:
        """Vérifie que la clé API est bien présente."""
        if not self.serpapi_key:
            raise EnvironmentError(
                "La variable SERPAPI_KEY doit être définie dans le fichier .env. "
                "Récupère ta clé sur https://serpapi.com/manage-api-key"
            )


def load_settings() -> Settings:
    """Factory : construit l'objet Settings depuis l'environnement."""
    settings = Settings(
        serpapi_key=os.getenv("SERPAPI_KEY", ""),
        default_currency=os.getenv("DEFAULT_CURRENCY", "EUR"),
        default_country=os.getenv("DEFAULT_COUNTRY", "fr"),
        default_language=os.getenv("DEFAULT_LANGUAGE", "fr"),
    )
    settings.validate()
    return settings
