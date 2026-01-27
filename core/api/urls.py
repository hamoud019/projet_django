from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AssetViewSet, PriceViewSet

router = DefaultRouter()
router.register('assets', AssetViewSet, basename='asset')
router.register('prices', PriceViewSet, basename='price')

urlpatterns = [
    path('', include(router.urls)),
]
