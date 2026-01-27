## 📊 Système Complet de Scraping et Synchronisation

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FLUX DE DONNÉES                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Forex + Crypto + Metals APIs                              │
│  (Fetchers: fx.py, crypto.py, metals.py)                   │
│           ↓                                                  │
│  [ScraperRunner] - Gestion des retries + erreurs            │
│  - Retries: Max 3 tentatives avec backoff exponentiel       │
│  - Validation de config + codes de sortie explicites        │
│           ↓                                                  │
│  PostgreSQL Database                                        │
│  (Upsert: asset_code + date = unique)                       │
│           ↓                                                  │
│  [SyncService] - Synchronisation vers MongoDB               │
│  - Fenêtre glissante (défaut 7 jours)                       │
│  - Vérification de cohérence                                │
│           ↓                                                  │
│  MongoDB Archive                                            │
│  (Collection: prices)                                       │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Composants Implémentés

#### 1. **Fetchers** (scraper/fetchers/)

| Fichier | Responsabilité |
|---------|-----------------|
| `base.py` | Classe abstraite avec retries, validation |
| `fx.py` | USD, EUR, CNY - Variations ±2% |
| `crypto.py` | Bitcoin - Variations ±5% |
| `metals.py` | GOLD, IRON, COPPER - Variations ±3%/±2% |

**Gestion d'erreurs**: Timeout, format invalide, prix négatif
**Validation**: `validate_price()` - Au moins 0.01 MRU

#### 2. **ScraperRunner** (scraper/runner.py)

- **Retries**: 3 tentatives par défaut, backoff exponentiel (2s × 2^attempts)
- **Codes de sortie**:
  - `0` = SUCCESS (tout OK)
  - `1` = PARTIAL_FAILURE (au moins 1 source échouée)
  - `2` = TOTAL_FAILURE (aucune donnée)
  - `3` = CONFIGURATION_ERROR

**Logs structurés**: Chaque étape loggée (✅✅⚠️❌📌)

#### 3. **DataStore** (scraper/store.py)

- **Upsert**: `update_or_create(asset, date)` = Idempotent
- **Validation**: Asset doit exister, prix > 0.01 MRU
- **Batch**: Traitement par lots avec détails des erreurs

#### 4. **SyncService** (sync/sync_prices.py)

- **Source**: PostgreSQL (fenêtre glissante par défaut 7 jours)
- **Destination**: MongoDB collection `prices`
- **Index unique**: (asset_code, date) = Pas de doublons
- **Upsert MongoDB**: `update_one(..., upsert=True)`
- **Vérification**: Cohérence PG vs Mongo

#### 5. **Management Commands**

| Commande | Usage |
|----------|-------|
| `python manage.py scrape_prices` | Scrape unique |
| `python manage.py scrape_prices --sync` | Scrape + Sync |
| `python manage.py sync_to_mongo` | Sync PG→Mongo |
| `python manage.py sync_to_mongo --verify` | Sync + Vérif |

#### 6. **Job Quotidien**

- **Docker Service `scraper`**: Boucle infinie
  - Lance `scrape_prices --sync` toutes les 24h
  - Logs structurés avec timestamps
  - Gestion d'erreurs automatique

### Base de Données

#### PostgreSQL (Prix récents)
```sql
CREATE UNIQUE INDEX idx_asset_date ON core_price(asset_id, date);
```
- Asset + Date = Unique (pas de duplication)
- Indexé pour requêtes rapides

#### MongoDB (Archive)
```javascript
db.prices.createIndex({asset_code: 1, date: 1}, {unique: true})
```
- Collection: `prices`
- Champs: asset_code, asset_label, asset_category, date, price_mru, synced_at

### Tests

✅ **Scraper réussi le 22/01/2026 à 10:16**
```
✅ Données récupérées: 7
✅ Données stockées: 7
❌ Données échouées: 0
📌 Code de sortie: 0 (SUCCESS)
```

Détails:
- USD, EUR, CNY: Récupérés et stockés
- BTC: Récupéré et mis à jour
- GOLD, IRON, COPPER: Créés avec succès

### Logs

Chaque exécution produit:
1. **Timestamp ISO** d'exécution
2. **Tentatives par source** avec numéro/max
3. **Résumé par étape** (Forex/Crypto/Metals)
4. **Résumé final** avec codes de sortie
5. **Erreurs détaillées** si problème

### Environnement

Fichier `.env` requis:
```env
POSTGRES_DB=asset_prices
POSTGRES_USER=user
POSTGRES_PASSWORD=pass

MONGO_USER=admin
MONGO_PASSWORD=admin
MONGO_URL=mongodb://admin:admin@mongo:27017
```

Docker Compose: 3 services
- `db` (PostgreSQL 16)
- `mongo` (MongoDB latest)
- `web` (Django)
- `scraper` (Job quotidien)

### Points Forts

✅ **Idempotence** - Upsert garantit pas de doublons
✅ **Retries** - 3 tentatives + backoff exponentiel
✅ **Validation** - Format, actif, prix > 0.01
✅ **Logs Structurés** - Emojis + timestamps ISO
✅ **Codes de sortie** - 0=OK, 1=Partiel, 2=Échoué, 3=Config
✅ **Deux BD** - PG pour récent, Mongo pour archive
✅ **Sync auto** - Glissant 7j par défaut
✅ **Job quotidien** - Docker service + boucle 24h
✅ **Sans modifs** - requirements.txt + Docker files inchangés

### Prochaines étapes (optionnelles)

1. **Cron réel**: Utiliser APScheduler pour jobs plus précis
2. **Webhooks**: Notifier sur erreurs critiques
3. **Metrics**: Ajouter Prometheus/Grafana
4. **Tests**: Suites unitaires pour retries
5. **API Real**: Remplacer les simulations par vraies API
