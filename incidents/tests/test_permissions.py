"""
Tests de la regle de visibilite des incidents par role (section 7).
C'est la regle qui avait le plus de bugs dans la version precedente du
projet (technicien bloque hors de l'incident qui lui etait affecte,
dashboard donnant un acces global a des roles qui n'y sont pas habilites) :
on la couvre donc explicitement pour ne plus jamais regresser.
"""
from django.utils import timezone

from accounts.models import User
from incidents.models import ActionCorrective, Incident
from incidents.permissions import incidents_visibles, peut_voir_incident
from incidents.services import declarer_incident
from .base import HSETestCase


class VisibiliteIncidentsTests(HSETestCase):
    def setUp(self):
        self.incident_casa = declarer_incident(
            incident=Incident(**self.donnees_incident_minimales(site=self.site_casa)),
            declarant=self.employe_casa,
        )
        self.incident_tanger = declarer_incident(
            incident=Incident(**self.donnees_incident_minimales(site=self.site_tanger)),
            declarant=self.employe_tanger,
        )

    def test_hse_admin_direction_voient_tous_les_sites(self):
        for utilisateur in [self.hse, self.admin, self.direction]:
            visibles = incidents_visibles(utilisateur)
            self.assertIn(self.incident_casa, visibles)
            self.assertIn(self.incident_tanger, visibles)

    def test_employe_voit_uniquement_son_site(self):
        visibles_casa = incidents_visibles(self.employe_casa)
        self.assertIn(self.incident_casa, visibles_casa)
        self.assertNotIn(self.incident_tanger, visibles_casa)

        visibles_tanger = incidents_visibles(self.employe_tanger)
        self.assertIn(self.incident_tanger, visibles_tanger)
        self.assertNotIn(self.incident_casa, visibles_tanger)

    def test_technicien_voit_l_incident_dont_il_a_une_action_assignee(self):
        # Sans affectation, le technicien ne voit rien sur cet incident.
        self.assertFalse(peut_voir_incident(self.technicien, self.incident_casa))

        ActionCorrective.objects.create(
            incident=self.incident_casa, description="Reparer", responsable=self.technicien,
            echeance=timezone.now().date(),
        )

        # Avec une action assignee, l'acces doit etre accorde (regression
        # corrigee par rapport a la v1 du projet).
        self.assertTrue(peut_voir_incident(self.technicien, self.incident_casa))
        self.assertFalse(peut_voir_incident(self.technicien, self.incident_tanger))

    def test_technicien_voit_l_incident_affecte_a_son_equipe(self):
        self.incident_casa.equipe_affectee = self.equipe
        self.incident_casa.save()
        self.assertTrue(peut_voir_incident(self.technicien, self.incident_casa))
