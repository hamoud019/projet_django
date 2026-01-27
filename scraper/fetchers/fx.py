"""
Fetcher pour les devises (Forex) - API Banque Centrale de Mauritanie
"""
import logging
import requests
from decimal import Decimal
from datetime import datetime, timedelta
import urllib3

# Désactiver l'avertissement SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class FXFetcher:
    """Récupère les taux de change depuis la Banque Centrale de Mauritanie"""
    
    BASE_URL = "https://connect.bcm.mr/api/cours_change_reference"
    TIMEOUT = 10
    
    # Devises supportées
    CURRENCIES = {
        "USD": "Dollar US",
        "EUR": "Euro",
        "CNY": "Yuan Chinois",
    }
    
    @staticmethod
    def fetch_rate(currency_code: str):
        """
        Récupère le taux de change pour une devise
        
        Args:
            currency_code: USD, EUR, ou CNY
            
        Returns:
            dict avec asset_code, price_mru, source, timestamp
        """
        if currency_code not in FXFetcher.CURRENCIES:
            logger.error(f"❌ Devise inconnue: {currency_code}")
            return None
        
        try:
            # Paramètres de la requête
            today = datetime.now().date()
            start_date = (today - timedelta(days=30)).isoformat()
            end_date = today.isoformat()
            
            params = {
                "from": start_date,
                "to": end_date,
                "currency": currency_code,
            }
            
            logger.debug(f"🔍 Requête: {FXFetcher.BASE_URL} {params}")
            response = requests.get(
                FXFetcher.BASE_URL,
                params=params,
                timeout=FXFetcher.TIMEOUT,
                verify=False  # Désactiver vérification SSL pour BCM
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Valider la structure
            if not isinstance(data, list) or len(data) == 0:
                logger.warning(f"⚠️ Réponse vide pour {currency_code}")
                return None
            
            # Prendre le dernier taux (le plus récent)
            latest = data[-1]
            
            # Le champ s'appelle "value" dans l'API BCM
            if "value" not in latest:
                logger.error(f"❌ Format invalide pour {currency_code}: {latest}")
                return None
            
            # Le taux est en MRU (1 USD = X MRU, etc.)
            price_mru = Decimal(str(latest["value"]))
            
            if price_mru < Decimal("0.01"):
                logger.warning(f"⚠️ Prix invalide {currency_code}: {price_mru}")
                return None
            
            logger.info(f"✅ {currency_code}: 1 {currency_code} = {price_mru} MRU")
            
            return {
                "asset_code": currency_code,
                "price_mru": price_mru.quantize(Decimal("0.01")),
                "source": "bcm_mauritanie",
                "timestamp": datetime.now(),
            }
            
        except requests.Timeout:
            logger.error(f"❌ Timeout {currency_code} (BCM)")
            return None
        except requests.RequestException as e:
            logger.error(f"❌ Erreur réseau {currency_code}: {e}")
            return None
        except (ValueError, KeyError) as e:
            logger.error(f"❌ Erreur parsing {currency_code}: {e}")
            return None
        except Exception as e:
            logger.error(f"❌ Erreur inattendue {currency_code}: {e}")
            return None
    
    @staticmethod
    def get_all_prices():
        """Récupère tous les taux de change"""
        results = []
        
        for currency_code in FXFetcher.CURRENCIES.keys():
            price_data = FXFetcher.fetch_rate(currency_code)
            
            if price_data:
                results.append(price_data)
                logger.info(f"✅ {currency_code}: {price_data['price_mru']} MRU")
            else:
                logger.warning(f"⚠️ {currency_code}: Récupération échouée")
        
        return results
