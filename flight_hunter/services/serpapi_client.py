"""
Client pour l'API SerpApi (Google Flights).

Documentation : https://serpapi.com/google-flights-api
SDK Python   : https://github.com/serpapi/google-search-results-python

Ce module encapsule l'endpoint Google Flights de SerpApi.
SerpApi se charge d'interroger Google Flights et de renvoyer un JSON propre.

Avantages vs Amadeus :
- Une seule clé API
- Données réelles de Google Flights (à jour, complètes)
- Tier gratuit 250 requêtes/mois sans CB
- Pas de gestion de token OAuth

Mapping ville -> code IATA :
SerpApi attend un code IATA (CDG, BOD, RAK, etc.). On maintient un dictionnaire
des principales villes pour convertir. Pour aller plus loin, on pourrait appeler
l'API d'autocomplétion de SerpApi, mais ça consommerait des requêtes pour rien.
"""
from __future__ import annotations

from typing import List, Optional

from serpapi import GoogleSearch

from flight_hunter.config.settings import Settings
from flight_hunter.utils.exceptions import (
    APIConfigurationError,
    APIRateLimitError,
    InvalidLocationError,
    NoFlightsFoundError,
)


# Dictionnaire ville -> code IATA principal.
# Ajoute des villes ici si besoin (ou utilise directement le code IATA dans la CLI).
CITY_TO_IATA = {
    # France
    "paris": "CDG",
    "bordeaux": "BOD",
    "marseille": "MRS",
    "lyon": "LYS",
    "nice": "NCE",
    "toulouse": "TLS",
    "nantes": "NTE",
    "strasbourg": "SXB",
    "lille": "LIL",
    "montpellier": "MPL",
    "biarritz": "BIQ",
    # Maroc
    "marrakech": "RAK",
    "casablanca": "CMN",
    "rabat": "RBA",
    "agadir": "AGA",
    "tanger": "TNG",
    "fes": "FEZ",
    "fès": "FEZ",
    # Europe
    "londres": "LHR",
    "london": "LHR",
    "madrid": "MAD",
    "barcelone": "BCN",
    "barcelona": "BCN",
    "rome": "FCO",
    "milan": "MXP",
    "lisbonne": "LIS",
    "lisbon": "LIS",
    "porto": "OPO",
    "amsterdam": "AMS",
    "berlin": "BER",
    "munich": "MUC",
    "vienne": "VIE",
    "athenes": "ATH",
    "athènes": "ATH",
    "istanbul": "IST",
    "dublin": "DUB",
    "geneve": "GVA",
    "genève": "GVA",
    "zurich": "ZRH",
    "bruxelles": "BRU",
    "brussels": "BRU",
    "copenhague": "CPH",
    "stockholm": "ARN",
    "oslo": "OSL",
    "helsinki": "HEL",
    "varsovie": "WAW",
    "prague": "PRG",
    "budapest": "BUD",
    # Amérique du Nord
    "new york": "JFK",
    "newyork": "JFK",
    "los angeles": "LAX",
    "miami": "MIA",
    "chicago": "ORD",
    "san francisco": "SFO",
    "boston": "BOS",
    "washington": "IAD",
    "montreal": "YUL",
    "montréal": "YUL",
    "toronto": "YYZ",
    "vancouver": "YVR",
    # Asie
    "tokyo": "HND",
    "osaka": "KIX",
    "seoul": "ICN",
    "séoul": "ICN",
    "pekin": "PEK",
    "pékin": "PEK",
    "shanghai": "PVG",
    "hong kong": "HKG",
    "hongkong": "HKG",
    "singapour": "SIN",
    "singapore": "SIN",
    "bangkok": "BKK",
    "bali": "DPS",
    "denpasar": "DPS",
    "delhi": "DEL",
    "mumbai": "BOM",
    # Moyen-Orient
    "dubai": "DXB",
    "dubaï": "DXB",
    "doha": "DOH",
    "abu dhabi": "AUH",
    "tel aviv": "TLV",
    # Afrique
    "le caire": "CAI",
    "cairo": "CAI",
    "alger": "ALG",
    "tunis": "TUN",
    "dakar": "DSS",
    "johannesburg": "JNB",
    "le cap": "CPT",
    "capetown": "CPT",
    "nairobi": "NBO",
    # Océanie
    "sydney": "SYD",
    "melbourne": "MEL",
}


