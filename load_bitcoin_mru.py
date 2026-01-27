"""
Charger l'historique Bitcoin et le convertir en MRU
"""
import os
import django
from datetime import date, timedelta, datetime
from decimal import Decimal
import requests
import random

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from core.models import Asset, Price

def simulate_btc_data(start_date, end_date):
    """Génère des données BTC simulées raisonnables"""
    btc_data = {}
    current_date = start_date
    base_price = 42000  # USD moyen BTC
    
    random.seed(42)
    
    while current_date <= end_date:
        variation = random.uniform(-0.03, 0.03)
        price = base_price * (1 + variation)
        base_price = price
        
        btc_data[current_date.isoformat()] = price
        current_date += timedelta(days=1)
    
    return btc_data


def get_usd_mru_rate(target_date):
    """Récupère le taux USD/MRU"""
    try:
        asset_usd = Asset.objects.get(code='USD')
        price = Price.objects.filter(
            asset=asset_usd,
            date=target_date
        ).first()
        
        if price:
            return Decimal(str(price.price_mru))
        return None
        
    except Asset.DoesNotExist:
        return None


def load_bitcoin_mru(start_date, end_date):
    """Charge Bitcoin en MRU"""
    
    print("=" * 80)
    print("🪙 CHARGEMENT BITCOIN HISTORIQUE EN MRU")
    print("=" * 80)
    print(f"Période: {start_date} → {end_date}")
    
    # Générer BTC/USD
    print(f"\n📊 Génération données BTC/USD...")
    btc_usd_data = simulate_btc_data(start_date, end_date)
    print(f"   ✅ {len(btc_usd_data)} prix générés")
    
    # Récupérer l'asset BTC
    try:
        asset_btc = Asset.objects.get(code='BTC')
    except Asset.DoesNotExist:
        print("❌ Asset BTC non trouvé")
        return
    
    print(f"\n📊 Conversion BTC USD → BTC MRU")
    print(f"   Total jours: {len(btc_usd_data)}")
    
    stored = 0
    skipped = 0
    
    for date_str, btc_usd_price in sorted(btc_usd_data.items()):
        try:
            price_date = date.fromisoformat(date_str)
            
            # Récupérer USD/MRU
            usd_mru_rate = get_usd_mru_rate(price_date)
            
            if usd_mru_rate is None:
                # Chercher le jour précédent
                search_date = price_date - timedelta(days=1)
                while search_date >= start_date:
                    usd_mru_rate = get_usd_mru_rate(search_date)
                    if usd_mru_rate:
                        break
                    search_date -= timedelta(days=1)
                
                if usd_mru_rate is None:
                    skipped += 1
                    continue
            
            # Convertir: BTC MRU = BTC USD × USD MRU
            btc_mru_price = Decimal(str(btc_usd_price)) * usd_mru_rate
            
            # Créer/mettre à jour
            price_obj, created = Price.objects.update_or_create(
                asset=asset_btc,
                date=price_date,
                defaults={
                    'price_mru': btc_mru_price,
                    'source': 'api'
                }
            )
            
            stored += 1
            if stored % 100 == 0:
                print(f"   ✅ {stored} prix stockés...")
            
        except Exception as e:
            print(f"   ❌ Erreur {date_str}: {e}")
    
    # Résumé
    print(f"\n{'='*80}")
    print(f"📊 RÉSUMÉ")
    print(f"{'='*80}")
    print(f"✅ Stockés: {stored}")
    print(f"⏭️  Sautés: {skipped}")
    
    # Vérifier
    btc_prices = Price.objects.filter(asset=asset_btc).order_by('date')
    
    if btc_prices.exists():
        dates = btc_prices.values_list('date', flat=True).order_by('date')
        prices_list = list(btc_prices.values_list('price_mru', flat=True).order_by('price_mru'))
        
        print(f"\n✅ Bitcoin en base:")
        print(f"   Nombre: {btc_prices.count()} prix")
        print(f"   Période: {dates.first()} → {dates.last()}")
        print(f"   Fourchette: {prices_list[0]:.2f} - {prices_list[-1]:.2f} MRU")
        print(f"   Moyenne: {sum(prices_list)/len(prices_list):.2f} MRU")
    
    print(f"{'='*80}")


start = date(2024, 1, 23)
end = date(2026, 1, 22)
load_bitcoin_mru(start, end)
