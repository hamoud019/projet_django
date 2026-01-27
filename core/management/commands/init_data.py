from django.core.management.base import BaseCommand
from decimal import Decimal
from datetime import datetime, timedelta
from core.models import Asset, Price
import random


class Command(BaseCommand):
    help = 'Initialise les données d\'exemple pour 2 ans'

    def handle(self, *args, **options):
        """Exécute l'initialisation des données"""
        
        # Définir les actifs
        assets_data = [
            # Devises
            {
                'code': 'USD',
                'label': 'Dollar US',
                'category': 'fx',
                'base_price': Decimal('600.00'),
                'volatility': Decimal('20.00'),
            },
            {
                'code': 'EUR',
                'label': 'Euro',
                'category': 'fx',
                'base_price': Decimal('650.00'),
                'volatility': Decimal('25.00'),
            },
            {
                'code': 'CNY',
                'label': 'Yuan Chinois',
                'category': 'fx',
                'base_price': Decimal('85.00'),
                'volatility': Decimal('5.00'),
            },
            {
                'code': 'BTC',
                'label': 'Bitcoin',
                'category': 'crypto',
                'base_price': Decimal('45000.00'),
                'volatility': Decimal('2000.00'),
            },
            # Matières premières
            {
                'code': 'GOLD',
                'label': 'Or',
                'category': 'metal',
                'base_price': Decimal('2100.00'),
                'volatility': Decimal('100.00'),
            },
            {
                'code': 'IRON',
                'label': 'Fer',
                'category': 'metal',
                'base_price': Decimal('150.00'),
                'volatility': Decimal('10.00'),
            },
            {
                'code': 'COPPER',
                'label': 'Cuivre',
                'category': 'metal',
                'base_price': Decimal('800.00'),
                'volatility': Decimal('50.00'),
            },
        ]
        
        today = datetime.now().date()
        two_years_ago = today - timedelta(days=730)
        
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
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Actif créé: {asset.code} - {asset.label}')
                )
            else:
                self.stdout.write(f'ℹ️  Actif existant: {asset.code} - {asset.label}')
            
            # Générer 2 ans de données
            current_price = asset_info['base_price']
            count = 0
            
            for day_offset in range(730):
                date = two_years_ago + timedelta(days=day_offset)
                
                # Variation aléatoire (marche aléatoire)
                variation = Decimal(str(random.uniform(-1, 1))) * asset_info['volatility']
                current_price = current_price + variation
                
                # S'assurer que le prix reste positif
                if current_price < Decimal('0.01'):
                    current_price = asset_info['base_price']
                
                # Créer le prix
                price, price_created = Price.objects.get_or_create(
                    asset=asset,
                    date=date,
                    defaults={'price_mru': current_price}
                )
                
                if price_created:
                    count += 1
            
            self.stdout.write(
                self.style.SUCCESS(f'   📊 {count} prix ajoutés (2 ans)')
            )
        
        self.stdout.write(self.style.SUCCESS('\n✅ Initialisation complète!'))
        self.stdout.write(f'   Total actifs: {Asset.objects.count()}')
        self.stdout.write(f'   Total prix: {Price.objects.count()}')

