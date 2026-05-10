# ✈️ Flight Hunter

Agent IA en Python pour trouver les billets d'avion les moins chers.
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
    │   └── settings.py              # Chargement clés API (.env)
    ├── services/
    │   └── amadeus_client.py        # Wrapper API Amadeus
    ├── agent/
    │   └── flight_agent.py          # Orchestrateur de recherche
    └── utils/
        ├── exceptions.py            # Exceptions métier
        └── formatter.py             # Affichage rich
```

---

## 🚀 Guide d'installation pas-à-pas

### Étape 1 — Créer un compte Amadeus (gratuit)

1. Va sur **https://developers.amadeus.com**
2. Crée un compte (gratuit, pas de CB)
3. Une fois connecté, va dans **Self-Service Workspace** → **Create New App**
4. Donne un nom à ton app (ex: `flight-hunter-amin`) et valide
5. Tu obtiens deux clés :
   - **API Key** → ce sera ton `AMADEUS_CLIENT_ID`
   - **API Secret** → ce sera ton `AMADEUS_CLIENT_SECRET`

> 💡 L'environnement **test** est gratuit (2000 requêtes/mois) mais ne couvre que certaines routes/dates.
> Pour des données réelles complètes : passer en **production** (payant après quota gratuit).

### Étape 2 — Cloner / récupérer le projet

```bash
cd ~/Projects   # ou le dossier de ton choix
# (place ici les fichiers du projet)
cd flight_hunter
```

### Étape 3 — Créer un environnement virtuel Python

```bash
python3 -m venv venv
source venv/bin/activate          # Linux / macOS
# venv\Scripts\activate          # Windows PowerShell
```

### Étape 4 — Installer les dépendances

```bash
pip install -r requirements.txt
```

### Étape 5 — Configurer les clés API

```bash
cp .env.example .env
```

Puis ouvre `.env` et remplace les valeurs :

```env
AMADEUS_CLIENT_ID=ta_cle_publique
AMADEUS_CLIENT_SECRET=ta_cle_secrete
AMADEUS_HOSTNAME=test
DEFAULT_CURRENCY=EUR
```

### Étape 6 — Lancer la recherche !

**Mode interactif** (l'app te pose les questions) :

```bash
python main.py
```

**Mode direct** :

```bash
python main.py --from Bordeaux --to Marrakech --date 2026-06-15
```

**Avec retour et tri sur 5 résultats** :

```bash
python main.py --from Paris --to Tokyo --date 2026-09-01 --return 2026-09-15 --max 5
```

**Vols directs uniquement** :

```bash
python main.py --from Bordeaux --to Lisbonne --date 2026-07-10 --non-stop
```

---

## 🧪 Test rapide sans API

Tu peux tester l'import des modules sans appeler l'API :

```bash
python -c "from flight_hunter.agent.flight_agent import FlightAgent; print('✅ OK')"
```

---

## 🛠️ Évolutions prévues (architecture pensée pour)

### 1. Alerte mail quand prix < seuil

Crée `flight_hunter/services/notifier.py` avec `smtplib`, et dans `FlightAgent` :

```python
def watch_price(self, request, threshold_eur):
    offers = self.search_cheapest_flights(request)
    if offers and float(offers[0]["price"]["total"]) < threshold_eur:
        notifier.send_email(...)
```

À planifier ensuite via `cron` (Linux) ou `Task Scheduler` (Windows).

### 2. Interface web (FastAPI)

Crée `web/app.py` :

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

Ensuite branche-le sur un agent Anthropic / OpenAI pour parser
*"Trouve-moi un vol pas cher pour Marrakech la semaine prochaine"*.

---

## 🐛 Gestion d'erreurs

| Exception                | Cause                          | Code de sortie CLI |
|--------------------------|--------------------------------|--------------------|
| `EnvironmentError`       | `.env` manquant ou incomplet   | `1`                |
| `ValueError`             | Date passée, format invalide   | `2`                |
| `APIConfigurationError`  | Clés invalides / 401           | `3`                |
| `APIRateLimitError`      | Quota dépassé / 429            | `3`                |
| `NoFlightsFoundError`    | Aucun vol pour ces critères    | `3`                |
| `InvalidLocationError`   | Ville/code IATA inconnu        | `3`                |

---

## 📚 Ressources

- [Amadeus for Developers](https://developers.amadeus.com/self-service)
- [SDK Python amadeus4dev](https://github.com/amadeus4dev/amadeus-python)
- [Codes IATA](https://www.iata.org/en/publications/directories/code-search/)

---

**Auteur** : Amin Hadariya
**Stack** : Python 3.10+ • Amadeus API • Click • Rich
