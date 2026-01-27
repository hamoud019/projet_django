from django.http import JsonResponse
from django.utils import timezone
from core.models import Price, Asset
from datetime import timedelta


def check_and_update_prices(request):
    """Endpoint pour vérifier les prix d'aujourd'hui et les mettre à jour si nécessaire"""
    today = timezone.now().date()
    
    data = {
        'today': str(today),
        'assets': [],
        'summary': {
            'total': 0,
            'with_today': 0,
            'missing': []
        },
        'all_recent_prices': []  # Afficher toutes les dates disponibles
    }
    
    # Afficher les dates les plus récentes en base
    recent_prices = Price.objects.all().order_by('-date')[:20]
    for p in recent_prices:
        data['all_recent_prices'].append({
            'asset': p.asset.code,
            'price': float(p.price_mru),
            'date': str(p.date),
            'source': p.source
        })
    
    assets = Asset.objects.all().order_by('category', 'code')
    
    for asset in assets:
        today_price = Price.objects.filter(
            asset=asset,
            date=today
        ).first()
        
        last_price = Price.objects.filter(asset=asset).order_by("-date").first()
        
        asset_data = {
            'code': asset.code,
            'label': asset.label,
            'category': asset.category,
            'has_today': bool(today_price),
        }
        
        if today_price:
            asset_data['price'] = float(today_price.price_mru)
            asset_data['date'] = str(today_price.date)
            asset_data['source'] = today_price.source
        elif last_price:
            days_diff = (today - last_price.date).days
            asset_data['last_price'] = float(last_price.price_mru)
            asset_data['last_date'] = str(last_price.date)
            asset_data['days_since'] = days_diff
            data['summary']['missing'].append(asset.code)
        
        data['assets'].append(asset_data)
    
    # Résumé
    data['summary']['total'] = Asset.objects.count()
    data['summary']['with_today'] = Price.objects.filter(date=today).values('asset').distinct().count()
    
    # Si scrape demandé
    if request.GET.get('scrape') == '1':
        try:
            from scripts.daily_scraper import DailyScraperJob
            result = DailyScraperJob.run()
            data['scrape_result'] = {
                'exit_code': result.get('exit_code'),
                'timestamp': result.get('timestamp'),
                'total_fetched': result.get('total_fetched'),
                'total_stored': result.get('total_stored'),
            }
        except Exception as e:
            data['scrape_error'] = str(e)
    
    return JsonResponse(data, json_dumps_params={'ensure_ascii': False, 'indent': 2})
