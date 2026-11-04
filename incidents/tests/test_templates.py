"""
Smoke tests : verifient que chaque page se rend (statut 200) pour le role
concerne, sans erreur de template. Les tests de services/vues verifient
deja le comportement metier ; ceux-ci verifient que le rendu HTML ne
plante pas (ex : layout crispy_forms, blocs conditionnels par role).
"""
from django.urls import reverse
from django.utils import timezone

from incidents.models import ActionCorrective, Incident
from incidents.services import cloturer_incident, declarer_incident
from .base import HSETestCase


class PagesAccessiblesParRoleTests(HSETestCase):
    def setUp(self):
        self.incident = declarer_incident(
            incident=Incident(**self.donnees_incident_minimales()), declarant=self.employe_casa
        )
        self.action = ActionCorrective.objects.create(
            incident=self.incident, description="Verifier l'extincteur", responsable=self.technicien,
            echeance=timezone.now().date(),
        )

    def _verifie_200(self, username, url_name, args=None):
        self.client.login(username=username, password='pass12345')
        reponse = self.client.get(reverse(url_name, args=args))
        self.assertEqual(reponse.status_code, 200, f"{url_name} a echoue pour {username}")
        self.client.logout()

    def test_pages_communes_a_tous_les_roles(self):
        for username in ['employe_casa', 'hse1', 'tech1', 'admin1', 'direction1']:
            self._verifie_200(username, 'dashboard:index')
            self._verifie_200(username, 'incidents:liste')
            self._verifie_200(username, 'incidents:declarer')
            self._verifie_200(username, 'incidents:notifications')
            self._verifie_200(username, 'accounts:profile')

    def test_detail_incident_pour_declarant_hse_et_technicien_affecte(self):
        self._verifie_200('employe_casa', 'incidents:detail', args=[self.incident.pk])
        self._verifie_200('hse1', 'incidents:detail', args=[self.incident.pk])
        self._verifie_200('tech1', 'incidents:detail', args=[self.incident.pk])

    def test_incident_cloture_sans_boutons_de_gestion(self):
        cloturer_incident(incident=self.incident, utilisateur=self.hse)
        self.client.login(username='hse1', password='pass12345')
        reponse = self.client.get(reverse('incidents:detail', args=[self.incident.pk]))
        self.assertNotContains(reponse, reverse('incidents:qualifier', args=[self.incident.pk]))
        self.assertNotContains(reponse, reverse('incidents:cloturer', args=[self.incident.pk]))

    def test_direction_voit_tous_les_incidents_clotures(self):
        cloturer_incident(incident=self.incident, utilisateur=self.hse)
        self.client.login(username='direction1', password='pass12345')
        reponse = self.client.get(reverse('incidents:clotures'))
        self.assertContains(reponse, self.incident.reference)

    def test_pages_reservees_hse_admin(self):
        for username in ['hse1', 'admin1']:
            self._verifie_200(username, 'incidents:qualifier', args=[self.incident.pk])
            self._verifie_200(username, 'incidents:ajouter_action', args=[self.incident.pk])
            self._verifie_200(username, 'incidents:clotures')

    def test_pages_reservees_supervision_globale(self):
        for username in ['hse1', 'admin1', 'direction1']:
            self._verifie_200(username, 'dashboard:statistiques')

    def test_pages_administration(self):
        self._verifie_200('admin1', 'accounts:gestion_utilisateurs')
        self._verifie_200('admin1', 'accounts:creer_utilisateur')
        self._verifie_200('admin1', 'accounts:modifier_utilisateur', args=[self.employe_casa.pk])
