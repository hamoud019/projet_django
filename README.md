# Projet Suivi des Actifs (MRU)

Application Django pour suivre les prix des actifs (Crypto, Métaux, Devises) en Mauritanie (MRU).

## 🚀 Installation et Démarrage

### Avec Docker Compose

```bash
# Démarrer les conteneurs
docker-compose up -d

# Appliquer les migrations
docker-compose exec web python manage.py migrate

# Initialiser les données d'exemple
docker-compose exec web python manage.py init_data
```

### Localement

```bash
# Créer l'environnement virtuel
python -m venv venv
source venv/bin/activate  # ou venv\Scripts\activate sur Windows

# Installer les dépendances
pip install -r requirements.txt

# Appliquer les migrations
python manage.py migrate

# Initialiser les données
python manage.py init_data

# Démarrer le serveur
python manage.py runserver
```

## 📊 Données Disponibles

Le script `init_data` ajoute 3 actifs de démonstration :

1. **Bitcoin (BTC)** - Catégorie: Crypto
   - Prix: 44 000 - 48 000 MRU
   
2. **Gold (XAU)** - Catégorie: Métal
   - Prix: 2 000 - 2 200 MRU
   
3. **Dollar US (USD)** - Catégorie: Devises
   - Prix: 600 - 620 MRU

Chaque actif a 7 jours de prix historiques.

## 🌐 Accès à l'Application

- **URL**: http://localhost:8000
- **Admin**: http://localhost:8000/admin
  - Utilisateur: admin
  - Password: (à créer avec `python manage.py createsuperuser`)

## 📋 Routes Disponibles

- `/` - Accueil (derniers prix)
- `/asset/<code>/` - Détail d'un actif
- `/comparison/` - Comparaison des actifs
- `/prediction/` - Prédictions de prix
- `/admin/` - Interface d'administration

## 🔧 Ajouter de Nouveaux Actifs

Via l'interface admin: http://localhost:8000/admin/core/asset/

Ou éditer le script `/core/management/commands/init_data.py` et relancer:
```bash
python manage.py init_data
```

## 📝 Structure du Projet

```
├── project/              # Configuration Django
│   ├── settings.py      # Paramètres Django
│   ├── urls.py          # Routes principales
│   └── wsgi.py
├── core/                # Application principale
│   ├── models.py        # Modèles (Asset, Price)
│   ├── views.py         # Vues
│   ├── urls.py          # Routes core
│   ├── admin.py         # Panneau admin
│   ├── services/        # Logique métier
│   ├── api/             # Routes API (optionnel)
│   ├── templates/       # Templates HTML
│   └── management/commands/
│       └── init_data.py # Script d'initialisation
├── manage.py            # Gestionnaire Django
├── requirements.txt     # Dépendances
└── docker-compose.yml   # Configuration Docker
```

## ⚙️ Configuration

Les variables d'environnement sont définies dans `.env`:
- `DJANGO_SECRET_KEY` - Clé secrète Django
- `DJANGO_DEBUG` - Mode debug (1=True, 0=False)
- `POSTGRES_DB` - Nom de la base de données
- `POSTGRES_USER` - Utilisateur PostgreSQL
- `POSTGRES_PASSWORD` - Mot de passe PostgreSQL
- `POSTGRES_HOST` - Hôte PostgreSQL
- `POSTGRES_PORT` - Port PostgreSQL

## 🐛 Dépannage

### Erreur: "No module named 'rest_framework'"
Les packages optionnels (rest_framework, corsheaders) ne sont pas dans requirements.txt. 
Pour les ajouter:
1. Ajouter à requirements.txt:
   ```
   djangorestframework>=3.14
   django-cors-headers>=4.0
   ```
2. Reinstaller: `pip install -r requirements.txt`
3. Ajouter à INSTALLED_APPS dans settings.py
4. Décommenter les routes API dans urls.py

### Erreur: "Connection refused"
PostgreSQL n'est pas accessible. Vérifier:
1. Le service PostgreSQL est démarré
2. Les variables d'environnement (.env) sont correctes
3. Le conteneur `postgres_mru` est en cours d'exécution

## 📞 Support

Pour toute question ou problème, consultez les logs:
```bash
docker-compose logs -f web
```
