"""
Management command: python manage.py sync_to_mongo
Synchronise les prix de PostgreSQL vers MongoDB
"""
from django.core.management.base import BaseCommand, CommandError
from sync.sync_prices import SyncService


class Command(BaseCommand):
    help = "Synchronise les prix de PostgreSQL vers MongoDB"
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Nombre de jours à synchroniser (défaut: 7)',
        )
        parser.add_argument(
            '--verify',
            action='store_true',
            help='Vérifier la cohérence après sync',
        )
    
    def handle(self, *args, **options):
        days = options.get('days', 7)
        verify = options.get('verify', False)
        
        self.stdout.write("=" * 60)
        self.stdout.write(self.style.SUCCESS("📊 Sync PostgreSQL → MongoDB"))
        self.stdout.write("=" * 60)
        
        # Synchroniser
        result = SyncService.sync_prices_to_mongo(days_back=days)
        
        if not result['success']:
            self.stdout.write(
                self.style.ERROR(f"❌ Erreur sync: {result.get('error')}")
            )
            raise CommandError("Sync échouée")
        
        # Afficher le résumé
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write(self.style.SUCCESS("📊 RÉSUMÉ SYNC"))
        self.stdout.write("=" * 60)
        self.stdout.write(f"✅ Synchronisés: {result['synced']}")
        self.stdout.write(f"❌ Échoués: {result['failed']}")
        self.stdout.write(f"📦 Total MongoDB: {result.get('total_in_mongo', 0)}")
        self.stdout.write("=" * 60)
        
        # Vérification optionnelle
        if verify:
            self.stdout.write("\n🔍 Vérification de la cohérence...")
            check_result = SyncService.verify_consistency()
            if check_result['success']:
                if check_result.get('consistent'):
                    self.stdout.write(self.style.SUCCESS("✅ Cohérence OK"))
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"⚠️ Incohérence: PG={check_result['pg_count']}, "
                            f"Mongo={check_result['mongo_count']}"
                        )
                    )
            else:
                self.stdout.write(
                    self.style.ERROR("❌ Erreur vérification")
                )
