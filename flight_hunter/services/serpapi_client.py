"""
Client pour l'API SerpApi (Google Flights).

Documentation : https://serpapi.com/google-flights-api
SDK Python   : https://github.com/serpapi/google-search-results-python
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
CITY_TO_IATA = {
    # France
    "paris": "CDG", "bordeaux": "BOD", "marseille": "MRS", "lyon": "LYS",
    "nice": "NCE", "toulouse": "TLS", "nantes": "NTE", "strasbourg": "SXB",
    "lille": "LIL", "montpellier": "MPL", "biarritz": "BIQ",
    # Maroc
    "marrakech": "RAK", "casablanca": "CMN", "rabat": "RBA", "agadir": "AGA",
    "tanger": "TNG", "fes": "FEZ", "fès": "FEZ",
    # Europe
    "londres": "LHR", "london": "LHR", "madrid": "MAD",
    "barcelone": "BCN", "barcelona": "BCN", "rome": "FCO", "milan": "MXP",
    "lisbonne": "LIS", "lisbon": "LIS", "porto": "OPO", "amsterdam": "AMS",
    "berlin": "BER", "munich": "MUC", "vienne": "VIE",
    "athenes": "ATH", "athènes": "ATH", "istanbul": "IST", "dublin": "DUB",
    "geneve": "GVA", "genève": "GVA", "zurich": "ZRH",
    "bruxelles": "BRU", "brussels": "BRU", "copenhague": "CPH",
    "stockholm": "ARN", "oslo": "OSL", "helsinki": "HEL",
    "varsovie": "WAW", "prague": "PRG", "budapest": "BUD",
    "valence": "VLC", "valencia": "VLC", "seville": "SVQ", "séville": "SVQ",
    "malaga": "AGP", "málaga": "AGP", "palma": "PMI", "ibiza": "IBZ",
    "naples": "NAP", "venise": "VCE", "venice": "VCE", "florence": "FLR",
    # Amérique du Nord
    "new york": "JFK", "newyork": "JFK", "los angeles": "LAX",
    "miami": "MIA", "chicago": "ORD", "san francisco": "SFO",
    "boston": "BOS", "washington": "IAD",
    "montreal": "YUL", "montréal": "YUL", "toronto": "YYZ", "vancouver": "YVR",
    # Asie
    "tokyo": "HND", "osaka": "KIX", "seoul": "ICN", "séoul": "ICN",
    "pekin": "PEK", "pékin": "PEK", "shanghai": "PVG",
    "hong kong": "HKG", "hongkong": "HKG",
    "singapour": "SIN", "singapore": "SIN", "bangkok": "BKK",
    "bali": "DPS", "denpasar": "DPS", "delhi": "DEL", "mumbai": "BOM",
    # Moyen-Orient
    "dubai": "DXB", "dubaï": "DXB", "doha": "DOH", "abu dhabi": "AUH",
    "tel aviv": "TLV",
    # Afrique
    "le caire": "CAI", "cairo": "CAI", "alger": "ALG", "tunis": "TUN",
    "dakar": "DSS", "johannesburg": "JNB", "le cap": "CPT", "capetown": "CPT",
    "nairobi": "NBO",
    # Océanie
    "sydney": "SYD", "melbourne": "MEL",
}


class SerpApiClient:
    """Wrapper autour de l'API SerpApi (engine google_flights)."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ------------------------------------------------------------------ #
    # Conversion ville -> code IATA                                      #
    # ------------------------------------------------------------------ #
    def get_iata_code(self, city_name: str) -> str:
        """Convertit un nom de ville en code IATA."""
        # Si c'est déjà un code IATA majuscules
        if len(city_name) == 3 and city_name.isalpha() and city_name.isupper():
            return city_name

        key = city_name.strip().lower()
        if key in CITY_TO_IATA:
            return CITY_TO_IATA[key]

        # Code IATA en minuscules
        if len(city_name) == 3 and city_name.isalpha():
            return city_name.upper()

        raise InvalidLocationError(
            f"Ville inconnue : '{city_name}'. "
            f"Utilise le code IATA à 3 lettres (ex: BOD, RAK, CDG). "
            f"Liste : https://www.iata.org/en/publications/directories/code-search/"
        )

    # ------------------------------------------------------------------ #
    # Recherche d'offres de vols                                         #
    # ------------------------------------------------------------------ #
    def search_flight_offers(
        self,
        origin_iata: str,
        destination_iata: str,
        departure_date: str,
        return_date: Optional[str] = None,
        adults: int = 1,
        max_results: int = 10,
        non_stop: bool = False,
        currency: Optional[str] = None,
        outbound_times: Optional[str] = None,
        return_times: Optional[str] = None,
    ) -> List[dict]:
        """
        Cherche des offres de vols sur Google Flights via SerpApi.

        :param outbound_times: tranche horaire vol aller au format
                              "h_dep_min,h_dep_max,h_arr_min,h_arr_max"
                              ex: "16,23,0,23" = départ entre 16h et 23h
        :param return_times: idem pour le vol retour
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

        if return_date:
            params["return_date"] = return_date
            params["type"] = "1"  # round trip
        else:
            params["type"] = "2"  # one way

        if non_stop:
            params["stops"] = "1"  # direct only

        if outbound_times:
            params["outbound_times"] = outbound_times
        if return_times:
            params["return_times"] = return_times

        try:
            search = GoogleSearch(params)
            results = search.get_dict()
        except Exception as exc:
            raise APIConfigurationError(
                f"Erreur lors de l'appel à SerpApi : {exc}"
            ) from exc

        if "error" in results:
            self._handle_api_error(results["error"])

        best = results.get("best_flights", []) or []
        others = results.get("other_flights", []) or []
        all_flights = best + others

        if not all_flights:
            raise NoFlightsFoundError(
                f"Aucun vol trouvé entre {origin_iata} et {destination_iata} "
                f"le {departure_date}."
            )

        all_flights.sort(key=lambda o: o.get("price", float("inf")))
        return all_flights[:max_results]

    # ------------------------------------------------------------------ #
    # Gestion centralisée des erreurs API                                #
    # ------------------------------------------------------------------ #
    @staticmethod
    def _handle_api_error(error_message: str) -> None:
        msg_lower = error_message.lower()

        if "invalid api key" in msg_lower or "unauthorized" in msg_lower:
            raise APIConfigurationError(
                "Clé API SerpApi invalide. Vérifie ton fichier .env."
            )
        if "run out" in msg_lower or "quota" in msg_lower or "limit" in msg_lower:
            raise APIRateLimitError(
                "Quota SerpApi dépassé. Réessaie le mois prochain."
            )
        if "haven't returned any results" in msg_lower or "no results" in msg_lower:
            raise NoFlightsFoundError("Aucun vol trouvé pour cette recherche.")

        raise APIConfigurationError(f"Erreur SerpApi : {error_message}")
