"""
Tests d'integration HTTP : reproduisent le cycle de vie complet d'un
incident tel que decrit dans le cahier des charges (section 6), en
verifiant aussi les restrictions par role (section 7).
"""
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from incidents.models import ActionCorrective, Incident, Notification
from .base import HSETestCase


class DeclarationEtCycleDeVieTests(HSETestCase):
    def test_cycle_complet_declaration_a_cloture(self):
        self.client.login(username='employe_casa', password='pass12345')
        reponse = self.client.post(reverse('incidents:declarer'), {
            'titre': 'Chute atelier 3',
            'description': 'Glissade sur sol mouille',
            'date_evenement': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'site': self.site_casa.pk,
            'service': self.service_casa_prod.pk,
            'lieu_precis': 'Atelier 3',
            'categorie': self.categorie.pk,
            'gravite': 2,
        }, follow=True)
        self.assertEqual(reponse.status_code, 200)
        incident = Incident.objects.get(titre='Chute atelier 3')
        self.assertEqual(incident.declarant, self.employe_casa)

        # L'employe d'un autre site ne doit pas pouvoir consulter l'incident.
        self.client.logout()
        self.client.login(username='employe_tanger', password='pass12345')
        reponse = self.client.get(reverse('incidents:detail', args=[incident.pk]), follow=True)
        self.assertEqual(len(reponse.redirect_chain), 1)  # redirige hors de la page

        # Le HSE qualifie et affecte l'incident au technicien.
        self.client.logout()
        self.client.login(username='hse1', password='pass12345')
        reponse = self.client.post(reverse('incidents:qualifier', args=[incident.pk]), {
            'categorie': self.categorie.pk, 'gravite': 3, 'priorite': 3,
            'affecte_a': self.technicien.pk, 'equipe_affectee': '',
            'echeance': timezone.now().date(), 'statut': 'AFFECTE',
        }, follow=True)
        self.assertEqual(reponse.status_code, 200)
        incident.refresh_from_db()
        self.assertEqual(incident.statut, 'AFFECTE')

        reponse = self.client.post(reverse('incidents:ajouter_action', args=[incident.pk]), {
            'type_action': 'CORRECTIVE', 'description': 'Nettoyer et signaliser',
            'responsable': self.technicien.pk, 'echeance': timezone.now().date(),
        }, follow=True)
        self.assertEqual(reponse.status_code, 200)
        action = ActionCorrective.objects.get(incident=incident)
        self.assertTrue(Notification.objects.filter(destinataire=self.technicien, incident=incident).exists())

        # Le technicien voit desormais l'incident (regression v1 corrigee).
        self.client.logout()
        self.client.login(username='tech1', password='pass12345')
        reponse = self.client.get(reverse('incidents:detail', args=[incident.pk]))
        self.assertEqual(reponse.status_code, 200)

        self.client.post(reverse('incidents:demarrer_action', args=[action.pk]))
        incident.refresh_from_db()
        self.assertEqual(incident.statut, 'EN_TRAITEMENT')

        # Le technicien ne peut pas cloturer.
        reponse = self.client.post(reverse('incidents:cloturer', args=[incident.pk]), follow=True)
        incident.refresh_from_db()
        self.assertNotEqual(incident.statut, 'CLOTURE')

        self.client.post(reverse('incidents:terminer_action', args=[action.pk]), {
            'commentaire_realisation': 'Sol nettoye.'
        })
        incident.refresh_from_db()
        self.assertEqual(incident.statut, 'RESOLU')

        # Le HSE cloture, l'incident devient lecture seule.
        self.client.logout()
        self.client.login(username='hse1', password='pass12345')
        self.client.post(reverse('incidents:cloturer', args=[incident.pk]))
        incident.refresh_from_db()
        self.assertEqual(incident.statut, 'CLOTURE')
        self.assertIsNotNone(incident.cloture_le)

    def test_direction_ne_peut_pas_qualifier(self):
        incident = Incident.objects.create(
            declarant=self.employe_casa, **self.donnees_incident_minimales()
        )
        self.client.login(username='direction1', password='pass12345')
        reponse = self.client.get(reverse('incidents:qualifier', args=[incident.pk]), follow=True)
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.redirect_chain[-1][0], reverse('incidents:detail', args=[incident.pk]))


class VerrouillageSiteDeclarationTests(HSETestCase):
    def test_employe_ne_peut_pas_choisir_un_autre_site(self):
        self.client.login(username='employe_casa', password='pass12345')
        reponse = self.client.post(reverse('incidents:declarer'), {
            'titre': 'Test usurpation site',
            'description': 'Tentative de declarer sur un autre site',
            'date_evenement': timezone.now().strftime('%Y-%m-%dT%H:%M'),
            'site': self.site_tanger.pk,  # falsifie
            'service': self.service_casa_prod.pk,
            'lieu_precis': '',
            'categorie': self.categorie.pk,
            'gravite': 2,
        }, follow=True)
        self.assertEqual(reponse.status_code, 200)
        incident = Incident.objects.get(titre='Test usurpation site')
        self.assertEqual(incident.site, self.site_casa)


class DashboardEtStatistiquesScopeTests(HSETestCase):
    def test_technicien_n_a_pas_acces_aux_statistiques_globales(self):
        self.client.login(username='tech1', password='pass12345')
        reponse = self.client.get(reverse('dashboard:statistiques'))
        self.assertEqual(reponse.status_code, 403)

    def test_direction_a_acces_aux_statistiques_globales(self):
        self.client.login(username='direction1', password='pass12345')
        reponse = self.client.get(reverse('dashboard:statistiques'))
        self.assertEqual(reponse.status_code, 200)


class AdministrationComptesTests(HSETestCase):
    def test_admin_peut_creer_et_desactiver_un_compte(self):
        self.client.login(username='admin1', password='pass12345')

        reponse = self.client.post(reverse('accounts:creer_utilisateur'), {
            'username': 'nouvel_employe', 'first_name': 'Nora', 'last_name': 'Test',
            'email': 'nora@hse.com', 'role': 'EMPLOYE', 'service': self.service_casa_prod.pk,
            'telephone': '', 'password1': 'UnMotDePasseSolide123', 'password2': 'UnMotDePasseSolide123',
        }, follow=True)
        self.assertEqual(reponse.status_code, 200)
        nouvel_utilisateur = User.objects.get(username='nouvel_employe')
        self.assertTrue(nouvel_utilisateur.is_active)

        reponse = self.client.post(reverse('accounts:gestion_utilisateurs'), {
            'toggle_user': '1', 'user_id': nouvel_utilisateur.pk,
        }, follow=True)
        nouvel_utilisateur.refresh_from_db()
        self.assertFalse(nouvel_utilisateur.is_active)

    def test_employe_ne_peut_pas_administrer(self):
        self.client.login(username='employe_casa', password='pass12345')
        reponse = self.client.get(reverse('accounts:gestion_utilisateurs'), follow=True)
        self.assertEqual(reponse.status_code, 200)
        self.assertEqual(reponse.redirect_chain[-1][0], reverse('dashboard:index'))
