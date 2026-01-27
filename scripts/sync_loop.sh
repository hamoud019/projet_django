#!/bin/bash
# Script de synchronisation périodique
# Synchronise PostgreSQL → MongoDB toutes les 6h

echo "🔄 Service de synchronisation PostgreSQL → MongoDB"
echo "=================================================="

# Boucle infinie - exécute la sync toutes les 6h
while true; do
    echo ""
    echo "⏰ $(date): Exécution de la synchronisation..."
    
    # Sync fenêtre glissante (7 derniers jours)
    python manage.py sync_prices_to_mongo --days 7 --verify
    
    # Vérifier la cohérence
    RESULT=$?
    
    if [ $RESULT -eq 0 ]; then
        echo "✅ Sync réussie"
    else
        echo "❌ Erreur sync, code: $RESULT"
    fi
    
    echo ""
    echo "⏳ Prochaine sync dans 6h (21600s)..."
    sleep 21600  # 6 heures en secondes
done
