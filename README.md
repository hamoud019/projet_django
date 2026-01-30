# Projet Suivi des Actifs (MRU)

Application Django pour suivre des actifs financiers en MRU (devises, metaux, crypto).
Les prix sont stockes en PostgreSQL, avec une synchronisation optionnelle vers MongoDB.
Un scraper quotidien met a jour les prix depuis l API de la BCM (devises) et des sources simulees (metaux, crypto).
Des vues de comparaison et de prediction sont incluses.

## Fonctionnalites

- Tableau de bord des derniers prix
- Fiche actif avec historique et graphiques
- Comparaison par categorie (devises, metaux, crypto)
- Prediction simple a partir de l historique
- Administration Django pour gerer les actifs
- Scraper quotidien + sync MongoDB optionnelle

## Sources de donnees

- Devises (USD, EUR, CNY): API Banque Centrale de Mauritanie (BCM)
- Metaux (GOLD, IRON, COPPER): simulation
- Crypto (BTC): simulation
- Historique (optionnel): Yahoo Finance pour BTC, GOLD, COPPER, IRON

## Installation rapide (Docker)

```bash
# Demarrer la stack (PostgreSQL, MongoDB, Django, scraper)
docker-compose up -d

# Initialiser des donnees de demo (2 ans)
docker-compose exec web python manage.py init_data

# Creer un compte admin
docker-compose exec web python manage.py createsuperuser
```

L application est disponible sur:
- http://localhost:8000
- http://localhost:8000/admin

Le service `scraper` execute `python manage.py scrape_prices --sync` toutes les 24h.

## Installation locale

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# ou: source venv/bin/activate

pip install -r requirements.txt
python manage.py migrate
python manage.py init_data
python manage.py runserver
```

## Commandes utiles

```bash
# Donnees de demo (2 ans)
python manage.py init_data

# Scraper quotidien (devises BCM + metaux/crypto simules)
python manage.py scrape_prices
python manage.py scrape_prices --sync

# Historique complet des devises depuis BCM
python manage.py scrape_historical_fx --days 730

# Historique Yahoo Finance (BTC, GOLD, COPPER, IRON)
python manage.py scrape_historical_yahoo --days 730

# Synchronisation PostgreSQL -> MongoDB
python manage.py sync_prices_to_mongo --days 7 --verify
```

## Routes

- `/` : accueil (dernier prix par actif)
- `/asset/<code>/` : detail d un actif
- `/comparison/` : comparaison des actifs
- `/prediction/` : predictions
- `/admin/` : administration

## Configuration

Variables dans `.env`:
- `DJANGO_SECRET_KEY`
- `DJANGO_DEBUG`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `POSTGRES_HOST`
- `POSTGRES_PORT`

MongoDB (optionnel):
- `MONGO_URL` (ex: `mongodb://user:pass@host:27017`)

## Structure du projet

```
project/                # Configuration Django
core/                   # App principale (models, views, templates)
scraper/                # Pipeline de scraping
sync/                   # Synchronisation MongoDB
scripts/                # Scripts utilitaires
```
