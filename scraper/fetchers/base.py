"""
Base fetcher avec gestion d'erreurs commune
"""
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


class BaseFetcher(ABC):
    """Classe de base pour tous les fetchers"""
    
    TIMEOUT = 10
    ASSET_CODES = []  # À définir dans les sous-classes
    
    @abstractmethod
    def fetch_price(self, asset_code: str) -> dict:
        """
        Récupère le prix d'un actif
        
        Returns:
            dict: {
                "asset_code": str,
                "price_mru": Decimal,
                "source": str,
                "timestamp": datetime
            }
        """
        pass
    
    @classmethod
    def get_all_prices(cls):
        """
        Récupère tous les prix pour ce fetcher
        
        Returns:
            list[dict]: Liste des prix
        """
        fetcher = cls()
        prices = []
        
        for asset_code in cls.ASSET_CODES:
            try:
                price_data = fetcher.fetch_price(asset_code)
                if price_data:
                    prices.append(price_data)
                    logger.debug(f"✅ {asset_code}: {price_data['price_mru']} MRU")
            except Exception as e:
                logger.error(f"❌ Erreur {asset_code}: {e}")
                continue
        
        return prices
    
    @staticmethod
    def validate_price(price: Decimal, min_value=Decimal("0.01")) -> bool:
        """Valide qu'un prix est cohérent"""
        try:
            if price < min_value:
                return False
            return True
        except:
            return False
