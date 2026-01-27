"""
Orchestrateur du scraping - Gestion des retries et des erreurs
"""
import logging
import time
from datetime import datetime
from decimal import Decimal

from scraper.fetchers.crypto import CryptoFetcher
from scraper.fetchers.fx import FXFetcher
from scraper.fetchers.metals import MetalsFetcher
from scraper.store import DataStore

logger = logging.getLogger(__name__)


class ScraperRunner:
    """Orchestre le scraping avec retries et gestion d'erreurs"""
    
    MAX_RETRIES = 3
    RETRY_DELAY = 2  # secondes
    BACKOFF_MULTIPLIER = 2
    
    # Codes de retour
    SUCCESS = 0
    PARTIAL_FAILURE = 1
    TOTAL_FAILURE = 2
    CONFIGURATION_ERROR = 3
    
    @staticmethod
    def _retry_fetch(fetcher_func, max_retries=MAX_RETRIES):
        """
        Exécute une fonction fetch avec retries et backoff exponentiel
        
        Args:
            fetcher_func: Fonction à appeler
            max_retries: Nombre maximum de tentatives
            
        Returns:
            list: Résultats du fetch
        """
        delay = ScraperRunner.RETRY_DELAY
        last_error = None
        
        for attempt in range(1, max_retries + 1):
            try:
                logger.info(f"🔄 Tentative {attempt}/{max_retries}")
                result = fetcher_func()
                
                if result:
                    logger.info(f"✅ Succès à la tentative {attempt}")
                    return result
                else:
                    last_error = "Aucun résultat retourné"
                    logger.warning(f"⚠️ Tentative {attempt}: Aucun résultat")
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"⚠️ Tentative {attempt} échouée: {e}")
                
                if attempt < max_retries:
                    logger.info(f"⏳ Attente {delay}s avant nouvelle tentative...")
                    time.sleep(delay)
                    delay *= ScraperRunner.BACKOFF_MULTIPLIER
        
        logger.error(
            f"❌ Échec après {max_retries} tentatives. "
            f"Dernière erreur: {last_error}"
        )
        return []
    
    @staticmethod
    def scrape_all():
        """
        Scrape tous les actifs (devises, crypto, matières premières)
        
        Returns:
            dict: {
                "exit_code": int,
                "timestamp": str,
                "fetched": int,
                "stored": int,
                "failed": int,
                "details": dict
            }
        """
        logger.info("=" * 60)
        logger.info("🚀 Démarrage du scraper quotidien")
        logger.info(f"⏰ Timestamp: {datetime.now().isoformat()}")
        logger.info("=" * 60)
        
        results = {
            "timestamp": datetime.now().isoformat(),
            "fetchers": {},
            "total_fetched": 0,
            "total_stored": 0,
            "total_failed": 0
        }
        
        all_prices = []
        exit_code = ScraperRunner.SUCCESS
        
        # Scraper les devises (Forex)
        logger.info("\n📌 Scraping Forex...")
        fx_prices = ScraperRunner._retry_fetch(FXFetcher.get_all_prices)
        results["fetchers"]["forex"] = {
            "count": len(fx_prices),
            "status": "success" if fx_prices else "failed"
        }
        all_prices.extend(fx_prices)
        results["total_fetched"] += len(fx_prices)
        
        if not fx_prices:
            exit_code = ScraperRunner.PARTIAL_FAILURE
            logger.warning("⚠️ Forex: Aucune donnée récupérée")
        
        # Scraper les cryptomonnaies
        logger.info("\n📌 Scraping Crypto...")
        crypto_prices = ScraperRunner._retry_fetch(CryptoFetcher.get_all_prices)
        results["fetchers"]["crypto"] = {
            "count": len(crypto_prices),
            "status": "success" if crypto_prices else "failed"
        }
        all_prices.extend(crypto_prices)
        results["total_fetched"] += len(crypto_prices)
        
        if not crypto_prices:
            exit_code = ScraperRunner.PARTIAL_FAILURE
            logger.warning("⚠️ Crypto: Aucune donnée récupérée")
        
        # Scraper les matières premières
        logger.info("\n📌 Scraping Matières premières...")
        metals_prices = ScraperRunner._retry_fetch(MetalsFetcher.get_all_prices)
        results["fetchers"]["metals"] = {
            "count": len(metals_prices),
            "status": "success" if metals_prices else "failed"
        }
        all_prices.extend(metals_prices)
        results["total_fetched"] += len(metals_prices)
        
        if not metals_prices:
            exit_code = ScraperRunner.PARTIAL_FAILURE
            logger.warning("⚠️ Matières premières: Aucune donnée récupérée")
        
        # Vérifier qu'on a au moins quelque chose
        if not all_prices:
            logger.error("❌ Aucune donnée récupérée de toutes les sources!")
            results["exit_code"] = ScraperRunner.TOTAL_FAILURE
            return results
        
        # Stocker les prix (source: bcm pour forex, sim pour les autres)
        logger.info(f"\n📝 Stockage des {len(all_prices)} prix...")
        
        # Séparer forex (bcm) et autres (sim)
        fx_prices_all = list(fx_prices) if fx_prices else []
        other_prices_all = list(crypto_prices) + list(metals_prices) if (crypto_prices or metals_prices) else []
        
        # Stocker forex avec source='bcm'
        if fx_prices_all:
            store_result_fx = DataStore.store_prices_batch(fx_prices_all, source="bcm")
            results["total_stored"] += store_result_fx["stored"]
            results["total_failed"] += store_result_fx["failed"]
        
        # Stocker autres avec source='sim'
        if other_prices_all:
            store_result_other = DataStore.store_prices_batch(other_prices_all, source="sim")
            results["total_stored"] += store_result_other["stored"]
            results["total_failed"] += store_result_other["failed"]
        
        # Pour compatibilité, création du résumé
        store_result = {
            "stored": results["total_stored"],
            "failed": results["total_failed"]
        }
        
        results["total_stored"] = store_result["stored"]
        results["total_failed"] = store_result["failed"]
        results["store_result"] = store_result
        
        # Déterminer le code de sortie final
        if store_result["failed"] > 0:
            exit_code = ScraperRunner.PARTIAL_FAILURE
        
        # Résumé final
        logger.info("\n" + "=" * 60)
        logger.info("📊 RÉSUMÉ DU SCRAPING")
        logger.info("=" * 60)
        logger.info(f"✅ Données récupérées: {results['total_fetched']}")
        logger.info(f"✅ Données stockées: {results['total_stored']}")
        logger.info(f"❌ Données échouées: {results['total_failed']}")
        logger.info(f"📌 Code de sortie: {exit_code}")
        logger.info("=" * 60)
        
        results["exit_code"] = exit_code
        return results
    
    @staticmethod
    def validate_configuration():
        """
        Valide la configuration du scraper
        
        Returns:
            tuple: (success: bool, errors: list)
        """
        errors = []
        
        try:
            from core.models import Asset
            
            required_assets = ["USD", "EUR", "CNY", "BTC", "GOLD", "IRON", "COPPER"]
            existing_assets = set(Asset.objects.values_list("code", flat=True))
            
            missing = set(required_assets) - existing_assets
            if missing:
                errors.append(f"Actifs manquants: {missing}")
        
        except Exception as e:
            errors.append(f"Erreur vérification actifs: {e}")
        
        return len(errors) == 0, errors
