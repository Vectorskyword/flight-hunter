"""
Scanner de week-ends.

Pour un mois donné (ex: "2026-08"), génère tous les couples (vendredi, dimanche)
qui constituent un week-end "strict" :
- départ vendredi à partir de 16h00
- retour dimanche

Délègue ensuite la recherche de vols à SerpApiClient et regroupe les résultats.
"""
from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Iterator, List, Optional

from flight_hunter.services.serpapi_client import SerpApiClient
from flight_hunter.utils.exceptions import (
    FlightHunterError,
    NoFlightsFoundError,
)


# Tranches horaires (au format SerpApi : "h_depart_min,h_depart_max,h_arrivee_min,h_arrivee_max")
# Vendredi : départ entre 16h et 23h, arrivée libre (0h-23h)
FRIDAY_OUTBOUND_TIMES = "16,23,0,23"

# Dimanche retour : départ entre 12h et 23h59 (après-midi/soir), arrivée libre
SUNDAY_RETURN_TIMES = "12,23,0,23"


@dataclass
class WeekendTrip:
    """Un week-end candidat avec ses dates."""
    friday: date    # date du vendredi (départ)
    sunday: date    # date du dimanche (retour)

    @property
    def departure_str(self) -> str:
        return self.friday.isoformat()

    @property
    def return_str(self) -> str:
        return self.sunday.isoformat()

    @property
    def label(self) -> str:
        """'Ven 14/08 → Dim 16/08' pour affichage."""
        return (
            f"Ven {self.friday.strftime('%d/%m')} → "
            f"Dim {self.sunday.strftime('%d/%m')}"
        )


@dataclass
class WeekendOffer:
    """Une offre regroupée pour un week-end donné."""
    weekend: WeekendTrip
    price: float
    currency: str
    outbound_carrier: str
    outbound_flight_number: str
    outbound_departure_time: str
    outbound_arrival_time: str
    return_carrier: str
    return_flight_number: str
    return_departure_time: str
    return_arrival_time: str
    booking_url: str
    raw_offer: dict


def list_weekends_in_month(year: int, month: int) -> List[WeekendTrip]:
    """
    Renvoie tous les week-ends (vendredi+dimanche) du mois donné.

    Un week-end est inclus si le vendredi ET le dimanche tombent dans le mois.
    On exclut les dates passées (départ < aujourd'hui).
    """
    weekends: List[WeekendTrip] = []
    today = date.today()

    _, last_day = calendar.monthrange(year, month)

    for day in range(1, last_day + 1):
        d = date(year, month, day)
        # weekday() : Monday=0, Friday=4, Sunday=6
        if d.weekday() == 4:  # vendredi
            sunday = d + timedelta(days=2)
            # On garde seulement si le dimanche est aussi dans le même mois
            # ET si le vendredi n'est pas dans le passé
            if sunday.month == month and d >= today:
                weekends.append(WeekendTrip(friday=d, sunday=sunday))

    return weekends


def iter_weekends_for_period(
    year: int,
    month: int,
    months_ahead: int = 1,
) -> Iterator[WeekendTrip]:
    """
    Itère sur les week-ends de `months_ahead` mois consécutifs à partir de (year, month).
    Utile pour étendre la recherche à plusieurs mois.
    """
    current_year, current_month = year, month
    for _ in range(months_ahead):
        for w in list_weekends_in_month(current_year, current_month):
            yield w
        current_month += 1
        if current_month > 12:
            current_month = 1
            current_year += 1


