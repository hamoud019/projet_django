from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("asset/<str:code>/", views.asset_detail, name="asset_detail"),
    path("comparison/", views.comparison_view, name="comparison"),
    path("prediction/", views.prediction_view, name="prediction"),
]
