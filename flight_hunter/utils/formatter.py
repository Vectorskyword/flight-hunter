"""
Mise en forme des résultats de vols pour l'affichage CLI.
Utilise la bibliothèque `rich` pour un rendu propre dans le terminal.

Format des données : SerpApi (Google Flights).
Documentation : https://serpapi.com/google-flights-api
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from rich.console import Console
from rich.table import Table


console = Console()


def _format_datetime(dt_str: str) -> str:
    """'2026-06-15 08:30' -> '15/06/2026 08:30'"""
    try:
        dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M")
        return dt.strftime("%d/%m/%Y %H:%M")
    except (ValueError, TypeError):
        return dt_str or "—"


def _format_duration(minutes: int) -> str:
    """600 (minutes) -> '10h00'"""
    if not minutes:
        return "—"
    h, m = divmod(int(minutes), 60)
    return f"{h}h{m:02d}"


def parse_offer(offer: dict) -> dict:
    """
    Extrait les infos clés d'une offre SerpApi (Google Flights).

    Une offre contient une liste de "flights" (segments).
    On prend l'aéroport de départ du premier segment et l'aéroport
    d'arrivée du dernier segment.
    """
    flights = offer.get("flights", [])
    if not flights:
        return {
            "price_total": 0, "carrier": "?", "flight_number": "?",
            "departure_airport": "?", "departure_time": "—",
            "arrival_airport": "?", "arrival_time": "—",
            "duration": "—", "stops": 0, "type": "—",
        }

    first = flights[0]
    last = flights[-1]

    return {
        "price_total": float(offer.get("price", 0)),
        "carrier": first.get("airline", "—"),
        "flight_number": first.get("flight_number", "—"),
        "departure_airport": first.get("departure_airport", {}).get("id", "—"),
        "departure_time": _format_datetime(first.get("departure_airport", {}).get("time", "")),
        "arrival_airport": last.get("arrival_airport", {}).get("id", "—"),
        "arrival_time": _format_datetime(last.get("arrival_airport", {}).get("time", "")),
        "duration": _format_duration(offer.get("total_duration", 0)),
        "stops": max(0, len(flights) - 1),
        "type": offer.get("type", "—"),
    }


def display_offers(offers: List[dict], origin: str, destination: str, currency: str = "EUR") -> None:
    """Affiche un tableau récapitulatif des offres triées par prix croissant."""
    table = Table(
        title=f"✈️  Meilleures offres : {origin} → {destination}",
        show_lines=True,
        header_style="bold cyan",
    )
    table.add_column("#", justify="right", style="dim")
    table.add_column("Prix", justify="right", style="bold green")
    table.add_column("Compagnie", justify="center")
    table.add_column("Vol", justify="center")
    table.add_column("Départ", justify="left")
    table.add_column("Arrivée", justify="left")
    table.add_column("Durée", justify="center")
    table.add_column("Escales", justify="center")
    table.add_column("Type", justify="center")

    for idx, offer in enumerate(offers, start=1):
        info = parse_offer(offer)
        table.add_row(
            str(idx),
            f"{info['price_total']:.2f} {currency}",
            info["carrier"],
            info["flight_number"],
            f"{info['departure_airport']}\n{info['departure_time']}",
            f"{info['arrival_airport']}\n{info['arrival_time']}",
            info["duration"],
            "Direct" if info["stops"] == 0 else str(info["stops"]),
            info["type"],
        )

    console.print(table)


def display_error(message: str) -> None:
    """Affiche une erreur en rouge."""
    console.print(f"[bold red]❌ {message}[/bold red]")


def display_info(message: str) -> None:
    """Affiche une info en bleu."""
    console.print(f"[bold blue]ℹ️  {message}[/bold blue]")


def display_success(message: str) -> None:
    """Affiche un succès en vert."""
    console.print(f"[bold green]✅ {message}[/bold green]")
