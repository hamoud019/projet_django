"""
Service de synchronisation PostgreSQL ↔ MongoDB
"""
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from decimal import Decimal
import os

logger = logging.getLogger(__name__)


class SyncService:
    """Synchronise les données entre PostgreSQL et MongoDB"""
    
    @staticmethod
    def get_mongo_client():
        """Initialise la connexion MongoDB"""
        try:
            from pymongo import MongoClient
            
            mongo_url = os.environ.get(
                'MONGO_URL',
                'mongodb://mongo:27017'
            )
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            # Tester la connexion
            client.admin.command('ping')
            logger.info(f"✅ Connexion MongoDB établie: {mongo_url}")
            return client
        except Exception as e:
            logger.warning(f"⚠️ MongoDB non disponible: {e}")
            return None
    
    @staticmethod
    def sync_prices_to_mongo(days_back=7):
        """
        Synchronise les prix de PostgreSQL vers MongoDB
        
        Args:
            days_back: Nombre de jours à synchroniser (glissant)
        
        Returns:
            dict: Résultats de la synchronisation
        """
        from core.models import Price, Asset
        
        logger.info("=" * 60)
        logger.info("📊 Démarrage synchronisation PostgreSQL → MongoDB")
        logger.info(f"⏰ Timestamp: {datetime.now().isoformat()}")
        logger.info("=" * 60)
        
        client = SyncService.get_mongo_client()
        if not client:
            logger.error("❌ MongoDB non accessible")
            return {
                "success": False,
                "error": "MongoDB non accessible",
                "synced": 0,
                "failed": 0,
            }
        
        try:
            db = client['asset_prices']
            collection = db['prices']
            
            # Ajouter un index unique pour éviter les doublons
            collection.create_index([("asset_code", 1), ("date", 1)], unique=True)
            
            # Récupérer les prix des N derniers jours
            cutoff_date = timezone.now().date() - timedelta(days=days_back)
            prices = Price.objects.filter(
                date__gte=cutoff_date
            ).select_related('asset').order_by('-date')
            
            synced = 0
            failed = 0
            
            logger.info(f"📥 Synchronisation de {prices.count()} prix depuis {cutoff_date}...")
            
            for price in prices:
                try:
                    document = {
                        "asset_code": price.asset.code,
                        "asset_label": price.asset.label,
                        "asset_category": price.asset.category,
                        "date": price.date.isoformat(),
                        "price_mru": float(price.price_mru),
                        "synced_at": datetime.utcnow(),
                    }
                    
                    # Upsert: mettre à jour si existe, créer sinon
                    result = collection.update_one(
                        {"asset_code": price.asset.code, "date": price.date.isoformat()},
                        {"$set": document},
                        upsert=True
                    )
                    
                    synced += 1
                    
                except Exception as e:
                    logger.error(f"❌ Erreur sync {price.asset.code}/{price.date}: {e}")
                    failed += 1
                    continue
            
            # Récupérer les stats
            total_in_mongo = collection.count_documents({})
            
            logger.info("\n" + "=" * 60)
            logger.info("📊 RÉSUMÉ SYNCHRONISATION")
            logger.info("=" * 60)
            logger.info(f"✅ Documents synchronisés: {synced}")
            logger.info(f"❌ Documents échoués: {failed}")
            logger.info(f"📦 Total dans MongoDB: {total_in_mongo}")
            logger.info("=" * 60)
            
            return {
                "success": True,
                "synced": synced,
                "failed": failed,
                "total_in_mongo": total_in_mongo,
                "timestamp": datetime.now().isoformat(),
            }
        
        except Exception as e:
            logger.error(f"❌ Erreur synchronisation: {e}")
            return {
                "success": False,
                "error": str(e),
                "synced": synced,
                "failed": failed,
            }
        
        finally:
            client.close()
            logger.info("🔌 Connexion MongoDB fermée")
    
    @staticmethod
    def verify_consistency():
        """
        Vérifie la cohérence entre PostgreSQL et MongoDB
        
        Returns:
            dict: Résultats de vérification
        """
        from core.models import Price
        
        logger.info("🔍 Vérification de la cohérence...")
        
        client = SyncService.get_mongo_client()
        if not client:
            logger.warning("⚠️ Impossible vérifier MongoDB")
            return {"success": False}
        
        try:
            db = client['asset_prices']
            collection = db['prices']
            
            pg_count = Price.objects.count()
            mongo_count = collection.count_documents({})
            
            logger.info(f"📊 PostgreSQL: {pg_count} prix")
            logger.info(f"📊 MongoDB: {mongo_count} prix")
            
            if pg_count == mongo_count:
                logger.info("✅ Cohérence OK")
                return {
                    "success": True,
                    "pg_count": pg_count,
                    "mongo_count": mongo_count,
                    "consistent": True,
                }
            else:
                logger.warning(f"⚠️ Incohérence: {pg_count} vs {mongo_count}")
                return {
                    "success": True,
                    "pg_count": pg_count,
                    "mongo_count": mongo_count,
                    "consistent": False,
                }
        
        except Exception as e:
            logger.error(f"❌ Erreur vérification: {e}")
            return {"success": False, "error": str(e)}
        
        finally:
            client.close()
