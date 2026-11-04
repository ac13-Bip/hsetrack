from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.index, name='index'),
    path('statistiques/', views.statistiques, name='statistiques'),
]
