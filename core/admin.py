from django.contrib import admin
from .models import Asset, Price

@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = ("code", "label", "category")
    list_filter = ("category",)
    search_fields = ("code", "label")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        # Créer les 7 actifs par défaut
        assets_data = [
            {"code": "USD", "label": "Dollar US", "category": "fx"},
            {"code": "EUR", "label": "Euro", "category": "fx"},
            {"code": "CNY", "label": "Yuan Chinois", "category": "fx"},
            {"code": "BTC", "label": "Bitcoin", "category": "crypto"},
            {"code": "GOLD", "label": "Or (once)", "category": "metal"},
            {"code": "IRON", "label": "Fer (tonne)", "category": "metal"},
            {"code": "COPPER", "label": "Cuivre (tonne)", "category": "metal"},
        ]
        for data in assets_data:
            Asset.objects.get_or_create(
                code=data["code"],
                defaults={"label": data["label"], "category": data["category"]}
            )


@admin.register(Price)
class PriceAdmin(admin.ModelAdmin):
    list_display = ("asset", "date", "price_mru")
    list_filter = ("asset",)
    date_hierarchy = "date"
