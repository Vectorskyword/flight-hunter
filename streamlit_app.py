"""
Flight Hunter — Web App Streamlit.

Lancement :
    streamlit run streamlit_app.py

L'app interroge SerpApi (Google Flights), scanne tous les week-ends d'un mois
choisi par l'utilisateur, et affiche les meilleures offres aller-retour
"week-end strict" (vendredi soir → dimanche).
"""
from __future__ import annotations

import calendar
from datetime import date
from typing import List

import pandas as pd
import streamlit as st

from flight_hunter.config.settings import load_settings
from flight_hunter.services.serpapi_client import SerpApiClient
from flight_hunter.services.weekend_scanner import (
    WeekendOffer,
    WeekendScanner,
    list_weekends_in_month,
)
from flight_hunter.utils.exceptions import (
    APIConfigurationError,
    APIRateLimitError,
    FlightHunterError,
    InvalidLocationError,
)


# ====================================================================== #
# Configuration de la page Streamlit                                     #
# ====================================================================== #
st.set_page_config(
    page_title="Weekend Flight Hunter ✈️",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ====================================================================== #
# CSS personnalisé pour un look moderne                                  #
# ====================================================================== #
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        color: #6c757d;
        font-size: 1.1rem;
        margin-bottom: 2rem;
    }
    .offer-card {
        background: linear-gradient(135deg, #f6f8fa 0%, #ffffff 100%);
        border: 1px solid #e1e4e8;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        transition: all 0.2s ease;
    }
    .offer-card:hover {
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        transform: translateY(-2px);
    }
    .price-tag {
        font-size: 2rem;
        font-weight: 700;
        color: #28a745;
    }
    .weekend-label {
        font-size: 1.1rem;
        font-weight: 600;
        color: #495057;
    }
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 0.5rem 1.5rem;
        font-weight: 600;
    }
    .stButton > button:hover {
        background: linear-gradient(90deg, #5568d3 0%, #6a3f8f 100%);
    }
</style>
""", unsafe_allow_html=True)


# ====================================================================== #
# Chargement de la configuration (clé API)                               #
# ====================================================================== #
@st.cache_resource
def get_scanner() -> WeekendScanner:
    """Crée le scanner une seule fois et le réutilise (singleton)."""
    settings = load_settings()
    client = SerpApiClient(settings)
    return WeekendScanner(client)


# ====================================================================== #
# Cache des recherches pour économiser le quota SerpApi                  #
# ====================================================================== #
@st.cache_data(ttl=3600, show_spinner=False)  # cache 1h
def cached_scan(
    origin_iata: str,
    destination_iata: str,
    year: int,
    month: int,
    max_price: float,
    non_stop: bool,
    currency: str,
) -> List[dict]:
    """
    Lance le scan et retourne une liste de dicts sérialisables
    (Streamlit ne peut pas cacher des objets complexes).
    """
    scanner = get_scanner()
    offers = scanner.scan_month(
        origin_iata=origin_iata,
        destination_iata=destination_iata,
        year=year,
        month=month,
        max_price=max_price if max_price > 0 else None,
        non_stop=non_stop,
        currency=currency,
    )
    return [_offer_to_dict(o) for o in offers]


def _offer_to_dict(offer: WeekendOffer) -> dict:
    return {
        "weekend_label": offer.weekend.label,
        "friday": offer.weekend.friday.isoformat(),
        "sunday": offer.weekend.sunday.isoformat(),
        "price": offer.price,
        "currency": offer.currency,
        "outbound_carrier": offer.outbound_carrier,
        "outbound_flight_number": offer.outbound_flight_number,
        "outbound_departure_time": offer.outbound_departure_time,
        "outbound_arrival_time": offer.outbound_arrival_time,
        "return_carrier": offer.return_carrier,
        "return_flight_number": offer.return_flight_number,
        "return_departure_time": offer.return_departure_time,
        "return_arrival_time": offer.return_arrival_time,
        "booking_url": offer.booking_url,
    }


# ====================================================================== #
# Sidebar — Formulaire de recherche                                      #
# ====================================================================== #
def render_sidebar() -> dict:
    """Affiche le formulaire dans la sidebar et retourne les paramètres."""
    st.sidebar.markdown("### 🔍 Critères de recherche")

    origin = st.sidebar.text_input(
        "Ville de départ",
        value="Bordeaux",
        help="Nom de ville ou code IATA (ex: Bordeaux, BOD)",
    )

    destination = st.sidebar.text_input(
        "Ville d'arrivée",
        value="Lisbonne",
        help="Nom de ville ou code IATA (ex: Lisbonne, LIS)",
    )

    # Sélecteur mois/année
    today = date.today()
    months_fr = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin",
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre",
    ]

    col_m, col_y = st.sidebar.columns(2)
    with col_m:
        # Par défaut : mois suivant
        default_month_idx = today.month  # mois actuel index 0-11 → next month
        if default_month_idx > 11:
            default_month_idx = 0
        month = st.selectbox(
            "Mois",
            options=list(range(1, 13)),
            format_func=lambda x: months_fr[x - 1],
            index=default_month_idx if default_month_idx < 12 else 0,
        )
    with col_y:
        year = st.selectbox(
            "Année",
            options=[today.year, today.year + 1],
            index=0 if month >= today.month else 1,
        )

    # Budget
    max_price = st.sidebar.slider(
        "Budget max (€)",
        min_value=0,
        max_value=1000,
        value=300,
        step=10,
        help="0 = pas de limite de budget",
    )

    non_stop = st.sidebar.checkbox(
        "Vols directs uniquement",
        value=False,
    )

    currency = st.sidebar.selectbox(
        "Devise",
        options=["EUR", "USD", "GBP", "MAD"],
        index=0,
    )

    st.sidebar.markdown("---")
    st.sidebar.markdown(
        "📅 **Week-end strict** :  \n"
        "Départ vendredi après 16h00,  \n"
        "Retour dimanche après-midi/soir."
    )

    search_button = st.sidebar.button("🔍 Lancer la recherche", use_container_width=True)

    return {
        "origin": origin,
        "destination": destination,
        "year": year,
        "month": month,
        "max_price": max_price,
        "non_stop": non_stop,
        "currency": currency,
        "search": search_button,
    }


# ====================================================================== #
# Affichage des résultats sous forme de cartes                            #
# ====================================================================== #
def render_offer_card(offer: dict, idx: int) -> None:
    """Affiche une offre sous forme de carte."""
    with st.container():
        st.markdown('<div class="offer-card">', unsafe_allow_html=True)

        col1, col2, col3 = st.columns([2, 3, 1.5])

        with col1:
            st.markdown(
                f'<div class="weekend-label">📅 {offer["weekend_label"]}</div>',
                unsafe_allow_html=True,
            )
            st.markdown(
                f'<div class="price-tag">{offer["price"]:.0f} {offer["currency"]}</div>',
                unsafe_allow_html=True,
            )

        with col2:
            st.markdown("**🛫 Aller**")
            st.write(
                f"{offer['outbound_carrier']} — {offer['outbound_flight_number']}  \n"
                f"🕐 {offer['outbound_departure_time']} → {offer['outbound_arrival_time']}"
            )
            if offer["return_carrier"] != "—":
                st.markdown("**🛬 Retour**")
                st.write(
                    f"{offer['return_carrier']} — {offer['return_flight_number']}  \n"
                    f"🕐 {offer['return_departure_time']} → {offer['return_arrival_time']}"
                )

        with col3:
            st.link_button(
                "✈️ Voir le vol",
                url=offer["booking_url"],
                use_container_width=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)


# ====================================================================== #
# Vue tableau (alternative aux cartes)                                    #
# ====================================================================== #
def render_table(offers: List[dict]) -> None:
    """Affiche les offres sous forme de tableau pandas."""
    df = pd.DataFrame([
        {
            "Week-end": o["weekend_label"],
            "Prix": f"{o['price']:.0f} {o['currency']}",
            "Aller (compagnie)": o["outbound_carrier"],
            "Aller (vol)": o["outbound_flight_number"],
            "Départ aller": o["outbound_departure_time"],
            "Retour (compagnie)": o["return_carrier"],
            "Retour (vol)": o["return_flight_number"],
            "Lien": o["booking_url"],
        }
        for o in offers
    ])

    st.dataframe(
        df,
        use_container_width=True,
        column_config={
            "Lien": st.column_config.LinkColumn(
                "Lien", display_text="✈️ Voir"
            ),
        },
        hide_index=True,
    )


# ====================================================================== #
# Page principale                                                         #
# ====================================================================== #
def main() -> None:
    # Header
    st.markdown(
        '<div class="main-header">✈️ Weekend Flight Hunter</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="sub-header">'
        "Trouvez les vols les moins chers pour des escapades week-end "
        "(vendredi soir → dimanche)."
        "</div>",
        unsafe_allow_html=True,
    )

    # Sidebar avec formulaire
    params = render_sidebar()

    # Vérifier que la config est OK
    try:
        get_scanner()
    except EnvironmentError as exc:
        st.error(f"⚠️ Configuration manquante : {exc}")
        st.info(
            "Crée un fichier `.env` à la racine du projet en t'inspirant "
            "de `.env.example`, et mets-y ta clé SerpApi."
        )
        st.stop()
    except Exception as exc:
        st.error(f"Erreur : {exc}")
        st.stop()

    # État initial : pas de recherche
    if not params["search"]:
        st.info(
            "👈 Renseigne tes critères dans la barre latérale et clique sur "
            "**🔍 Lancer la recherche** pour démarrer."
        )

        # Aperçu des week-ends du mois sélectionné
        st.markdown("### 📅 Aperçu des week-ends scannés")
        try:
            weekends = list_weekends_in_month(params["year"], params["month"])
            if weekends:
                cols = st.columns(min(len(weekends), 5))
                for i, w in enumerate(weekends):
                    with cols[i % len(cols)]:
                        st.markdown(f"**{w.label}**")
            else:
                st.warning(
                    "Aucun week-end disponible dans ce mois "
                    "(mois passé ou aucun vendredi/dimanche)."
                )
        except Exception as exc:
            st.warning(f"Impossible de lister les week-ends : {exc}")

        return

    # Validation des inputs
    if not params["origin"] or not params["destination"]:
        st.error("Merci de renseigner une ville de départ et une ville d'arrivée.")
        return

    # Résolution des codes IATA
    try:
        scanner = get_scanner()
        origin_iata = scanner._client.get_iata_code(params["origin"])
        destination_iata = scanner._client.get_iata_code(params["destination"])
    except InvalidLocationError as exc:
        st.error(f"❌ {exc}")
        return

    st.markdown(
        f"### 🔎 Recherche en cours : **{params['origin']}** ({origin_iata}) → "
        f"**{params['destination']}** ({destination_iata})"
    )

    # Indicateur du nombre de week-ends à scanner
    weekends = list_weekends_in_month(params["year"], params["month"])
    st.caption(f"📅 {len(weekends)} week-end(s) à scanner")

    # Lancement de la recherche avec spinner
    try:
        with st.spinner(
            f"⏳ Interrogation de Google Flights pour {len(weekends)} week-end(s)... "
            "(peut prendre 30-60 secondes)"
        ):
            offers = cached_scan(
                origin_iata=origin_iata,
                destination_iata=destination_iata,
                year=params["year"],
                month=params["month"],
                max_price=float(params["max_price"]),
                non_stop=params["non_stop"],
                currency=params["currency"],
            )
    except APIConfigurationError as exc:
        st.error(f"❌ Erreur configuration : {exc}")
        return
    except APIRateLimitError as exc:
        st.error(f"❌ Quota dépassé : {exc}")
        return
    except FlightHunterError as exc:
        st.warning(f"⚠️ {exc}")
        return
    except Exception as exc:
        st.error(f"❌ Erreur inattendue : {exc}")
        return

    # Affichage des résultats
    if not offers:
        st.warning(
            f"😕 Aucune offre trouvée pour ces critères "
            f"(budget max : {params['max_price']} {params['currency']})."
        )
        st.info(
            "💡 Essaie d'augmenter le budget, de désactiver le filtre "
            "'vols directs', ou de changer de mois."
        )
        return

    st.success(f"✅ {len(offers)} offre(s) trouvée(s), triée(s) par prix croissant.")

    # Statistiques
    prices = [o["price"] for o in offers]
    col1, col2, col3 = st.columns(3)
    col1.metric("💰 Prix min", f"{min(prices):.0f} {offers[0]['currency']}")
    col2.metric("📊 Prix moyen", f"{sum(prices)/len(prices):.0f} {offers[0]['currency']}")
    col3.metric("🏷️ Prix max", f"{max(prices):.0f} {offers[0]['currency']}")

    # Choix vue cartes / tableau
    view_mode = st.radio(
        "Affichage",
        ["🃏 Cartes", "📊 Tableau"],
        horizontal=True,
    )

    st.markdown("---")

    if view_mode == "🃏 Cartes":
        for idx, offer in enumerate(offers):
            render_offer_card(offer, idx)
    else:
        render_table(offers)


if __name__ == "__main__":
    main()
