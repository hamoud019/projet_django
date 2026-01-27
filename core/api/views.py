from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from ..models import Asset, Price
from .serializers import AssetSerializer, PriceSerializer


class AssetViewSet(viewsets.ModelViewSet):
    """API pour les actifs (assets)"""
    queryset = Asset.objects.all()
    serializer_class = AssetSerializer
    lookup_field = 'code'

    @action(detail=True, methods=['get'])
    def prices(self, request, code=None):
        """Récupère tous les prix d'un actif"""
        asset = self.get_object()
        prices = Price.objects.filter(asset=asset).order_by('-date')
        serializer = PriceSerializer(prices, many=True)
        return Response(serializer.data)


class PriceViewSet(viewsets.ModelViewSet):
    """API pour les prix"""
    queryset = Price.objects.all().order_by('-date')
    serializer_class = PriceSerializer
    filter_fields = ['asset', 'date']
