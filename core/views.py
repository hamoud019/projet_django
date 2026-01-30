from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from .models import Asset, Price
from .services.pricing import get_latest_prices, get_price_history
from .services.comparison import compare_assets, calculate_variation
from .services.prediction import predict_price, get_predictions_multiple
from datetime import datetime, timedelta
from django.utils import timezone
import json


def home(request):
    """Vue d'accueil avec les derniers prix et variations"""
    assets = Asset.objects.all().order_by('category', 'code')
    data = []
    today = timezone.now().date()

    for asset in assets:
        # Chercher d'abord le prix d'aujourd'hui
        today_price = Price.objects.filter(
            asset=asset,
            date=today
        ).first()
        
        # Si pas de prix aujourd'hui, prendre le dernier disponible
        if today_price:
            last = today_price
        else:
            last = Price.objects.filter(asset=asset).order_by("-date").first()
        
        # Chercher les prix précédents pour les variations
        if last:
            # Variation J-1 (hier)
            yesterday = today - timedelta(days=1)
            prev_j1 = Price.objects.filter(
                asset=asset,
                date=yesterday
            ).first()
            
            # Si pas hier, chercher les 8 derniers prix après aujourd'hui
            if not prev_j1:
                all_prices = Price.objects.filter(asset=asset).order_by("-date")[:10]
                if len(all_prices) > 1:
                    prev_j1 = all_prices[1]
            
            variation_j1 = None
            if prev_j1:
                variation_j1 = calculate_variation(float(last.price_mru), float(prev_j1.price_mru))
            
            # Variation J-7
            last_week = today - timedelta(days=7)
            prev_j7 = Price.objects.filter(
                asset=asset,
                date__lte=last_week
            ).order_by("-date").first()
            
            variation_j7 = None
            if prev_j7:
                variation_j7 = calculate_variation(float(last.price_mru), float(prev_j7.price_mru))
        else:
            variation_j1 = None
            variation_j7 = None

        data.append({
            "asset": asset,
            "price": last,
            "variation_j1": variation_j1,
            "variation_j7": variation_j7,
            "variation": variation_j1 or variation_j7,
        })

    # Grouper par catégorie
    devises = [d for d in data if d['asset'].category == 'fx']
    metaux = [d for d in data if d['asset'].category == 'metal']
    crypto = [d for d in data if d['asset'].category == 'crypto']

    return render(request, "core/home.html", {
        "data": data,
        "devises": devises,
        "metaux": metaux,
        "crypto": crypto,
    })


def asset_detail(request, code):
    """Vue détail d'un actif avec filtres de dates"""
    asset = get_object_or_404(Asset, code=code)
    
    # Filtres de dates
    days = int(request.GET.get('days', 365))  # Par défaut 1 an
    start_date = timezone.now().date() - timedelta(days=days)
    
    prices = Price.objects.filter(
        asset=asset,
        date__gte=start_date
    ).order_by('date')

    # Calculer min et max
    min_price = float('inf')
    max_price = 0.0
    for p in prices:
        price_val = float(p.price_mru)
        if price_val < min_price:
            min_price = price_val
        if price_val > max_price:
            max_price = price_val
    
    if min_price == float('inf'):
        min_price = 0

    # Préparer les données pour le graphique
    chart_dates = [str(p.date) for p in prices]
    chart_prices = [float(p.price_mru) for p in prices]

    return render(request, "core/asset_detail.html", {
        "asset": asset,
        "prices": prices,
        "days": days,
        "min_price": min_price,
        "max_price": max_price,
        "chart_dates": json.dumps(chart_dates),
        "chart_prices": json.dumps(chart_prices),
    })


def comparison_view(request):
    """Vue de comparaison par catégorie"""
    category_type = request.GET.get('type', 'all')  # all, devises, metaux
    
    # Récupérer les actifs par catégorie
    if category_type == 'devises':
        assets = Asset.objects.filter(category='fx').order_by('code')
    elif category_type == 'metaux':
        assets = Asset.objects.filter(category='metal').order_by('code')
    else:
        assets = Asset.objects.all().order_by('category', 'code')
    
    # Récupérer les données de comparaison
    comparison = {}
    for asset in assets:
        prices = Price.objects.filter(asset=asset).order_by('-date')[:365]
        
        if prices:
            price_values = [float(p.price_mru) for p in prices]
            comparison[asset.code] = {
                'asset': asset,
                'current_price': float(prices[0].price_mru),
                'min': min(price_values),
                'max': max(price_values),
                'avg': sum(price_values) / len(price_values),
                'chart_dates': json.dumps([str(p.date) for p in reversed(prices)]),
                'chart_prices': json.dumps([float(p.price_mru) for p in reversed(prices)]),
            }
    
    # Grouper par catégorie
    devises = {k: v for k, v in comparison.items() if v['asset'].category == 'fx'}
    metaux = {k: v for k, v in comparison.items() if v['asset'].category == 'metal'}

    # Pour le graphique des devises : récupérer les dates du premier actif devise
    currencies_chart_dates = []
    if devises:
        currencies_chart_dates = next(iter(devises.values()))['chart_dates']
    return render(request, "core/comparison.html", {
        "comparison": comparison,
        "devises": devises,
        "metaux": metaux,
        "category_type": category_type,
        "currencies_chart_dates": currencies_chart_dates,
    })


def prediction_view(request):
    """Vue de prédiction avec sélection d'actif et horizon"""
    assets = Asset.objects.all().order_by('category', 'code')
    selected_asset_code = request.GET.get('asset', None)
    days_ahead = int(request.GET.get('days', 7))  # 7 ou 30
    
    prediction = None
    if selected_asset_code:
        try:
            asset = Asset.objects.get(code=selected_asset_code)
            prediction = predict_price(asset, days_ahead)
            
            if 'predictions' in prediction:
                # Préparer les données pour le graphique
                pred_dates = prediction['historical_dates'] + [str(p['date']) for p in prediction['predictions']]
                pred_values = prediction['historical_values'] + [p['value'] for p in prediction['predictions']]
                prediction['chart_dates'] = json.dumps(pred_dates)
                prediction['chart_prices'] = json.dumps(pred_values)
                
                # Ajouter un indicateur pour les prédictions
                prediction['historical_length'] = len(prediction['historical_dates'])
        except Asset.DoesNotExist:
            prediction = {'error': f'Actif {selected_asset_code} non trouvé'}

    return render(request, "core/prediction.html", {
        "assets": assets,
        "prediction": prediction,
        "selected_asset": selected_asset_code,
        "days_ahead": days_ahead,
    })


def comparison_devises_metaux(request):
    """Vue comparant devises vs matières premières"""
    # Récupérer un actif de chaque catégorie
    devises = Asset.objects.filter(category='fx').order_by('code')
    metaux = Asset.objects.filter(category='metal').order_by('code')
    
    return render(request, "core/comparison_categories.html", {
        "devises": devises,
        "metaux": metaux,
    })



