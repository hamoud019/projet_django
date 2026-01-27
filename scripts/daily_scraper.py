"""
Orchestrateur du scraping quotidien
Scrape les données et appelle le sync
"""
import logging
import sys
from datetime import datetime
from scraper.runner import ScraperRunner

logger = logging.getLogger(__name__)


class DailyScraperJob:
    """Job de scraping quotidien"""
    
    @staticmethod
    def run():
        """Exécute le job complet: scrape + sync"""
        logger.info("🚀 Démarrage du job quotidien de scraping")
        
        # Validation de la configuration
        is_valid, errors = ScraperRunner.validate_configuration()
        if not is_valid:
            logger.error(f"❌ Configuration invalide: {errors}")
            return {
                "exit_code": ScraperRunner.CONFIGURATION_ERROR,
                "errors": errors,
            }
        
        # Scraper les données
        scrape_result = ScraperRunner.scrape_all()
        
        if scrape_result["exit_code"] == ScraperRunner.SUCCESS:
            logger.info("✅ Scraping réussi")
            
            # Lancer le sync (optionnel)
            try:
                from sync.sync_prices import SyncService
                sync_result = SyncService.sync_prices_to_mongo(days_back=7)
                logger.info(f"📊 Sync: {sync_result}")
            except ImportError:
                logger.warning("⚠️ Sync non disponible (MongoDB non configuré)")
            except Exception as e:
                logger.warning(f"⚠️ Erreur sync: {e}")
        else:
            logger.warning(f"⚠️ Scraping partiel/échoué: code {scrape_result['exit_code']}")
        
        return scrape_result


if __name__ == "__main__":
    import os
    import django
    
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
    django.setup()
    
    result = DailyScraperJob.run()
    exit_code = result.get("exit_code", ScraperRunner.TOTAL_FAILURE)
    sys.exit(exit_code)
