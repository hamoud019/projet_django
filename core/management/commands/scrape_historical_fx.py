"""
Management command: python manage.py scrape_historical_fx
Récupère l'historique complet 2 ans de l'API BCM
"""
from django.core.management.base import BaseCommand, CommandError
from datetime import datetime, timedelta
from decimal import Decimal
import requests
import logging
from core.models import Asset, Price
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Scrape l'historique 2 ans des devises depuis l'API BCM"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=730,
            help='Nombre de jours à récupérer (défaut: 730 = 2 ans)',
        )
    
    def handle(self, *args, **options):
        days = options.get('days', 730)
        
        self.stdout.write("=" * 70)
        self.stdout.write(self.style.SUCCESS("🚀 Scraping Historique BCM (2 ans)"))
        self.stdout.write("=" * 70)
        
        # Calculer les dates
        today = datetime.now().date()
        start_date = today - timedelta(days=days)
        
        self.stdout.write(f"📅 Période: {start_date} → {today} ({days} jours)")
        self.stdout.write("")
        
        # Devises à scraper
        currencies = {
            "USD": "Dollar US",
            "EUR": "Euro",
            "CNY": "Yuan Chinois",
        }
        
        total_stored = 0
        total_failed = 0
        
        for currency_code, currency_label in currencies.items():
            self.stdout.write(f"\n📌 Scraping {currency_code} ({currency_label})...")
            
            try:
                prices_data = self.fetch_historical_prices(
                    currency_code,
                    start_date,
                    today
                )
                
                if not prices_data:
                    self.stdout.write(
                        self.style.WARNING(f"⚠️  Aucune donnée pour {currency_code}")
                    )
                    total_failed += len(prices_data) if prices_data else 1
                    continue
                
                # Stocker les prix
                stored, failed = self.store_prices(currency_code, prices_data)
                
                self.stdout.write(
                    self.style.SUCCESS(f"✅ {currency_code}: {stored} prix stockés")
                )
                if failed > 0:
                    self.stdout.write(
                        self.style.WARNING(f"⚠️  {failed} prix échoués")
                    )
                
                total_stored += stored
                total_failed += failed
                
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Erreur {currency_code}: {e}")
                )
                total_failed += 1
        
        # Résumé final
        self.stdout.write("\n" + "=" * 70)
        self.stdout.write(self.style.SUCCESS("📊 RÉSUMÉ"))
        self.stdout.write("=" * 70)
        self.stdout.write(f"✅ Stockés: {total_stored}")
        self.stdout.write(f"❌ Échoués: {total_failed}")
        self.stdout.write(f"📊 Total: {total_stored + total_failed}")
        self.stdout.write("=" * 70)
    
    def fetch_historical_prices(self, currency_code, start_date, end_date):
        """
        Récupère les prix historiques depuis l'API BCM
        
        Args:
            currency_code: USD, EUR, CNY
            start_date: datetime.date
            end_date: datetime.date
            
        Returns:
            list: [{'date': date, 'taux': float}, ...]
        """
        url = "https://connect.bcm.mr/api/cours_change_reference"
        
        params = {
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "currency": currency_code,
        }
        
        logger.info(f"🔍 Requête: {url} {params}")
        
        try:
            response = requests.get(
                url,
                params=params,
                timeout=15,
                verify=False
            )
            response.raise_for_status()
            
            data = response.json()
            
            if not isinstance(data, list):
                logger.error(f"Format invalide pour {currency_code}: {data}")
                return []
            
            logger.info(f"✅ {currency_code}: {len(data)} enregistrements reçus")
            
            return data
        
        except requests.Timeout:
            logger.error(f"Timeout: {currency_code}")
            raise CommandError(f"Timeout {currency_code}")
        except requests.RequestException as e:
            logger.error(f"Erreur réseau {currency_code}: {e}")
            raise CommandError(f"Erreur réseau {currency_code}: {e}")
        except Exception as e:
            logger.error(f"Erreur {currency_code}: {e}")
            raise CommandError(f"Erreur {currency_code}: {e}")
    
    def store_prices(self, currency_code, prices_data):
        """
        Stocke les prix historiques dans PostgreSQL
        
        Args:
            currency_code: USD, EUR, CNY
            prices_data: [{'date': str, 'value': float}, ...]
            
        Returns:
            tuple: (stored_count, failed_count)
        """
        try:
            asset = Asset.objects.get(code=currency_code)
        except Asset.DoesNotExist:
            logger.error(f"Actif {currency_code} introuvable")
            return 0, len(prices_data)
        
        stored = 0
        failed = 0
        
        for item in prices_data:
            try:
                # Parser la date et le prix
                date_str = item.get('date')
                price_value = item.get('value')
                
                if not date_str or price_value is None:
                    logger.warning(f"Données incomplètes: {item}")
                    failed += 1
                    continue
                
                # Convertir la date
                try:
                    if isinstance(date_str, str):
                        price_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                    else:
                        price_date = date_str
                except ValueError:
                    logger.warning(f"Date invalide: {date_str}")
                    failed += 1
                    continue
                
                # Convertir le prix
                try:
                    price_mru = Decimal(str(price_value))
                except (ValueError, TypeError):
                    logger.warning(f"Prix invalide: {price_value}")
                    failed += 1
                    continue
                
                # Vérifier que le prix est valide
                if price_mru < Decimal("0.01"):
                    logger.warning(f"Prix trop petit: {price_mru}")
                    failed += 1
                    continue
                
                # Upsert
                price, created = Price.objects.update_or_create(
                    asset=asset,
                    date=price_date,
                    defaults={'price_mru': price_mru, 'source': 'bcm'}
                )
                
                stored += 1
                
                if stored % 50 == 0:
                    logger.debug(f"  {stored} prix traités...")
            
            except Exception as e:
                logger.error(f"Erreur stockage {currency_code}/{item}: {e}")
                failed += 1
                continue
        
        return stored, failed
