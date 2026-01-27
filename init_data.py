#!/usr/bin/env python
"""
Script pour initialiser les données du projet avec des actifs de démonstration
Exécution: python init_data.py
"""
import os
import sys
import django
from datetime import datetime, timedelta
from decimal import Decimal

# Configuration Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
sys.path.insert(0, str(os.path.dirname(__file__)))

django.setup()

from core.models import Asset, Price


def create_sample_data():
    """Crée les données d'exemple"""
    
    # Définir les actifs
    assets_data = [
        {
            'code': 'BTC',
            'label': 'Bitcoin',
            'category': 'crypto',
            'prices': [
                (Decimal('44000.00'), -30),
                (Decimal('45000.00'), -25),
                (Decimal('45500.00'), -20),
                (Decimal('46000.00'), -15),
                (Decimal('46500.00'), -10),
                (Decimal('47000.00'), -5),
                (Decimal('48000.00'), 0),
            ]
        },
        {
            'code': 'XAU',
            'label': 'Gold',
            'category': 'metal',
            'prices': [
                (Decimal('2000.00'), -30),
                (Decimal('2050.00'), -25),
                (Decimal('2080.00'), -20),
                (Decimal('2100.00'), -15),
                (Decimal('2120.00'), -10),
                (Decimal('2150.00'), -5),
                (Decimal('2200.00'), 0),
            ]
        },
        {
            'code': 'USD',
            'label': 'Dollar US',
            'category': 'fx',
            'prices': [
                (Decimal('600.00'), -30),
                (Decimal('605.00'), -25),
                (Decimal('608.00'), -20),
                (Decimal('610.00'), -15),
                (Decimal('612.00'), -10),
                (Decimal('615.00'), -5),
                (Decimal('620.00'), 0),
            ]
        },
    ]
    
    today = datetime.now().date()
    
    for asset_info in assets_data:
        # Créer ou obtenir l'actif
        asset, created = Asset.objects.get_or_create(
            code=asset_info['code'],
            defaults={
                'label': asset_info['label'],
                'category': asset_info['category'],
            }
        )
        
        if created:
            print(f"✅ Actif créé: {asset.code} - {asset.label}")
        else:
            print(f"ℹ️  Actif existant: {asset.code} - {asset.label}")
        
        # Créer les prix
        for price_mru, days_ago in asset_info['prices']:
            date = today + timedelta(days=days_ago)
            price, price_created = Price.objects.get_or_create(
                asset=asset,
                date=date,
                defaults={'price_mru': price_mru}
            )
            
            if price_created:
                print(f"   📊 Prix ajouté: {date} - {price_mru} MRU")
            else:
                print(f"   ℹ️  Prix existant: {date} - {price_mru} MRU")
    
    print("\n✅ Initialisation des données complète!")
    print("\n📋 Résumé:")
    print(f"   Total actifs: {Asset.objects.count()}")
    print(f"   Total prix: {Price.objects.count()}")


if __name__ == '__main__':
    try:
        create_sample_data()
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
