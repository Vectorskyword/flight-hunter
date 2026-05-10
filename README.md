# ✈️ Flight Hunter

Agent IA en Python pour trouver les billets d'avion les moins chers via **Google Flights** (SerpApi).

Deux interfaces :
- 🖥️ **CLI** — pour la recherche rapide en ligne de commande
- 🌐 **Web App Streamlit** — pour le scan de week-ends entiers avec interface graphique

---

## 📁 Structure du projet

```
flight-hunter/
├── main.py                          # Point d'entrée CLI (Click)
├── streamlit_app.py                 # Point d'entrée Web (Streamlit)
├── requirements.txt
├── .env.example                     # Modèle à copier en .env
├── README.md
└── flight_hunter/
    ├── config/
    │   └── settings.py              # Chargement clé API
    ├── services/
    │   ├── serpapi_client.py        # Wrapper Google Flights
    │   └── weekend_scanner.py       # Scanner de week-ends
    ├── agent/
    │   └── flight_agent.py          # Orchestrateur de recherche
    └── utils/
        ├── exceptions.py
        └── formatter.py             # Affichage CLI
```

---

## 🚀 Guide d'installation

### Étape 1 — Compte SerpApi (gratuit, 250 req/mois)

1. https://serpapi.com/users/sign_up
2. Vérifie ton email
3. Récupère ta clé : https://serpapi.com/manage-api-key

### Étape 2 — Cloner & installer

```bash
git clone https://github.com/<ton-username>/flight-hunter.git
cd flight-hunter
python -m venv venv
.\venv\Scripts\Activate.ps1            # Windows PowerShell
# source venv/bin/activate              # Linux / macOS
pip install -r requirements.txt
```

### Étape 3 — Configurer la clé

```bash
copy .env.example .env                 # Windows
# cp .env.example .env                  # Linux / macOS
notepad .env                           # Édite et colle ta clé SerpApi
```

---

## 🖥️ Mode CLI

```bash
# Mode interactif
python main.py

# Recherche directe
python main.py --from Bordeaux --to Marrakech --date 2026-08-15

# Aller-retour avec budget
python main.py --from Paris --to Tokyo --date 2026-09-01 --return 2026-09-15 --max 5

# Vols directs uniquement
python main.py --from BOD --to LIS --date 2026-07-10 --non-stop
```

---

## 🌐 Mode Web (Streamlit)

```bash
streamlit run streamlit_app.py
```

Ouvre automatiquement le navigateur sur `http://localhost:8501`.

### Fonctionnalités web

- 🔍 Recherche par mois entier
- 📅 **Filtre Week-end strict** : départ vendredi après 16h00, retour dimanche
- 💰 Budget max ajustable
- 🛫 Vols directs uniquement (option)
- 🃏 Affichage cartes ou tableau interactif
- 🔗 Bouton "Voir le vol" → ouvre Google Flights
- ⚡ Cache 1h pour économiser le quota SerpApi

---

## 🌍 Villes supportées

Noms de villes principaux reconnus automatiquement. Sinon utilise le **code IATA à 3 lettres** :
- BOD = Bordeaux, RAK = Marrakech, CDG = Paris (CDG)
- LIS = Lisbonne, BCN = Barcelone, FCO = Rome
- HND = Tokyo, JFK = New York, DXB = Dubaï

Liste IATA complète : https://www.iata.org/en/publications/directories/code-search/

---

## 🛠️ Évolutions futures

### Alerte mail quand prix < seuil

`flight_hunter/services/notifier.py` avec `smtplib` + cron/Task Scheduler.

### Déploiement public (Streamlit Cloud)

```bash
# Le projet est prêt à être déployé sur https://share.streamlit.io
# Il suffit de :
# 1. Pusher le repo sur GitHub
# 2. Connecter Streamlit Cloud au repo
# 3. Définir la variable d'environnement SERPAPI_KEY dans Streamlit Cloud secrets
```

### Agent LLM avec LangChain

Décommente les lignes LangChain dans `requirements.txt`, puis enrobe le `FlightAgent`
en tools LangChain pour parser du langage naturel.

---

## 🐛 Erreurs courantes

| Erreur | Solution |
|---|---|
| `SERPAPI_KEY doit être définie` | Crée `.env` à partir de `.env.example` et colle ta clé |
| `Ville inconnue` | Utilise le code IATA à 3 lettres |
| `Quota dépassé` | 250 requêtes/mois max. Attends le mois prochain ou prends un plan payant. |
| `'streamlit' n'est pas reconnu` | Réactive le venv : `.\venv\Scripts\Activate.ps1` |

---

## 📚 Ressources

- [SerpApi Google Flights](https://serpapi.com/google-flights-api)
- [Streamlit Docs](https://docs.streamlit.io)
- [Codes IATA](https://www.iata.org/en/publications/directories/code-search/)

---

**Stack** : Python 3.10+ • SerpApi • Streamlit • Pandas • Click • Rich
