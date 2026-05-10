"""
FlightAgent : orchestrateur principal.

Approche choisie : agent par "fonctions modulaires" (sans LLM).
Cette approche est plus prédictible, gratuite et plus rapide qu'un agent LangChain
pour ce cas d'usage où la logique est déterministe.

Pour évoluer vers un vrai agent LLM (ex: parsing langage naturel
"trouve-moi un vol pas cher pour Marrakech la semaine prochaine"),
il suffira d'enrober ces méthodes en `Tool` LangChain — voir README.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List, Optional

from flight_hunter.config.settings import Settings
from flight_hunter.services.amadeus_client import AmadeusClient


@dataclass
class FlightSearchRequest:
    """Requête de recherche normalisée."""
    origin_city: str
    destination_city: str
    departure_date: str               # "YYYY-MM-DD"
    return_date: Optional[str] = None # "YYYY-MM-DD" ou None
    adults: int = 1
    max_results: int = 10
    non_stop: bool = False

    def validate(self) -> None:
        """Vérifie les contraintes basiques sur la requête."""
        try:
            dep = date.fromisoformat(self.departure_date)
        except ValueError as exc:
            raise ValueError(
                f"Date de départ invalide : '{self.departure_date}' "
                "(format attendu : YYYY-MM-DD)"
            ) from exc

        if dep < date.today():
            raise ValueError("La date de départ doit être dans le futur.")

        if self.return_date:
            try:
                ret = date.fromisoformat(self.return_date)
            except ValueError as exc:
                raise ValueError(
                    f"Date de retour invalide : '{self.return_date}'"
                ) from exc
            if ret < dep:
                raise ValueError("La date de retour doit être après le départ.")

        if self.adults < 1 or self.adults > 9:
            raise ValueError("Le nombre d'adultes doit être entre 1 et 9.")


class FlightAgent:
    """
    Agent en charge de la recherche de vols.

    Pipeline :
        1) Résolution des codes IATA depuis les noms de villes
        2) Appel à l'API de recherche d'offres
        3) Tri par prix croissant
        4) Renvoi des résultats bruts (mise en forme déléguée à formatter.py)
    """

    def __init__(self, settings: Settings) -> None:
        self._client = AmadeusClient(settings)

    # ------------------------------------------------------------------ #
    # Méthode principale exposée à la CLI / future UI                    #
    # ------------------------------------------------------------------ #
    def search_cheapest_flights(self, request: FlightSearchRequest) -> List[dict]:
        request.validate()

        origin_iata = self._client.get_iata_code(request.origin_city)
        destination_iata = self._client.get_iata_code(request.destination_city)

        offers = self._client.search_flight_offers(
            origin_iata=origin_iata,
            destination_iata=destination_iata,
            departure_date=request.departure_date,
            return_date=request.return_date,
            adults=request.adults,
            max_results=request.max_results,
            non_stop=request.non_stop,
        )

        # Le client trie déjà, mais on s'assure du tri ici (single source of truth)
        offers.sort(key=lambda o: float(o["price"]["total"]))
        return offers

    # ------------------------------------------------------------------ #
    # Helpers exposables comme `Tool` LangChain plus tard                #
    # ------------------------------------------------------------------ #
    def resolve_city(self, city_name: str) -> str:
        """Renvoie le code IATA d'une ville. Utile pour debug & tools LLM."""
        return self._client.get_iata_code(city_name)
