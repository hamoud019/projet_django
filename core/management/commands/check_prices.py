from django.core.management.base import BaseCommand
from django.utils import timezone
from core.models import Price, Asset
from datetime import timedelta


class Command(BaseCommand):
    help = 'Vérifie les prix disponibles pour aujourd\'hui'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update',
            action='store_true',
            help='Scrape les données manquantes',
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Nombre de jours à vérifier',
        )

    def handle(self, *args, **options):
        today = timezone.now().date()
        days_back = options['days']
        
        self.stdout.write(self.style.SUCCESS(f"\n📊 Vérification des prix du {today}"))
        self.stdout.write("=" * 60)
        
        assets = Asset.objects.all().order_by('category', 'code')
        
        for asset in assets:
            # Prix d'aujourd'hui
            today_price = Price.objects.filter(
                asset=asset,
                date=today
            ).first()
            
            # Dernier prix disponible
            last_price = Price.objects.filter(asset=asset).order_by("-date").first()
            
            status = "✅" if today_price else "⚠️"
            
            if today_price:
                self.stdout.write(
                    f"{status} {asset.code:10} - Aujourd'hui: {today_price.price_mru} "
                    f"({today_price.date})"
                )
            else:
                if last_price:
                    days_diff = (today - last_price.date).days
                    self.stdout.write(
                        f"{status} {asset.code:10} - Dernier prix: {last_price.price_mru} "
                        f"({last_price.date}) [depuis {days_diff} jours]"
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(
                            f"❌ {asset.code:10} - Aucun prix disponible"
                        )
                    )
        
        self.stdout.write("=" * 60)
        
        # Résumé
        total_assets = Asset.objects.count()
        with_today = Price.objects.filter(date=today).values('asset').distinct().count()
        
        self.stdout.write(f"\n📈 Résumé:")
        self.stdout.write(f"   Total actifs: {total_assets}")
        self.stdout.write(
            self.style.SUCCESS(f"   Avec prix aujourd'hui: {with_today}")
            if with_today == total_assets
            else self.style.WARNING(f"   Avec prix aujourd'hui: {with_today}/{total_assets}")
        )
        
        if options['update']:
            self.stdout.write("\n🔄 Tentative de scraping...")
            try:
                from scripts.daily_scraper import DailyScraperJob
                result = DailyScraperJob.run()
                self.stdout.write(self.style.SUCCESS(f"   Scraping: {result}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"   Erreur: {e}"))
