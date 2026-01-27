"""
Fetcher pour les matières premières (Métaux)
"""
import logging
from decimal import Decimal
from datetime import datetime
import random

logger = logging.getLogger(__name__)


class MetalsFetcher:
    """Récupère les prix des métaux"""
    
    # Taux de base pour conversion en MRU
    RATES = {
        "GOLD": Decimal("2100.00"),    # 1 oz = 2100 MRU
        "IRON": Decimal("150.00"),     # 1 tonne = 150 MRU
        "COPPER": Decimal("800.00"),   # 1 tonne = 800 MRU
    }
    
    @staticmethod
    def fetch_metal_price(code: str):
        """Récupère le prix d'un métal (simulation)"""
        try:
            if code not in MetalsFetcher.RATES:
                raise ValueError(f"Métal inconnu: {code}")
            
            base_price = MetalsFetcher.RATES[code]
            
            # Variation aléatoire
            if code == "GOLD":
                variation = Decimal(str(random.uniform(-0.03, 0.03)))  # ±3%
            else:
                variation = Decimal(str(random.uniform(-0.02, 0.02)))  # ±2%
            
            price_mru = base_price * (Decimal("1") + variation)
            
            if price_mru < Decimal("0.01"):
                logger.warning(f"Prix invalide {code}: {price_mru}")
                return None
            
            logger.info(f"{code}: {price_mru.quantize(Decimal('0.01'))} MRU")
            
            return {
                "asset_code": code,
                "price_mru": price_mru.quantize(Decimal("0.01")),
                "source": "metals_api",
                "timestamp": datetime.now(),
            }
            
        except Exception as e:
            logger.error(f"Erreur récupération {code}: {e}")
            return None
    
    @staticmethod
    def get_all_prices():
        """Récupère tous les prix des métaux"""
        results = []
        
        for code in MetalsFetcher.RATES.keys():
            price_data = MetalsFetcher.fetch_metal_price(code)
            if price_data:
                results.append(price_data)
                logger.info(f"✅ {code}: {price_data['price_mru']} MRU")
            else:
                logger.warning(f"⚠️ {code}: Récupération échouée")
        
        return results
