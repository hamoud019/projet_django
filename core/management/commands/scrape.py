"""
Commande Django pour exécuter le scraper quotidien
Usage: python manage.py scrape
"""
from django.core.management.base import BaseCommand, CommandError
from scraper.runner import ScraperRunner
import logging

# Configurer les logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Scrape les données de prix des actifs et met à jour la base de données'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--validate',
            action='store_true',
            help='Valide la configuration sans scraper'
        )
    
    def handle(self, *args, **options):
        """Exécute la commande scrape"""
        
        self.stdout.write(self.style.SUCCESS("🔍 Scraper Quotidien\n"))
        
        # Valider la configuration
        self.stdout.write("Validation de la configuration...")
        valid, errors = ScraperRunner.validate_configuration()
        
        if not valid:
            self.stdout.write(self.style.ERROR("\n❌ Erreurs de configuration:"))
            for error in errors:
                self.stdout.write(self.style.ERROR(f"  - {error}"))
            raise CommandError("Configuration invalide")
        
        self.stdout.write(self.style.SUCCESS("✅ Configuration valide\n"))
        
        if options['validate']:
            self.stdout.write(self.style.SUCCESS("Mode validation uniquement"))
            return
        
        # Exécuter le scraper
        result = ScraperRunner.scrape_all()
        
        # Afficher les résultats
        exit_code = result.get("exit_code", ScraperRunner.TOTAL_FAILURE)
        
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("📊 RÉSULTATS")
        self.stdout.write("=" * 60)
        self.stdout.write(f"Timestamp: {result['timestamp']}")
        self.stdout.write(f"Données récupérées: {result['total_fetched']}")
        self.stdout.write(f"Données stockées: {result['total_stored']}")
        self.stdout.write(f"Données échouées: {result['total_failed']}")
        self.stdout.write("=" * 60 + "\n")
        
        # Afficher les détails par fetcher
        if "fetchers" in result:
            self.stdout.write("Détails par source:")
            for fetcher_name, fetcher_result in result["fetchers"].items():
                status = self.style.SUCCESS("✅") if fetcher_result["status"] == "success" else self.style.ERROR("❌")
                self.stdout.write(
                    f"  {status} {fetcher_name}: {fetcher_result['count']} prix"
                )
        
        # Code de sortie
        if exit_code == ScraperRunner.SUCCESS:
            self.stdout.write(self.style.SUCCESS("\n✅ Scraping réussi (code 0)"))
        elif exit_code == ScraperRunner.PARTIAL_FAILURE:
            self.stdout.write(self.style.WARNING("\n⚠️ Scraping partiellement réussi (code 1)"))
        elif exit_code == ScraperRunner.TOTAL_FAILURE:
            self.stdout.write(self.style.ERROR("\n❌ Scraping complètement échoué (code 2)"))
        
        # Retourner le code approprié
        if exit_code != ScraperRunner.SUCCESS:
            raise CommandError(f"Scraper failed with exit code {exit_code}")
