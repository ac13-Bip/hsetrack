"""
Verifie que le responsable HSE est notifie systematiquement a chaque
declaration d'incident (et pas uniquement pour les incidents critiques).
"""
from incidents.models import Incident, Notification
from incidents.services import declarer_incident
from .base import HSETestCase


class NotificationDeclarationTests(HSETestCase):
    def test_hse_notifie_pour_un_incident_non_critique(self):
        incident = declarer_incident(
            incident=Incident(**self.donnees_incident_minimales()), declarant=self.employe_casa
        )
        notif = Notification.objects.get(destinataire=self.hse, incident=incident)
        self.assertEqual(notif.niveau, Notification.Niveau.INFO)
        self.assertIn(incident.reference, notif.message)

    def test_hse_notifie_en_alerte_pour_un_incident_critique(self):
        donnees = self.donnees_incident_minimales()
        donnees['gravite'] = Incident.Gravite.CRITIQUE
        incident = declarer_incident(incident=Incident(**donnees), declarant=self.employe_casa)

        notif = Notification.objects.get(destinataire=self.hse, incident=incident)
        self.assertEqual(notif.niveau, Notification.Niveau.ALERTE)
        self.assertIn("CRITIQUE", notif.message)

    def test_un_seul_responsable_hse_actif_recoit_la_notification(self):
        from accounts.models import User
        autre_hse = User.objects.create_user(
            'hse2', password='pass12345', role=User.Role.RESPONSABLE_HSE,
            service=self.service_casa_prod, is_active=False,
        )
        incident = declarer_incident(
            incident=Incident(**self.donnees_incident_minimales()), declarant=self.employe_casa
        )
        self.assertTrue(Notification.objects.filter(destinataire=self.hse, incident=incident).exists())
        self.assertFalse(Notification.objects.filter(destinataire=autre_hse, incident=incident).exists())
