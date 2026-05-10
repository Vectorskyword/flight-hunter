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
    amadeus_client_id: str
    amadeus_client_secret: str
    amadeus_hostname: str  # "test" ou "production"
    default_currency: str

    def validate(self) -> None:
        """Vérifie que les clés API sont bien présentes."""
        if not self.amadeus_client_id or not self.amadeus_client_secret:
            raise EnvironmentError(
                "Les clés AMADEUS_CLIENT_ID et AMADEUS_CLIENT_SECRET "
                "doivent être définies dans le fichier .env"
            )


def load_settings() -> Settings:
    """Factory : construit l'objet Settings depuis l'environnement."""
    settings = Settings(
        amadeus_client_id=os.getenv("AMADEUS_CLIENT_ID", ""),
        amadeus_client_secret=os.getenv("AMADEUS_CLIENT_SECRET", ""),
        amadeus_hostname=os.getenv("AMADEUS_HOSTNAME", "test"),
        default_currency=os.getenv("DEFAULT_CURRENCY", "EUR"),
    )
    settings.validate()
    return settings
