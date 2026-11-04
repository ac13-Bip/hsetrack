from .models import Notification


def notifications_non_lues(request):
    """Expose le nombre de notifications non lues dans toutes les pages (cloche navbar)."""
    if request.user.is_authenticated:
        return {
            'nb_notifications_non_lues': Notification.objects.filter(
                destinataire=request.user, lue=False
            ).count()
        }
    return {'nb_notifications_non_lues': 0}
