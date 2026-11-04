"""
Tests de la couche service (regles de gestion, section 7 du cahier des
charges), sans passer par le client HTTP : plus rapides, et ils testent
directement le coeur metier independamment des vues/templates.
"""
from django.utils import timezone

from incidents.models import ActionCorrective, Incident
from incidents.services import (
    ActionNonAutorisee, cloturer_incident, declarer_incident,
    demarrer_action, terminer_action,
)
from .base import HSETestCase


class DeclarerIncidentTests(HSETestCase):
    def test_declaration_genere_une_reference_unique_et_une_priorite(self):
        incident = Incident(**self.donnees_incident_minimales())
        incident = declarer_incident(incident=incident, declarant=self.employe_casa)

        self.assertTrue(incident.reference.startswith(f"INC-{timezone.now().year}-"))
        self.assertEqual(incident.declarant, self.employe_casa)
        self.assertIsNotNone(incident.priorite)

    def test_deux_incidents_ont_des_references_differentes(self):
        i1 = declarer_incident(incident=Incident(**self.donnees_incident_minimales()), declarant=self.employe_casa)
        i2 = declarer_incident(incident=Incident(**self.donnees_incident_minimales()), declarant=self.employe_casa)
        self.assertNotEqual(i1.reference, i2.reference)

    def test_reference_non_reattribuee_apres_suppression(self):
        i1 = declarer_incident(incident=Incident(**self.donnees_incident_minimales()), declarant=self.employe_casa)
        i2 = declarer_incident(incident=Incident(**self.donnees_incident_minimales()), declarant=self.employe_casa)
        i1.delete()
        i3 = declarer_incident(incident=Incident(**self.donnees_incident_minimales()), declarant=self.employe_casa)
        self.assertNotEqual(i3.reference, i2.reference)


class CycleDeVieActionTests(HSETestCase):
    def setUp(self):
        self.incident = declarer_incident(
            incident=Incident(**self.donnees_incident_minimales()), declarant=self.employe_casa
        )
        self.action = ActionCorrective.objects.create(
            incident=self.incident, description="Nettoyer le sol", responsable=self.technicien,
            echeance=timezone.now().date(),
        )

    def test_demarrer_action_passe_incident_en_traitement(self):
        demarrer_action(action=self.action, utilisateur=self.technicien)
        self.incident.refresh_from_db()
        self.action.refresh_from_db()

        self.assertEqual(self.action.statut, ActionCorrective.StatutAction.EN_COURS)
        self.assertEqual(self.incident.statut, Incident.Statut.EN_TRAITEMENT)

    def test_demarrer_action_refuse_si_pas_le_responsable(self):
        with self.assertRaises(ActionNonAutorisee):
            demarrer_action(action=self.action, utilisateur=self.hse)

    def test_terminer_seule_action_resout_l_incident(self):
        demarrer_action(action=self.action, utilisateur=self.technicien)
        _, resolu = terminer_action(action=self.action, utilisateur=self.technicien, commentaire_realisation="Fait.")
        self.incident.refresh_from_db()

        self.assertTrue(resolu)
        self.assertEqual(self.incident.statut, Incident.Statut.RESOLU)
        self.assertEqual(self.action.commentaire_realisation, "Fait.")

    def test_incident_reste_en_traitement_si_une_autre_action_n_est_pas_terminee(self):
        autre_action = ActionCorrective.objects.create(
            incident=self.incident, description="Signaler la zone", responsable=self.technicien,
            echeance=timezone.now().date(),
        )
        demarrer_action(action=self.action, utilisateur=self.technicien)
        _, resolu = terminer_action(action=self.action, utilisateur=self.technicien)
        self.incident.refresh_from_db()

        self.assertFalse(resolu)
        self.assertEqual(self.incident.statut, Incident.Statut.EN_TRAITEMENT)
        self.assertEqual(autre_action.statut, ActionCorrective.StatutAction.A_FAIRE)

    def test_terminer_action_refuse_si_pas_le_responsable(self):
        with self.assertRaises(ActionNonAutorisee):
            terminer_action(action=self.action, utilisateur=self.hse)

    def test_cloturer_incident_idempotent(self):
        _, vient_de_cloturer_1 = cloturer_incident(incident=self.incident, utilisateur=self.hse)
        _, vient_de_cloturer_2 = cloturer_incident(incident=self.incident, utilisateur=self.hse)

        self.assertTrue(vient_de_cloturer_1)
        self.assertFalse(vient_de_cloturer_2)
        self.incident.refresh_from_db()
        self.assertEqual(self.incident.statut, Incident.Statut.CLOTURE)
        self.assertIsNotNone(self.incident.cloture_le)
