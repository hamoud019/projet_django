"""
Fetcher pour les cryptomonnaies (Bitcoin)
"""
import logging
from decimal import Decimal
from datetime import datetime
import random

logger = logging.getLogger(__name__)


class CryptoFetcher:
    """Récupère les prix des cryptomonnaies"""
    
    BASE_PRICES = {
        "BTC": Decimal("45000.00"),  # Prix base en USD, convertir en MRU
    }
    
    @staticmethod
    def fetch_bitcoin_price():
        """Récupère le prix du Bitcoin (simulation)"""
        try:
            # Simulation: variation aléatoire
            base = Decimal("45000.00")  # USD
            variation = Decimal(str(random.uniform(-0.05, 0.05)))  # ±5%
            price_usd = base * (Decimal("1") + variation)
            
            # Convertir en MRU (1 USD = 600 MRU approximativement)
            mru_rate = Decimal("600.00")
            price_mru = price_usd * mru_rate
            
            if price_mru < Decimal("0.01"):
                logger.warning(f"Prix invalide Bitcoin: {price_mru}")
                return None
            
            logger.info(f"Bitcoin: {price_usd.quantize(Decimal('0.01'))} USD = {price_mru.quantize(Decimal('0.01'))} MRU")
            
            return {
                "asset_code": "BTC",
                "price_mru": price_mru.quantize(Decimal("0.01")),
                "source": "crypto_api",
                "timestamp": datetime.now(),
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération Bitcoin: {e}")
            return None
    
    @staticmethod
    def get_all_prices():
        """Récupère tous les prix crypto"""
        results = []
        
        btc_price = CryptoFetcher.fetch_bitcoin_price()
        if btc_price:
            results.append(btc_price)
            logger.info(f"✅ BTC: {btc_price['price_mru']} MRU")
        else:
            logger.warning("⚠️ BTC: Récupération échouée")
        
        return results
