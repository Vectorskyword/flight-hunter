"""
Client pour l'API Amadeus Self-Service.

Documentation : https://developers.amadeus.com/self-service
SDK Python   : https://github.com/amadeus4dev/amadeus-python

Ce module encapsule deux endpoints clés :
- /v1/reference-data/locations  : convertit un nom de ville en code IATA
- /v2/shopping/flight-offers     : recherche d'offres de vols
"""
from __future__ import annotations

from typing import List, Optional

from amadeus import Client, ResponseError

from flight_hunter.config.settings import Settings
from flight_hunter.utils.exceptions import (
    APIConfigurationError,
    APIRateLimitError,
    InvalidLocationError,
    NoFlightsFoundError,
)


class AmadeusClient:
    """Wrapper autour du SDK officiel Amadeus."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        try:
            self._client = Client(
                client_id=settings.amadeus_client_id,
                client_secret=settings.amadeus_client_secret,
                hostname=settings.amadeus_hostname,  # "test" ou "production"
            )
        except Exception as exc:
            raise APIConfigurationError(
                f"Impossible d'initialiser le client Amadeus : {exc}"
            ) from exc

    # ------------------------------------------------------------------ #
    # Conversion ville -> code IATA                                      #
    # ------------------------------------------------------------------ #
    def get_iata_code(self, city_name: str) -> str:
        """
        Convertit un nom de ville en code IATA (ex: "Paris" -> "PAR").
        Lève InvalidLocationError si rien n'est trouvé.
        """
        try:
            response = self._client.reference_data.locations.get(
                keyword=city_name,
                subType="CITY,AIRPORT",
            )
        except ResponseError as exc:
            self._handle_response_error(exc)

        if not response.data:
            raise InvalidLocationError(
                f"Aucun aéroport/ville trouvé pour '{city_name}'."
            )

        # On prend le premier résultat (le plus pertinent selon Amadeus)
        return response.data[0]["iataCode"]

    # ------------------------------------------------------------------ #
    # Recherche d'offres de vols                                         #
    # ------------------------------------------------------------------ #
    def search_flight_offers(
        self,
        origin_iata: str,
        destination_iata: str,
        departure_date: str,           # format "YYYY-MM-DD"
        return_date: Optional[str] = None,
        adults: int = 1,
        max_results: int = 10,
        non_stop: bool = False,
        currency: Optional[str] = None,
    ) -> List[dict]:
        """
        Cherche des offres de vols et retourne la liste brute (dict JSON).

        Le tri par prix croissant est appliqué via le paramètre `currencyCode`
        + tri côté client pour être robuste (Amadeus trie déjà par prix par défaut,
        mais on re-trie pour garantir le résultat).
        """
        params = {
            "originLocationCode": origin_iata,
            "destinationLocationCode": destination_iata,
            "departureDate": departure_date,
            "adults": adults,
            "max": max_results,
            "currencyCode": currency or self._settings.default_currency,
        }
        if return_date:
            params["returnDate"] = return_date
        if non_stop:
            params["nonStop"] = "true"

        try:
            response = self._client.shopping.flight_offers_search.get(**params)
        except ResponseError as exc:
            self._handle_response_error(exc)

        offers = response.data or []
        if not offers:
            raise NoFlightsFoundError(
                f"Aucun vol trouvé entre {origin_iata} et {destination_iata} "
                f"le {departure_date}."
            )

        # Tri par prix croissant (sécurité)
        offers.sort(key=lambda o: float(o["price"]["total"]))
        return offers

    # ------------------------------------------------------------------ #
    # Gestion centralisée des erreurs API                                #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _handle_response_error(exc: ResponseError) -> None:
        """Convertit les erreurs Amadeus en exceptions métier explicites."""
        status = getattr(exc.response, "status_code", None)

        if status == 401:
            raise APIConfigurationError(
                "Clés API Amadeus invalides ou expirées. "
                "Vérifie ton fichier .env."
            ) from exc
        if status == 429:
            raise APIRateLimitError(
                "Quota Amadeus dépassé. Réessaie plus tard."
            ) from exc
        if status and 400 <= status < 500:
            raise InvalidLocationError(
                f"Requête invalide ({status}) : {exc}"
            ) from exc

        # Erreur réseau / serveur
        raise APIConfigurationError(f"Erreur Amadeus : {exc}") from exc
