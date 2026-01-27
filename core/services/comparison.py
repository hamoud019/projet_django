from django.db.models import Q
from ..models import Asset, Price
from datetime import timedelta
from django.utils import timezone


def compare_assets(asset_codes, days=30):
    """
    Compare les prix de plusieurs actifs sur une période
    
    Args:
        asset_codes: liste des codes d'actifs
        days: nombre de jours à comparer
    
    Returns:
        dict: données de comparaison
    """
    start_date = timezone.now().date() - timedelta(days=days)
    assets = Asset.objects.filter(code__in=asset_codes)
    
    comparison = {}
    for asset in assets:
        prices = Price.objects.filter(
            asset=asset,
            date__gte=start_date
        ).order_by('date')
        
        if prices:
            comparison[asset.code] = {
                'asset': asset,
                'prices': list(prices),
                'min': prices.order_by('price_mru').first(),
                'max': prices.order_by('-price_mru').first(),
                'avg': sum(p.price_mru for p in prices) / len(prices),
            }
    
    return comparison


def calculate_variation(current_price, previous_price):
    """Calcule la variation en pourcentage"""
    if not previous_price or previous_price == 0:
        return 0
    return ((current_price - previous_price) / previous_price) * 100
