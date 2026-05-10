# ✈️ Flight Hunter

Agent IA en Python pour trouver les billets d'avion les moins chers via **Google Flights** (SerpApi).
Architecture modulaire, prête à évoluer (alertes mail, interface web, agent LLM).

---

## 📁 Structure du projet

```
flight_hunter/
├── main.py                          # Point d'entrée CLI (Click)
├── requirements.txt
├── .env.example                     # Modèle à copier en .env
├── README.md
└── flight_hunter/
    ├── config/
    │   └── settings.py              # Chargement clé API (.env)
    ├── services/
    │   └── serpapi_client.py        # Wrapper API SerpApi/Google Flights
    ├── agent/
    │   └── flight_agent.py          # Orchestrateur de recherche
    └── utils/
        ├── exceptions.py            # Exceptions métier
        └── formatter.py             # Affichage rich
```

---

## 🚀 Guide d'installation pas-à-pas

### Étape 1 — Créer un compte SerpApi (gratuit)

1. Va sur **https://serpapi.com/users/sign_up**
2. Inscris-toi (250 requêtes/mois gratuites, pas de CB requise)
3. Vérifie ton email
4. Récupère ta clé API sur **https://serpapi.com/manage-api-key**

### Étape 2 — Cloner le projet

```bash
git clone https://github.com/<ton-username>/flight-hunter.git
cd flight-hunter
```

### Étape 3 — Créer un environnement virtuel Python

```bash
python -m venv venv
venv\Scripts\activate          # Windows PowerShell
# source venv/bin/activate     # Linux / macOS
```

### Étape 4 — Installer les dépendances

```bash
pip install -r requirements.txt
```

### Étape 5 — Configurer la clé API

```bash
copy .env.example .env         # Windows
# cp .env.example .env         # Linux / macOS
```

Puis ouvre `.env` et remplace `ta_cle_serpapi_ici` par ta vraie clé.

### Étape 6 — Lancer la recherche !

```bash
python main.py
```

Ou en mode direct :

```bash
python main.py --from Bordeaux --to Marrakech --date 2026-06-15
python main.py --from Paris --to Tokyo --date 2026-09-01 --return 2026-09-15 --max 5
python main.py --from BOD --to RAK --date 2026-06-15 --non-stop
```

---

## 🌍 Villes supportées

Les noms des grandes villes françaises, marocaines, européennes, américaines, asiatiques et africaines sont reconnus automatiquement.

Si une ville n'est pas reconnue, utilise directement son **code IATA à 3 lettres** :
- BOD = Bordeaux
- RAK = Marrakech
- CDG = Paris (Charles de Gaulle)
- HND = Tokyo (Haneda)
- JFK = New York

Liste complète : https://www.iata.org/en/publications/directories/code-search/

---

## 🛠️ Évolutions prévues

### 1. Alerte mail quand prix < seuil

Crée `flight_hunter/services/notifier.py` avec `smtplib`, et dans `FlightAgent` :

```python
def watch_price(self, request, threshold_eur):
    offers = self.search_cheapest_flights(request)
    if offers and float(offers[0]["price"]) < threshold_eur:
        notifier.send_email(...)
```

À planifier ensuite via `cron` (Linux) ou `Task Scheduler` (Windows).

### 2. Interface web (FastAPI)

```python
from fastapi import FastAPI
from flight_hunter.agent.flight_agent import FlightAgent, FlightSearchRequest
from flight_hunter.config.settings import load_settings

app = FastAPI()
agent = FlightAgent(load_settings())

@app.post("/search")
def search(req: FlightSearchRequest):
    return agent.search_cheapest_flights(req)
```

Puis : `uvicorn web.app:app --reload`

### 3. Agent LLM avec LangChain (langage naturel)

Décommente les lignes LangChain dans `requirements.txt`, puis :

```python
from langchain_core.tools import tool

@tool
def search_flights_tool(origin: str, destination: str, date: str) -> str:
    """Recherche des vols entre deux villes à une date donnée."""
    request = FlightSearchRequest(origin, destination, date)
    return agent.search_cheapest_flights(request)
```

Branche-le sur Claude/GPT pour parser :
*"Trouve-moi un vol pas cher pour Marrakech la semaine prochaine"*.

---

## 🐛 Gestion d'erreurs

| Exception                | Cause                          | Code de sortie CLI |
|--------------------------|--------------------------------|--------------------|
| `EnvironmentError`       | `.env` manquant ou incomplet   | `1`                |
| `ValueError`             | Date passée, format invalide   | `2`                |
| `APIConfigurationError`  | Clé invalide                   | `3`                |
| `APIRateLimitError`      | Quota dépassé (250/mois)       | `3`                |
| `NoFlightsFoundError`    | Aucun vol pour ces critères    | `3`                |
| `InvalidLocationError`   | Ville/code IATA inconnu        | `3`                |

---

## 📚 Ressources

- [SerpApi Google Flights API](https://serpapi.com/google-flights-api)
- [SDK Python google-search-results](https://github.com/serpapi/google-search-results-python)
- [Codes IATA](https://www.iata.org/en/publications/directories/code-search/)

---

**Stack** : Python 3.10+ • SerpApi (Google Flights) • Click • Rich
