"""
Point d'entrée CLI de Flight Hunter.

Exemples :
    python main.py
    python main.py --from Bordeaux --to Marrakech --date 2026-06-15
    python main.py --from Paris --to Tokyo --date 2026-09-01 --return 2026-09-15 --max 5
    python main.py --from BOD --to RAK --date 2026-06-15      # codes IATA directs
"""
from __future__ import annotations

import sys

import click

from flight_hunter.agent.flight_agent import FlightAgent, FlightSearchRequest
from flight_hunter.config.settings import load_settings
from flight_hunter.utils.exceptions import FlightHunterError
from flight_hunter.utils.formatter import (
    console,
    display_error,
    display_info,
    display_offers,
    display_success,
)


@click.command()
@click.option("--from", "origin", prompt="Ville de départ", help="Ex: Bordeaux ou BOD")
@click.option("--to", "destination", prompt="Ville d'arrivée", help="Ex: Marrakech ou RAK")
@click.option(
    "--date", "departure_date",
    prompt="Date de départ (YYYY-MM-DD)",
    help="Format : YYYY-MM-DD",
)
@click.option(
    "--return", "return_date",
    default=None,
    help="Date de retour optionnelle (YYYY-MM-DD)",
)
@click.option("--adults", default=1, type=int, help="Nombre d'adultes (1-9)")
@click.option("--max", "max_results", default=10, type=int, help="Nombre de résultats")
@click.option("--non-stop", is_flag=True, help="Vols directs uniquement")
def cli(origin, destination, departure_date, return_date, adults, max_results, non_stop):
    """Flight Hunter — Trouve les vols les moins chers via Google Flights."""
    console.print("[bold magenta]🛫 Flight Hunter[/bold magenta]\n")

    try:
        settings = load_settings()
    except EnvironmentError as exc:
        display_error(str(exc))
        sys.exit(1)

    agent = FlightAgent(settings)

    request = FlightSearchRequest(
        origin_city=origin,
        destination_city=destination,
        departure_date=departure_date,
        return_date=return_date,
        adults=adults,
        max_results=max_results,
        non_stop=non_stop,
    )

    display_info(
        f"Recherche en cours : {origin} → {destination} | "
        f"Aller : {departure_date}"
        + (f" | Retour : {return_date}" if return_date else " (aller simple)")
        + f" | {adults} adulte(s)"
    )

    try:
        with console.status("[bold green]Interrogation de Google Flights via SerpApi...[/]"):
            offers = agent.search_cheapest_flights(request)
    except ValueError as exc:
        display_error(f"Paramètres invalides : {exc}")
        sys.exit(2)
    except FlightHunterError as exc:
        display_error(str(exc))
        sys.exit(3)
    except Exception as exc:  # noqa: BLE001 — filet de sécurité pour la CLI
        display_error(f"Erreur inattendue : {exc}")
        sys.exit(99)

    display_offers(offers, origin, destination, currency=agent.currency)
    display_success(f"{len(offers)} offre(s) trouvée(s), triée(s) par prix croissant.")


if __name__ == "__main__":
    cli()
