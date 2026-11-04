from django.urls import path
from . import views

app_name = 'incidents'

urlpatterns = [
    path('', views.liste_incidents, name='liste'),
    path('declarer/', views.declarer_incident, name='declarer'),
    path('<int:pk>/', views.detail_incident, name='detail'),
    path('<int:pk>/qualifier/', views.qualifier_incident, name='qualifier'),
    path('<int:pk>/action/', views.ajouter_action, name='ajouter_action'),
    path('<int:pk>/cloturer/', views.cloturer_incident, name='cloturer'),
    path('clotures/', views.incidents_clotures, name='clotures'),
    path('action/<int:pk>/demarrer/', views.demarrer_action, name='demarrer_action'),
    path('action/<int:pk>/terminer/', views.terminer_action, name='terminer_action'),
    path('notifications/', views.liste_notifications, name='notifications'),
    path('notifications/<int:pk>/lue/', views.marquer_notification_lue, name='notif_lue'),
    path('notifications/tout-lu/', views.marquer_toutes_lues, name='notif_tout_lu'),
]
