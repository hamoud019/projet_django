"""
Vérifier les données Bitcoin
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from core.models import Asset, Price
from django.db.models import Count, Min, Max, Avg

print("=" * 80)
print("📊 VÉRIFICATION BITCOIN")
print("=" * 80)

btc = Asset.objects.get(code='BTC')
print(f"\n✅ Asset BTC trouvé: {btc.label}")

btc_prices = Price.objects.filter(asset=btc)
count = btc_prices.count()

print(f"\n📈 Données Bitcoin:")
print(f"  Nombre de prix: {count}")

if count > 0:
    stats = btc_prices.aggregate(
        min_price=Min('price_mru'),
        max_price=Max('price_mru'),
        avg_price=Avg('price_mru'),
        min_date=Min('date'),
        max_date=Max('date')
    )
    
    print(f"  Plage: {stats['min_date']} → {stats['max_date']}")
    print(f"  Prix (MRU):")
    print(f"    Min: {stats['min_price']:,.2f}")
    print(f"    Max: {stats['max_price']:,.2f}")
    print(f"    Moy: {stats['avg_price']:,.2f}")
    
    # Vérifier les sources
    sources = btc_prices.values('source').annotate(count=Count('source'))
    print(f"\n  Sources:")
    for s in sources:
        print(f"    {s['source']}: {s['count']} prix")

print("\n" + "=" * 80)

# Vérifier d'autres actifs
print("\n📊 RÉSUMÉ DE TOUS LES ACTIFS:")
print("=" * 80)

for asset in Asset.objects.all():
    prices = Price.objects.filter(asset=asset)
    count = prices.count()
    
    if count > 0:
        stats = prices.aggregate(
            min_price=Min('price_mru'),
            max_price=Max('price_mru')
        )
        print(f"  {asset.code:6} ({asset.category:6}) → {count:4} prix [{stats['min_price']:12.2f} - {stats['max_price']:12.2f}]")
    else:
        print(f"  {asset.code:6} ({asset.category:6}) → 0 prix")

total_prices = Price.objects.count()
print(f"\n💾 TOTAL: {total_prices} prix en base")
print("=" * 80)
