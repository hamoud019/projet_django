"""
Management command: python manage.py scrape_prices
Scrape les prix quotidiens et les stocke dans PostgreSQL
"""
from django.core.management.base import BaseCommand, CommandError
from scraper.runner import ScraperRunner
import sys


class Command(BaseCommand):
    help = "Scrape les prix des actifs depuis les sources externes"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--sync',
            action='store_true',
            help='Synchroniser aussi avec MongoDB après le scraping',
        )
    
    def handle(self, *args, **options):
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("🚀 Scraper les prix"))
        self.stdout.write("=" * 60)
        
        # Valider la configuration
        is_valid, errors = ScraperRunner.validate_configuration()
        if not is_valid:
            self.stdout.write(
                self.style.ERROR(f"❌ Configuration invalide: {errors}")
            )
            raise CommandError("Configuration invalide")
        
        # Scraper
        result = ScraperRunner.scrape_all()
        exit_code = result.get("exit_code")
        
        # Afficher le résumé
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📊 RÉSUMÉ"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"✅ Récupérés: {result.get('total_fetched', 0)}")
        self.stdout.write(f"✅ Stockés: {result.get('total_stored', 0)}")
        self.stdout.write(f"❌ Échoués: {result.get('total_failed', 0)}")
        self.stdout.write(f"📌 Code sortie: {exit_code}")
        self.stdout.write("=" * 60)
        
        # Sync optionnel
        if options.get('sync'):
            try:
                from sync.sync_prices import SyncService
                self.stdout.write("\n🔄 Synchronisation avec MongoDB...")
                sync_result = SyncService.sync_prices_to_mongo()
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Sync: {sync_result['synced']} documents")
                )
            except ImportError:
                self.stdout.write(
                    self.style.WARNING("⚠️ MongoDB non disponible")
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"❌ Erreur sync: {e}")
                )
        
        # Code de sortie
        if exit_code != ScraperRunner.SUCCESS:
            raise CommandError(f"Scraper échoué avec code {exit_code}")
