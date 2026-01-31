from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db import transaction
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
    yahoo_assets = {"BTC", "GOLD", "COPPER", "IRON"}

    for asset in assets:
        price_qs = Price.objects.filter(asset=asset)
        if asset.code in yahoo_assets:
            price_qs = price_qs.filter(source="yahoo")

        # Chercher d'abord le prix d'aujourd'hui
        today_price = price_qs.filter(date=today).first()
        
        # Si pas de prix aujourd'hui, prendre le dernier disponible
        if today_price:
            last = today_price
        else:
            last = price_qs.order_by("-date").first()
        
        # Chercher les prix précédents pour les variations
        display_date = last.date if last else None
        if asset.code in yahoo_assets and not today_price and last:
            display_date = today

        if last:
            # Variation J-1 (hier)
            yesterday = today - timedelta(days=1)
            prev_j1 = price_qs.filter(date=yesterday).first()
            
            # Si pas hier, chercher les 8 derniers prix après aujourd'hui
            if not prev_j1:
                all_prices = price_qs.order_by("-date")[:10]
                if len(all_prices) > 1:
                    prev_j1 = all_prices[1]
            
            variation_j1 = None
            if prev_j1:
                variation_j1 = calculate_variation(float(last.price_mru), float(prev_j1.price_mru))
            
            # Variation J-7
            last_week = today - timedelta(days=7)
            prev_j7 = price_qs.filter(date__lte=last_week).order_by("-date").first()
            
            variation_j7 = None
            if prev_j7:
                variation_j7 = calculate_variation(float(last.price_mru), float(prev_j7.price_mru))
        else:
            variation_j1 = None
            variation_j7 = None

        data.append({
            "asset": asset,
            "price": last,
            "display_date": display_date,
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
    """Vue d?tail d'un actif avec filtres de dates"""
    asset = get_object_or_404(Asset, code=code)
    today = timezone.now().date()
    yahoo_assets = {"BTC", "GOLD", "COPPER", "IRON"}

    # Filtres de dates
    days = int(request.GET.get('days', 365))  # Par d?faut 1 an
    start_date = timezone.now().date() - timedelta(days=days)

    price_qs = Price.objects.filter(asset=asset)
    if asset.code in yahoo_assets:
        price_qs = price_qs.filter(source="yahoo")

    # Forcer un prix "aujourd'hui" si absent (copie du dernier connu)
    today_price = price_qs.filter(date=today).first()
    if not today_price:
        last = price_qs.order_by("-date").first()
        if last:
            try:
                with transaction.atomic():
                    Price.objects.update_or_create(
                        asset=asset,
                        date=today,
                        defaults={"price_mru": last.price_mru, "source": last.source},
                    )
            except Exception:
                pass
            today_price = price_qs.filter(date=today).first()

    prices = price_qs.filter(date__gte=start_date).order_by('date')

    # Prix courant align? avec l'accueil
    last = today_price or price_qs.order_by("-date").first()
    current_price = float(last.price_mru) if last else 0
    display_date = today if (not today_price and last) else (last.date if last else None)

    # Variation 24h
    yesterday = today - timedelta(days=1)
    prev_j1 = price_qs.filter(date=yesterday).first()
    if not prev_j1:
        recent = price_qs.order_by("-date")[:2]
        prev_j1 = recent[1] if len(recent) > 1 else None
    price_change = calculate_variation(current_price, float(prev_j1.price_mru)) if prev_j1 else 0

    # Min / max 7 jours
    last_7d = price_qs.filter(date__gte=today - timedelta(days=7))
    if last_7d.exists():
        values_7d = [float(p.price_mru) for p in last_7d]
        min_7d = min(values_7d)
        max_7d = max(values_7d)
    else:
        min_7d = 0
        max_7d = 0

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

    # Pr?parer les donn?es pour le graphique
    chart_dates = [str(p.date) for p in prices]
    chart_prices = [float(p.price_mru) for p in prices]

    return render(request, "core/asset_detail.html", {
        "asset": asset,
        "prices": prices,
        "days": days,
        "current_price": current_price,
        "price_change": price_change,
        "min_7d": min_7d,
        "max_7d": max_7d,
        "display_date": display_date,
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



