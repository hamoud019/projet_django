from ..models import Price
from datetime import timedelta
from django.utils import timezone
from statistics import mean, stdev
import math
import random


class DecisionTree:
    """Arbre de décision simplifié pour Random Forest"""
    def __init__(self, max_depth=5):
        self.max_depth = max_depth
        self.tree = None
    
    def build(self, X, y, depth=0):
        """Construit récursivement l'arbre"""
        if depth >= self.max_depth or len(X) < 2:
            return mean(y) if y else 0
        
        best_split = None
        best_gain = 0
        
        # Essayer de diviser sur chaque feature
        for feature_idx in range(len(X[0])):
            values = sorted(set(x[feature_idx] for x in X))
            
            for threshold in values[:max(1, len(values)//3)]:  # Limiter les seuils
                left_X = [X[i] for i in range(len(X)) if X[i][feature_idx] <= threshold]
                right_X = [X[i] for i in range(len(X)) if X[i][feature_idx] > threshold]
                
                if not left_X or not right_X:
                    continue
                
                left_y = [y[i] for i in range(len(y)) if X[i][feature_idx] <= threshold]
                right_y = [y[i] for i in range(len(y)) if X[i][feature_idx] > threshold]
                
                # Gain de variance
                gain = self._variance_reduction(y, left_y, right_y)
                
                if gain > best_gain:
                    best_gain = gain
                    best_split = (feature_idx, threshold, left_X, right_X, left_y, right_y)
        
        if best_split is None:
            return mean(y)
        
        feature_idx, threshold, left_X, right_X, left_y, right_y = best_split
        
        return {
            'feature': feature_idx,
            'threshold': threshold,
            'left': self.build(left_X, left_y, depth + 1),
            'right': self.build(right_X, right_y, depth + 1)
        }
    
    def _variance_reduction(self, parent, left, right):
        """Calcule la réduction de variance"""
        if not parent:
            return 0
        
        n = len(parent)
        n_left = len(left)
        n_right = len(right)
        
        if n_left == 0 or n_right == 0:
            return 0
        
        var_parent = stdev(parent) ** 2 if len(parent) > 1 else 0
        var_left = stdev(left) ** 2 if len(left) > 1 else 0
        var_right = stdev(right) ** 2 if len(right) > 1 else 0
        
        gain = var_parent - (n_left/n * var_left + n_right/n * var_right)
        return gain
    
    def predict(self, x, node=None):
        """Prédit la valeur pour une entrée x"""
        if node is None:
            node = self.tree
        
        if isinstance(node, dict):
            if x[node['feature']] <= node['threshold']:
                return self.predict(x, node['left'])
            else:
                return self.predict(x, node['right'])
        else:
            return node


class RandomForestRegressor:
    """Random Forest simplifié pour régression"""
    def __init__(self, n_trees=10, max_depth=5, max_features=None):
        self.n_trees = n_trees
        self.max_depth = max_depth
        self.max_features = max_features
        self.trees = []
    
    def fit(self, X, y):
        """Entraîne les arbres sur des sous-ensembles aléatoires"""
        for _ in range(self.n_trees):
            # Bootstrap sample
            indices = [random.randint(0, len(X)-1) for _ in range(len(X))]
            X_sample = [X[i] for i in indices]
            y_sample = [y[i] for i in indices]
            
            # Construire l'arbre
            tree = DecisionTree(max_depth=self.max_depth)
            tree.tree = tree.build(X_sample, y_sample)
            self.trees.append(tree)
    
    def predict(self, X):
        """Prédit en moyennant les prédictions de tous les arbres"""
        predictions = []
        for x in X:
            tree_predictions = [tree.predict(x) for tree in self.trees]
            predictions.append(mean(tree_predictions))
        return predictions


def linear_regression(x_values, y_values):
    """
    Régression linéaire simple sans numpy
    Retourne (pente, intercept, r_squared)
    """
    n = len(x_values)
    mean_x = sum(x_values) / n
    mean_y = sum(y_values) / n
    
    numerator = sum((x_values[i] - mean_x) * (y_values[i] - mean_y) for i in range(n))
    denominator = sum((x_values[i] - mean_x) ** 2 for i in range(n))
    
    if denominator == 0:
        return 0, mean_y, 0
    
    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    
    # Calculer R²
    y_pred = [slope * x + intercept for x in x_values]
    ss_res = sum((y_values[i] - y_pred[i]) ** 2 for i in range(n))
    ss_tot = sum((y - mean_y) ** 2 for y in y_values)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
    
    return slope, intercept, r_squared


def exponential_smoothing(values, alpha=0.3):
    """
    Lissage exponentiel simple
    """
    if not values:
        return []
    
    smoothed = [values[0]]
    for i in range(1, len(values)):
        smoothed.append(alpha * values[i] + (1 - alpha) * smoothed[i-1])
    
    return smoothed


def moving_average(values, window=7):
    """Moyenne mobile simple"""
    if len(values) < window:
        return values
    
    ma = []
    for i in range(len(values) - window + 1):
        ma.append(mean(values[i:i+window]))
    
    return ma


def calculate_rsi(values, period=14):
    """
    Calcul de l'Indice de Force Relative (RSI)
    Valeur entre 0 et 100
    """
    if len(values) < period:
        return 50  # Neutre par défaut
    
    deltas = [values[i] - values[i-1] for i in range(1, len(values))]
    
    gains = [d for d in deltas if d > 0]
    losses = [-d for d in deltas if d < 0]
    
    avg_gain = mean(gains[-period:]) if gains else 0
    avg_loss = mean(losses[-period:]) if losses else 0
    
    if avg_loss == 0:
        return 100 if avg_gain > 0 else 50
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    
    return min(100, max(0, rsi))


def calculate_bollinger_bands(values, window=20, num_std=2):
    """
    Bandes de Bollinger: moyenne mobile ± écart-types
    """
    if len(values) < window:
        return None
    
    last_values = values[-window:]
    middle = mean(last_values)
    std = stdev(last_values) if len(last_values) > 1 else 0
    
    return {
        'middle': middle,
        'upper': middle + (num_std * std),
        'lower': middle - (num_std * std),
    }


def create_features(values, window=7):
    """Crée des features pour Random Forest basées sur l'historique des prix"""
    features = []
    targets = []
    
    for i in range(window, len(values) - 1):
        # Features: les 'window' derniers prix normalisés
        recent_prices = values[i-window:i]
        avg_recent = mean(recent_prices)
        
        # Normaliser les prix
        normalized = [(p - avg_recent) / avg_recent if avg_recent != 0 else 0 for p in recent_prices]
        
        # Ajouter des features techniques
        rsi_val = calculate_rsi(values[:i+1], period=14)
        ma_val = moving_average(values[max(0, i-7):i+1], window=7)[-1] if len(values[max(0, i-7):i+1]) >= 7 else values[i]
        
        features.append(normalized + [rsi_val/100, (ma_val - values[i]) / values[i]])
        targets.append(values[i+1])
    
    return features, targets


def predict_price(asset, days_ahead=7):
    """
    Prédiction avec Random Forest + indicateurs techniques
    
    Args:
        asset: Asset object
        days_ahead: nombre de jours à prédire (7 ou 30)
    
    Returns:
        dict: prédictions avec dates et indicateurs techniques
    """
    # Récupérer les 120 derniers prix
    days_back = 120
    start_date = timezone.now().date() - timedelta(days=days_back)
    prices = Price.objects.filter(
        asset=asset,
        date__gte=start_date
    ).order_by('date')
    
    if len(prices) < 20:  # Augmenté pour Random Forest
        return {'error': 'Pas assez de données (min 20 prix)'}
    
    # Extraire les données
    dates = []
    values = []
    for i, p in enumerate(prices):
        dates.append(p.date)
        values.append(float(p.price_mru))
    
    # Méthode 1: Régression linéaire (référence)
    x = list(range(len(values)))
    y = values
    slope_lr, intercept_lr, r_squared = linear_regression(x, y)
    
    # Méthode 2: Lissage exponentiel
    smoothed = exponential_smoothing(values, alpha=0.3)
    
    # Méthode 3: Moyenne mobile (prédire la tendance)
    ma7 = moving_average(values, window=7)
    recent_ma = ma7[-1] if ma7 else values[-1]
    last_price = values[-1]
    ma_trend = recent_ma - last_price
    
    # Méthode 4: Random Forest (nouveau)
    X_train, y_train = create_features(values, window=7)
    
    rf_model = RandomForestRegressor(n_trees=10, max_depth=5)
    if len(X_train) > 2:  # Besoin d'au moins 3 samples
        rf_model.fit(X_train, y_train)
        rf_ready = True
        
        # Évaluer la qualité du modèle RF
        rf_predictions = rf_model.predict(X_train[-10:])
        rf_actual = y_train[-10:]
        rf_r_squared = 1 - (sum((rf_actual[i] - rf_predictions[i])**2 for i in range(len(rf_actual))) / 
                           sum((y - mean(rf_actual))**2 for y in rf_actual))
    else:
        rf_ready = False
        rf_r_squared = 0
    
    # Indicateurs techniques
    rsi = calculate_rsi(values, period=14)
    bb = calculate_bollinger_bands(values, window=20)
    
    # Calculer les prédictions
    today = timezone.now().date()
    predictions = []
    
    for day in range(1, days_ahead + 1):
        pred_date = today + timedelta(days=day)
        x_pred = len(values) + day - 1
        
        # Prédiction linéaire
        pred_lr = slope_lr * x_pred + intercept_lr
        
        # Prédiction exponentielle
        pred_exp = smoothed[-1] + (smoothed[-1] - smoothed[-2]) * day if len(smoothed) > 1 else smoothed[-1]
        
        # Prédiction par momentum
        pred_momentum = last_price + (ma_trend * 0.5 * day)
        
        # Prédiction Random Forest
        pred_rf = None
        if rf_ready and day <= 7:  # RF fiable sur court terme
            recent_prices = values[-7:]
            avg_recent = mean(recent_prices)
            normalized = [(p - avg_recent) / avg_recent if avg_recent != 0 else 0 for p in recent_prices]
            rsi_norm = rsi / 100
            ma_norm = (recent_ma - last_price) / last_price if last_price != 0 else 0
            
            x_rf = [normalized + [rsi_norm, ma_norm]]
            pred_rf = rf_model.predict(x_rf)[0]
        
        # Moyenne pondérée intelligente
        weights = []
        predictions_list = [pred_lr, pred_exp, pred_momentum]
        
        if pred_rf is not None:
            predictions_list.append(pred_rf)
            # Poids: LR, Exp, Momentum, RF
            weights = [max(0.2, r_squared * 0.4), 0.25, 0.2, max(0.15, rf_r_squared * 0.4)]
        else:
            # Poids: LR, Exp, Momentum
            w_lr = max(0.3, r_squared)
            w_exp = 0.25
            w_mom = 1 - w_lr - w_exp
            weights = [w_lr, w_exp, w_mom]
        
        # Normaliser les poids
        total_weight = sum(weights)
        weights = [w / total_weight for w in weights]
        
        pred_value = sum(p * w for p, w in zip(predictions_list, weights))
        
        # Garder les prédictions dans une plage raisonnable
        min_price = min(values) * 0.7
        max_price = max(values) * 1.3
        pred_value = max(min_price, min(max_price, pred_value))
        
        predictions.append({
            'date': pred_date,
            'value': round(pred_value, 2),
            'method_lr': round(pred_lr, 2),      # Régression linéaire
            'method_exp': round(pred_exp, 2),    # Exponentielle
            'method_mom': round(pred_momentum, 2), # Momentum
            'method_rf': round(pred_rf, 2) if pred_rf else None,  # Random Forest
        })
    
    # Calculs de volatilité et tendance
    volatility = stdev(values) if len(values) > 1 else 0
    avg_price = mean(values)
    
    # Tendance: comparer les 7 derniers jours vs moyenne globale
    recent_avg = mean(values[-7:]) if len(values) >= 7 else mean(values)
    if recent_avg > avg_price * 1.01:
        trend = "haussier"
    elif recent_avg < avg_price * 0.99:
        trend = "baissier"
    else:
        trend = "neutre"
    
    # Signal de trading basé sur RSI
    if rsi > 70:
        signal = "suracheté (RSI > 70)"
        signal_type = "warning"
    elif rsi < 30:
        signal = "survendu (RSI < 30)"
        signal_type = "success"
    else:
        signal = f"Neutre (RSI = {round(rsi, 1)})"
        signal_type = "info"
    
    # Choisir le meilleur modèle
    best_model = "Random Forest" if rf_ready and rf_r_squared > 0.5 else ("Linéaire" if r_squared > 0.5 else "Ensemble")
    
    result = {
        'asset_code': asset.code,
        'asset_label': asset.label,
        'current_price': float(values[-1]),
        'average': avg_price,
        'min_price': min(values),
        'max_price': max(values),
        'volatility': volatility,
        'volatility_percent': round((volatility / avg_price * 100), 2),
        'trend': trend,
        'predictions': predictions,
        'historical_dates': [str(d) for d in dates[-30:]],  # Derniers 30 jours
        'historical_values': values[-30:],
        'historical_length': len([str(d) for d in dates[-30:]]),
        
        # Indicateurs techniques
        'rsi': round(rsi, 1),
        'signal': signal,
        'signal_type': signal_type,
        'bollinger_bands': {
            'middle': round(bb['middle'], 2) if bb else avg_price,
            'upper': round(bb['upper'], 2) if bb else avg_price * 1.1,
            'lower': round(bb['lower'], 2) if bb else avg_price * 0.9,
        },
        
        # Qualité de la prédiction
        'model_quality_lr': f"R² = {round(r_squared, 3)} ({round(r_squared*100)}%)",
        'model_quality_rf': f"R² = {round(rf_r_squared, 3)} ({round(rf_r_squared*100)}%)" if rf_ready else "N/A",
        'best_model': best_model,
        'confidence': "Élevée" if (rf_r_squared if rf_ready else r_squared) > 0.7 else ("Moyenne" if (rf_r_squared if rf_ready else r_squared) > 0.4 else "Faible"),
    }
    
    return result


def get_predictions_multiple(asset_codes, days_ahead=7):
    """Récupère les prédictions pour plusieurs actifs"""
    from ..models import Asset
    predictions = {}
    
    for code in asset_codes:
        try:
            asset = Asset.objects.get(code=code)
            predictions[code] = predict_price(asset, days_ahead)
        except Asset.DoesNotExist:
            predictions[code] = {'error': f'Actif {code} non trouvé'}
    
    return predictions
