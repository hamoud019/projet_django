from django.urls import path
from . import views
from .api.check_prices_view import check_and_update_prices

urlpatterns = [
    path("", views.home, name="home"),
    path("asset/<str:code>/", views.asset_detail, name="asset_detail"),
    path("comparison/", views.comparison_view, name="comparison"),
    path("prediction/", views.prediction_view, name="prediction"),
    path("api/check-prices/", check_and_update_prices, name="check_prices"),
]
