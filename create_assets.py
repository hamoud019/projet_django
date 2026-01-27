"""
Vérifier et créer les actifs manquants
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

from core.models import Asset

print("=" * 80)
print("📋 VÉRIFICATION DES ACTIFS")
print("=" * 80)

# Actifs requis
required_assets = [
    {'code': 'USD', 'label': 'Dollar US', 'category': 'fx'},
    {'code': 'EUR', 'label': 'Euro', 'category': 'fx'},
    {'code': 'CNY', 'label': 'Yuan Chinois', 'category': 'fx'},
    {'code': 'BTC', 'label': 'Bitcoin', 'category': 'crypto'},
    {'code': 'GOLD', 'label': 'Or', 'category': 'metal'},
    {'code': 'IRON', 'label': 'Fer', 'category': 'metal'},
    {'code': 'COPPER', 'label': 'Cuivre', 'category': 'metal'},
]

print("\nActifs existants:")
for asset in Asset.objects.all():
    print(f"  ✅ {asset.code}: {asset.label} ({asset.category})")

print("\nCréation des actifs manquants:")
created_count = 0

for asset_data in required_assets:
    asset, created = Asset.objects.get_or_create(
        code=asset_data['code'],
        defaults={
            'label': asset_data['label'],
            'category': asset_data['category']
        }
    )
    
    if created:
        print(f"  ✅ Créé: {asset.code} - {asset.label}")
        created_count += 1
    else:
        print(f"  ℹ️  Existant: {asset.code}")

print(f"\n{'='*80}")
print(f"✅ {created_count} actifs créés")
print(f"📊 Total: {Asset.objects.count()} actifs en base")
print(f"{'='*80}")
