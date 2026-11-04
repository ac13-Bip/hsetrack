"""Fixtures communes aux tests : sites, services, utilisateurs de chaque role."""
from django.test import TestCase
from django.utils import timezone

from accounts.models import Equipe, Service, Site, User
from incidents.models import CategorieIncident


class HSETestCase(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.site_casa = Site.objects.create(nom="Usine de Casablanca")
        cls.site_tanger = Site.objects.create(nom="Usine de Tanger")

        cls.service_casa_prod = Service.objects.create(nom="Production", site=cls.site_casa)
        cls.service_tanger_prod = Service.objects.create(nom="Production", site=cls.site_tanger)

        cls.categorie = CategorieIncident.objects.create(nom="Chute", domaine=CategorieIncident.Domaine.SECURITE)

        cls.employe_casa = User.objects.create_user(
            'employe_casa', password='pass12345', role=User.Role.EMPLOYE, service=cls.service_casa_prod
        )
        cls.employe_tanger = User.objects.create_user(
            'employe_tanger', password='pass12345', role=User.Role.EMPLOYE, service=cls.service_tanger_prod
        )
        cls.hse = User.objects.create_user(
            'hse1', password='pass12345', role=User.Role.RESPONSABLE_HSE, service=cls.service_casa_prod
        )
        cls.technicien = User.objects.create_user(
            'tech1', password='pass12345', role=User.Role.TECHNICIEN, service=cls.service_casa_prod
        )
        cls.admin = User.objects.create_user(
            'admin1', password='pass12345', role=User.Role.ADMIN, service=cls.service_casa_prod, is_staff=True
        )
        cls.direction = User.objects.create_user(
            'direction1', password='pass12345', role=User.Role.DIRECTION, service=cls.service_casa_prod
        )

        cls.equipe = Equipe.objects.create(nom="Equipe Securite", site=cls.site_casa, responsable=cls.hse)
        cls.equipe.membres.add(cls.technicien)

    def donnees_incident_minimales(self, site=None):
        return {
            'titre': 'Chute dans l\'atelier',
            'description': 'Un operateur a glisse sur une flaque d\'huile.',
            'date_evenement': timezone.now(),
            'site': site or self.site_casa,
            'categorie': self.categorie,
            'gravite': 2,
        }
