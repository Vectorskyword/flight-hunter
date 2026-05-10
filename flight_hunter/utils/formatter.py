"""
Mise en forme des résultats de vols pour l'affichage CLI.
Utilise la bibliothèque `rich` pour un rendu propre dans le terminal.
"""
from __future__ import annotations

from datetime import datetime
from typing import List

from rich.console import Console
from rich.table import Table


console = Console()


def _format_iso_datetime(iso_str: str) -> str:
    """'2025-12-15T08:30:00' -> '15/12/2025 08:30'"""
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime("%d/%m/%Y %H:%M")
    except ValueError:
        return iso_str


def _format_duration(iso_duration: str) -> str:
    """'PT11H30M' -> '11h30'"""
    if not iso_duration.startswith("PT"):
        return iso_duration
    txt = iso_duration[2:].lower().replace("h", "h").replace("m", "")
    return txt or iso_duration


def parse_offer(offer: dict) -> dict:
    """Extrait les infos clés d'une offre brute Amadeus."""
    price = offer["price"]
    itineraries = offer["itineraries"]

    # Premier segment de l'aller (pour la compagnie principale)
    first_segment = itineraries[0]["segments"][0]
    last_segment_outbound = itineraries[0]["segments"][-1]

    parsed = {
        "price_total": float(price["total"]),
        "currency": price["currency"],
        "carrier": first_segment["carrierCode"],
        "flight_number": f"{first_segment['carrierCode']}{first_segment['number']}",
        "departure_airport": first_segment["departure"]["iataCode"],
        "departure_time": _format_iso_datetime(first_segment["departure"]["at"]),
        "arrival_airport": last_segment_outbound["arrival"]["iataCode"],
        "arrival_time": _format_iso_datetime(last_segment_outbound["arrival"]["at"]),
        "duration_outbound": _format_duration(itineraries[0]["duration"]),
        "stops_outbound": len(itineraries[0]["segments"]) - 1,
        "has_return": len(itineraries) > 1,
    }

    if parsed["has_return"]:
        parsed["duration_return"] = _format_duration(itineraries[1]["duration"])
        parsed["stops_return"] = len(itineraries[1]["segments"]) - 1

    return parsed


def display_offers(offers: List[dict], origin: str, destination: str) -> None:
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
    table.add_column("AR ?", justify="center")

    for idx, offer in enumerate(offers, start=1):
        info = parse_offer(offer)
        table.add_row(
            str(idx),
            f"{info['price_total']:.2f} {info['currency']}",
            info["carrier"],
            info["flight_number"],
            f"{info['departure_airport']}\n{info['departure_time']}",
            f"{info['arrival_airport']}\n{info['arrival_time']}",
            info["duration_outbound"],
            str(info["stops_outbound"]) if info["stops_outbound"] else "Direct",
            "✓" if info["has_return"] else "—",
        )

    console.print(table)


def display_error(message: str) -> None:
    """Affiche une erreur en rouge."""
    console.print(f"[bold red]❌ {message}[/bold red]")


def display_info(message: str) -> None:
    """Affiche une info en bleu."""
    console.print(f"[bold blue]ℹ️  {message}[/bold blue]")
