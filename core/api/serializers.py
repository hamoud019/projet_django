from rest_framework import serializers
from ..models import Asset, Price


class AssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asset
        fields = ['code', 'label', 'category']


class PriceSerializer(serializers.ModelSerializer):
    asset_code = serializers.CharField(source='asset.code', read_only=True)
    
    class Meta:
        model = Price
        fields = ['id', 'asset_code', 'date', 'price_mru']
