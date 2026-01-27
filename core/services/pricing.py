from ..models import Price, Asset
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta


def get_latest_prices(category=None):
    """
    Récupère les derniers prix, optionnellement filtrés par catégorie
    
    Args:
        category: catégorie optionnelle (fx, metal, crypto)
    
    Returns:
        list: derniers prix
    """
    query = Price.objects.all()
    
    if category:
        query = query.filter(asset__category=category)
    
    # Récupérer le dernier prix pour chaque actif
    latest_prices = []
    for asset in Asset.objects.filter(category=category) if category else Asset.objects.all():
        price = Price.objects.filter(asset=asset).order_by('-date').first()
        if price:
            latest_prices.append(price)
    
    return latest_prices


def get_price_history(asset_code, days=30):
    """
    Récupère l'historique des prix
    
    Args:
        asset_code: code de l'actif
        days: nombre de jours
    
    Returns:
        list: historique des prix
    """
    start_date = timezone.now().date() - timedelta(days=days)
    return Price.objects.filter(
        asset__code=asset_code,
        date__gte=start_date
    ).order_by('date')


def calculate_price_change(asset_code, days=7):
    """
    Calcule le changement de prix
    
    Args:
        asset_code: code de l'actif
        days: nombre de jours
    
    Returns:
        dict: changement et pourcentage
    """
    start_date = timezone.now().date() - timedelta(days=days)
    prices = Price.objects.filter(
        asset__code=asset_code,
        date__gte=start_date
    ).order_by('date')
    
    if len(prices) < 2:
        return {'error': 'Pas assez de données'}
    
    first_price = float(prices.first().price_mru)
    last_price = float(prices.last().price_mru)
    change = last_price - first_price
    change_percent = (change / first_price) * 100 if first_price != 0 else 0
    
    return {
        'period_days': days,
        'initial_price': first_price,
        'final_price': last_price,
        'change': change,
        'change_percent': round(change_percent, 2),
    }
