"""
Module de stockage des données - Gestion de l'upsert dans PostgreSQL
"""
import logging
from decimal import Decimal
from datetime import datetime
from django.db import connection
from django.db.models import Q
from core.models import Asset, Price

logger = logging.getLogger(__name__)


class DataStore:
    """Stockage des données avec upsert et gestion d'erreurs"""
    
    @staticmethod
    def store_price(asset_code, price_mru, date=None, source="api"):
        """
        Stocke un prix avec upsert (insert or update)
        
        Args:
            asset_code: Code de l'actif
            price_mru: Prix en MRU
            date: Date (par défaut aujourd'hui)
            source: Source de données (bcm, api, sim, init)
            
        Returns:
            dict: {"success": bool, "id": int, "created": bool}
        """
        if date is None:
            date = datetime.now().date()
        
        try:
            # Récupérer ou créer l'actif
            asset = Asset.objects.get(code=asset_code)
            
            # Convertir le prix en Decimal si nécessaire
            if not isinstance(price_mru, Decimal):
                price_mru = Decimal(str(price_mru))
            
            # Upsert: update_or_create
            price, created = Price.objects.update_or_create(
                asset=asset,
                date=date,
                defaults={'price_mru': price_mru, 'source': source}
            )
            
            action = "créé" if created else "mis à jour"
            logger.info(f"✅ Prix {action}: {asset_code} = {price_mru} MRU ({date})")
            
            return {
                "success": True,
                "id": price.id,
                "created": created,
                "asset_code": asset_code,
                "price_mru": float(price_mru),
                "date": str(date)
            }
            
        except Asset.DoesNotExist:
            logger.error(f"❌ Actif introuvable: {asset_code}")
            return {
                "success": False,
                "error": f"Asset not found: {asset_code}"
            }
        except Exception as e:
            logger.error(f"❌ Erreur stockage {asset_code}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @staticmethod
    def store_prices_batch(prices_list, date=None, source="api"):
        """
        Stocke plusieurs prix en batch
        
        Args:
            prices_list: Liste de {"asset_code": str, "price_mru": Decimal, ...}
            date: Date commune (par défaut aujourd'hui)
            source: Source de données (bcm, api, sim, init)
            
        Returns:
            dict: {"stored": int, "failed": int}
        """
        if date is None:
            from django.utils import timezone
            date = timezone.now().date()
        
        stored_count = 0
        failed_count = 0
        
        for price_data in prices_list:
            # Accepter "code" ou "asset_code"
            code = price_data.get("asset_code") or price_data.get("code")
            price_mru = price_data.get("price_mru")
            
            if not code or price_mru is None:
                logger.warning(f"⚠️ Données incomplètes: {price_data}")
                failed_count += 1
                continue
            
            result = DataStore.store_price(code, price_mru, date, source)
            
            if result["success"]:
                stored_count += 1
            else:
                failed_count += 1
        
        summary = {
            "stored": stored_count,
            "failed": failed_count,
            "total": len(prices_list),
        }
        
        logger.info(
            f"📊 Batch résumé: {stored_count} stockés, {failed_count} échoués "
            f"({len(prices_list)} total)"
        )
        
        return summary
    
    @staticmethod
    def get_latest_prices():
        """Récupère les derniers prix de tous les actifs"""
        try:
            prices = Price.objects.filter(
                asset__in=Asset.objects.all()
            ).distinct('asset').order_by('asset', '-date')
            
            results = []
            for p in prices:
                results.append({
                    "code": p.asset.code,
                    "label": p.asset.label,
                    "price_mru": float(p.price_mru),
                    "date": str(p.date)
                })
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Erreur récupération prix: {e}")
            return []