class SerpApiClient:
    """Wrapper autour de l'API SerpApi (engine google_flights)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ------------------------------------------------------------------ #
    # Conversion ville -> code IATA                                      #
    # ------------------------------------------------------------------ #
    def get_iata_code(self, city_name: str) -> str:
        """
        Convertit un nom de ville en code IATA (ex: "Bordeaux" -> "BOD").

        Si la valeur fournie est déjà un code IATA (3 lettres majuscules),
        on la retourne telle quelle.
        Sinon on cherche dans le dictionnaire CITY_TO_IATA.
        """
        # Si c'est déjà un code IATA (3 lettres majuscules), on le garde
        if len(city_name) == 3 and city_name.isalpha() and city_name.isupper():
            return city_name

        # Recherche insensible à la casse / aux accents simples
        key = city_name.strip().lower()
        if key in CITY_TO_IATA:
            return CITY_TO_IATA[key]

        # Tentative en majuscules (au cas où l'utilisateur a tapé un code IATA
        # en minuscules : "bod" -> "BOD")
        if len(city_name) == 3 and city_name.isalpha():
            return city_name.upper()

        raise InvalidLocationError(
            f"Ville inconnue : '{city_name}'. "
            f"Essaie d'utiliser directement le code IATA à 3 lettres "
            f"(ex: BOD pour Bordeaux, RAK pour Marrakech). "
            f"Voir https://www.iata.org/en/publications/directories/code-search/"
        )

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
        Cherche des offres de vols sur Google Flights via SerpApi.
        Retourne une liste normalisée de dictionnaires (format unifié).
        """
        params = {
            "engine": "google_flights",
            "api_key": self._settings.serpapi_key,
            "departure_id": origin_iata,
            "arrival_id": destination_iata,
            "outbound_date": departure_date,
            "currency": currency or self._settings.default_currency,
            "hl": self._settings.default_language,
            "gl": self._settings.default_country,
            "adults": adults,
        }

        # Type de vol : 1 = aller-retour, 2 = aller simple
        if return_date:
            params["return_date"] = return_date
            params["type"] = "1"
        else:
            params["type"] = "2"

        # Vols directs uniquement
        if non_stop:
            params["stops"] = "1"  # 1 = direct only chez SerpApi

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
        except Exception as exc:
            raise APIConfigurationError(
                f"Erreur lors de l'appel à SerpApi : {exc}"
            ) from exc

        # Vérification erreur retournée par SerpApi
        if "error" in results:
            self._handle_api_error(results["error"])

        # Récupération des vols : Google Flights renvoie 2 listes
        # - best_flights : sélection mise en avant par Google
        # - other_flights : alternatives
        best = results.get("best_flights", []) or []
        others = results.get("other_flights", []) or []
        all_flights = best + others

        if not all_flights:
            raise NoFlightsFoundError(
                f"Aucun vol trouvé entre {origin_iata} et {destination_iata} "
                f"le {departure_date}."
            )

        # Tri par prix croissant
        all_flights.sort(key=lambda o: o.get("price", float("inf")))

        # On limite au nombre demandé
        return all_flights[:max_results]

    # ------------------------------------------------------------------ #
    # Gestion centralisée des erreurs API                                #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _handle_api_error(error_message: str) -> None:
        """Convertit les erreurs SerpApi en exceptions métier explicites."""
        msg_lower = error_message.lower()

        if "invalid api key" in msg_lower or "unauthorized" in msg_lower:
            raise APIConfigurationError(
                "Clé API SerpApi invalide. "
                "Vérifie ton fichier .env et la valeur SERPAPI_KEY."
            )
        if "run out of searches" in msg_lower or "quota" in msg_lower or "limit" in msg_lower:
            raise APIRateLimitError(
                "Quota SerpApi dépassé (250 requêtes/mois sur le plan gratuit). "
                "Réessaie le mois prochain ou passe à un plan payant."
            )
        if "haven't returned any results" in msg_lower or "no results" in msg_lower:
            raise NoFlightsFoundError(
                "Aucun vol trouvé pour cette recherche."
            )

        # Erreur générique
        raise APIConfigurationError(f"Erreur SerpApi : {error_message}")