class WeekendScanner:
    """
    Scanne plusieurs week-ends et retourne les meilleures offres triées par prix.
    Une "offre" = un aller-retour vendredi soir + dimanche.
    """

    def __init__(self, client: SerpApiClient) -> None:
        self._client = client

    def scan_month(
        self,
        origin_iata: str,
        destination_iata: str,
        year: int,
        month: int,
        max_price: Optional[float] = None,
        non_stop: bool = False,
        currency: str = "EUR",
        adults: int = 1,
    ) -> List[WeekendOffer]:
        """
        Pour chaque week-end du mois :
        - lance une recherche aller-retour
        - garde l'offre la moins chère
        - filtre par budget si max_price défini
        Renvoie la liste triée par prix croissant.
        """
        weekends = list_weekends_in_month(year, month)
        if not weekends:
            raise FlightHunterError(
                f"Aucun week-end disponible dans {year}-{month:02d} "
                "(mois passé ou aucun vendredi/dimanche)."
            )

        results: List[WeekendOffer] = []

        for w in weekends:
            try:
                offers = self._client.search_flight_offers(
                    origin_iata=origin_iata,
                    destination_iata=destination_iata,
                    departure_date=w.departure_str,
                    return_date=w.return_str,
                    adults=adults,
                    max_results=5,
                    non_stop=non_stop,
                    currency=currency,
                    outbound_times=FRIDAY_OUTBOUND_TIMES,
                    return_times=SUNDAY_RETURN_TIMES,
                )
            except NoFlightsFoundError:
                # Pas de vol ce week-end, on passe au suivant
                continue
            except FlightHunterError:
                # Erreur API ponctuelle : on saute ce week-end mais on continue
                continue

            if not offers:
                continue

            # On prend l'offre la moins chère pour ce week-end
            cheapest = offers[0]
            price = float(cheapest.get("price", 0))

            # Filtre budget
            if max_price is not None and price > max_price:
                continue

            results.append(_to_weekend_offer(w, cheapest, currency))

        # Tri global par prix croissant
        results.sort(key=lambda r: r.price)
        return results


def _to_weekend_offer(weekend: WeekendTrip, offer: dict, currency: str) -> WeekendOffer:
    """Convertit une offre brute SerpApi (aller-retour) en WeekendOffer normalisée."""
    flights = offer.get("flights", [])

    # En aller-retour, SerpApi met les segments aller PUIS retour dans la même liste "flights".
    # Mais souvent ils sont dans deux listes séparées ou il faut un 2e appel.
    # On gère le cas simple : tous dans "flights" ; si on a return_flights, on les utilise.
    outbound_flights = offer.get("flights", []) or []
    return_flights = offer.get("return_flights", []) or []

    # Si pas de "return_flights" séparée, on coupe "flights" en deux par défaut
    if not return_flights and len(outbound_flights) > 1:
        # heuristique : on garde tous dans outbound, retour vide
        # (la plupart des cas avec SerpApi : un seul appel = aller seul)
        pass

    out_first = outbound_flights[0] if outbound_flights else {}
    out_last = outbound_flights[-1] if outbound_flights else {}
    ret_first = return_flights[0] if return_flights else {}
    ret_last = return_flights[-1] if return_flights else {}

    booking_url = _extract_booking_url(offer)

    return WeekendOffer(
        weekend=weekend,
        price=float(offer.get("price", 0)),
        currency=currency,
        outbound_carrier=out_first.get("airline", "—"),
        outbound_flight_number=out_first.get("flight_number", "—"),
        outbound_departure_time=out_first.get("departure_airport", {}).get("time", "—"),
        outbound_arrival_time=out_last.get("arrival_airport", {}).get("time", "—"),
        return_carrier=ret_first.get("airline", "—") if ret_first else "—",
        return_flight_number=ret_first.get("flight_number", "—") if ret_first else "—",
        return_departure_time=ret_first.get("departure_airport", {}).get("time", "—") if ret_first else "—",
        return_arrival_time=ret_last.get("arrival_airport", {}).get("time", "—") if ret_last else "—",
        booking_url=booking_url,
        raw_offer=offer,
    )


def _extract_booking_url(offer: dict) -> str:
    """
    Récupère un lien de réservation depuis l'offre.
    Fallback : URL Google Flights générique si rien d'autre n'est dispo.
    """
    # 1) Cas où SerpApi a déjà inclus des booking_options
    booking_options = offer.get("booking_options") or []
    for opt in booking_options:
        # Cas 1a : option groupée "together"
        together = opt.get("together", {})
        url = together.get("booking_request", {}).get("url") if together else None
        if url:
            return url
        # Cas 1b : option "departing"
        departing = opt.get("departing", {})
        url = departing.get("booking_request", {}).get("url") if departing else None
        if url:
            return url

    # 2) Fallback : URL Google Flights générique
    return "https://www.google.com/travel/flights"
