"""
Management command: python manage.py sync_prices_to_mongo
Synchronise les prix PostgreSQL → MongoDB toutes les 6h ou 24h
"""
import logging
from django.core.management.base import BaseCommand
from sync.sync_prices import SyncService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Synchronise les prix de PostgreSQL vers MongoDB"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Nombre de jours à synchroniser en mode glissant (défaut: 7)',
        )
        parser.add_argument(
            '--full',
            action='store_true',
            help='Synchroniser toutes les données (pas de fenêtre glissante)',
        )
        parser.add_argument(
            '--verify',
            action='store_true',
            help='Vérifier la cohérence après la sync',
        )
    
    def handle(self, *args, **options):
        days = options.get('days', 7)
        full_sync = options.get('full', False)
        verify = options.get('verify', False)
        
        self.stdout.write(self.style.SUCCESS("=" * 70))
        self.stdout.write(self.style.SUCCESS("🔄 SYNCHRONISATION PostgreSQL → MongoDB"))
        self.stdout.write(self.style.SUCCESS("=" * 70))
        
        if full_sync:
            self.stdout.write(self.style.WARNING(f"⚠️  Mode FULL SYNC (toutes les données)"))
            days = 99999  # Très grand nombre de jours
        else:
            self.stdout.write(f"📅 Fenêtre glissante: {days} jours")
        
        # Exécuter la synchronisation
        result = SyncService.sync_prices_to_mongo(days_back=days)
        
        # Afficher les résultats
        if result['success']:
            self.stdout.write(
                self.style.SUCCESS(f"✅ Synchronisation réussie")
            )
            self.stdout.write(f"   Synchronisés: {result['synced']}")
            self.stdout.write(f"   Échoués: {result['failed']}")
            self.stdout.write(f"   Total MongoDB: {result.get('total_in_mongo', 'N/A')}")
        else:
            self.stdout.write(
                self.style.ERROR(f"❌ Erreur: {result.get('error', 'Erreur inconnue')}")
            )
        
        # Vérifier la cohérence si demandé
        if verify:
            self.stdout.write("\n" + self.style.WARNING("🔍 Vérification cohérence..."))
            consistency = SyncService.verify_consistency()
            
            if consistency['success']:
                pg = consistency.get('pg_count', 'N/A')
                mongo = consistency.get('mongo_count', 'N/A')
                is_consistent = consistency.get('consistent', False)
                
                self.stdout.write(f"   PostgreSQL: {pg} prix")
                self.stdout.write(f"   MongoDB: {mongo} prix")
                
                if is_consistent:
                    self.stdout.write(self.style.SUCCESS("   ✅ Cohérence OK"))
                else:
                    self.stdout.write(self.style.WARNING("   ⚠️  Incohérence détectée"))
            else:
                self.stdout.write(
                    self.style.ERROR(f"   ❌ Erreur vérification")
                )
        
        self.stdout.write(self.style.SUCCESS("=" * 70))
