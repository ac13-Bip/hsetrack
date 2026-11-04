from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('profile/', views.profile_view, name='profile'),
    path('administration/', views.gestion_utilisateurs, name='gestion_utilisateurs'),
    path('administration/nouveau/', views.creer_utilisateur, name='creer_utilisateur'),
    path('administration/<int:pk>/modifier/', views.modifier_utilisateur, name='modifier_utilisateur'),
    path('administration/<int:pk>/mot-de-passe/', views.reinitialiser_mot_de_passe, name='reinitialiser_mot_de_passe'),
]
