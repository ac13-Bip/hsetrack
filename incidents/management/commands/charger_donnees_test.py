"""
Commande de chargement de donnees de demonstration.
Usage : python manage.py charger_donnees_test

Cree (cf. _donnees_demo.py pour le detail des donnees) :
- 3 sites (Casablanca, Tanger, Agadir) avec leurs services
- 7 utilisateurs : un employe par site + un par autre role (HSE, technicien,
  admin, direction), tous rattaches au site de Casablanca sauf le 2e et 3e
  employe (Tanger et Agadir)
- 6 categories d'incidents
- 2 equipes (rattachees a Casablanca)
- pour chaque categorie (site de Casablanca) : 2 incidents clotures avec une
  action corrective terminee (texte volontairement proche d'un cas a
  l'autre) + 1 incident declare au vocabulaire similaire, afin que le
  module intelligent (intelligence/similarity_detector.py) ait de la
  matiere pour detecter des incidents similaires et recommander des
  actions deja realisees
- pour employe2 (Tanger) et employe3 (Agadir) : 2 incidents clotures
  declares par chacun sur son site + 1 incident encore en cours, pour
  alimenter la rubrique "Incidents clotures" cote employe sur les sites
  autres que Casablanca
- le superuser admin/admin

Supprime les incidents existants avant de recreer le jeu de demonstration.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Equipe, Service, Site, User
from incidents.models import ActionCorrective, CategorieIncident, Incident

from ._donnees_demo import (
    CATEGORIES, INCIDENTS_AUTRES_SITES, INCIDENTS_CASABLANCA, MOT_DE_PASSE, SITES, UTILISATEURS,
)


class Command(BaseCommand):
    help = "Charge des donnees de demonstration pour la plateforme HSE"

    def handle(self, *args, **options):
        self.stdout.write("Creation des donnees de demonstration...")
        self.maintenant = timezone.now()

        sites, services = self._creer_sites()
        users = self._creer_utilisateurs(services)
        equipe_secu, equipe_maint = self._creer_equipes(sites['casa'], users)
        categories = self._creer_categories()
        equipe_par_domaine = {
            CategorieIncident.Domaine.SECURITE: equipe_secu,
            CategorieIncident.Domaine.ENVIRONNEMENT: equipe_maint,
            CategorieIncident.Domaine.HYGIENE: equipe_maint,
        }

        Incident.objects.all().delete()
        nb_actions_creees = 0

        for nom_categorie, donnees in INCIDENTS_CASABLANCA.items():
            categorie = categories[nom_categorie]
            contexte = {
                'site': sites['casa'], 'service': services['casa', 'Production'],
                'declarant': users['employe1'], 'categorie': categorie,
            }
            for index, cas in enumerate(donnees['cloture']):
                self._creer_incident_cloture(
                    cas, jours=30 + index * 10, technicien=users['tech1'],
                    equipe=equipe_par_domaine.get(categorie.domaine, equipe_maint), **contexte,
                )
                nb_actions_creees += 1
            self._creer_incident_declare(donnees['declare'], **contexte)

        for donnees_site in INCIDENTS_AUTRES_SITES:
            contexte = {
                'site': sites[donnees_site['site']],
                'service': services[donnees_site['site'], donnees_site['service']],
                'declarant': users[donnees_site['employe']],
            }
            for index, cas in enumerate(donnees_site['cloture']):
                self._creer_incident_cloture(
                    cas, jours=20 + index * 10, technicien=users['tech1'],
                    categorie=categories[cas['categorie']], **contexte,
                )
                nb_actions_creees += 1
            cas_declare = donnees_site['declare']
            self._creer_incident_declare(cas_declare, categorie=categories[cas_declare['categorie']], **contexte)

        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser(
                'admin', 'admin@hse.com', 'admin', role=User.Role.ADMIN, first_name='Super', last_name='Admin'
            )
            self.stdout.write(self.style.SUCCESS("Superuser 'admin' / 'admin' cree."))

        self.stdout.write(self.style.SUCCESS(
            f"Donnees creees : {Incident.objects.count()} incidents ({nb_actions_creees} actions terminees), "
            f"{User.objects.count()} utilisateurs, {Site.objects.count()} sites."
        ))
        self.stdout.write(self.style.WARNING(
            f"Mots de passe : admin/admin pour le superuser, {MOT_DE_PASSE} pour les autres."
        ))

    # ------------------------------------------------------------------
    # Referentiels
    # ------------------------------------------------------------------
    def _creer_sites(self):
        """Retourne ({cle: Site}, {(cle, nom_service): Service})."""
        sites, services = {}, {}
        for cle, (nom, adresse, noms_services) in SITES.items():
            site, _ = Site.objects.get_or_create(nom=nom, defaults={'adresse': adresse})
            sites[cle] = site
            for nom_service in noms_services:
                services[cle, nom_service] = Service.objects.get_or_create(nom=nom_service, site=site)[0]
        return sites, services

    def _creer_utilisateurs(self, services):
        users = {}
        for username, role, prenom, nom, cle_site, nom_service in UTILISATEURS:
            user, cree = User.objects.get_or_create(
                username=username,
                defaults={
                    'first_name': prenom, 'last_name': nom, 'email': f'{username}@hse.com',
                    'role': role, 'service': services[cle_site, nom_service],
                },
            )
            if cree:
                user.set_password(MOT_DE_PASSE)
                user.save()
            users[username] = user
        return users

    def _creer_equipes(self, site, users):
        equipe_secu, _ = Equipe.objects.get_or_create(
            nom="Equipe Securite", defaults={'site': site, 'responsable': users['hse1']}
        )
        equipe_maint, _ = Equipe.objects.get_or_create(
            nom="Equipe Maintenance", defaults={'site': site, 'responsable': users['tech1']}
        )
        equipe_secu.membres.add(users['hse1'], users['tech1'])
        equipe_maint.membres.add(users['tech1'])
        return equipe_secu, equipe_maint

    def _creer_categories(self):
        return {
            nom: CategorieIncident.objects.get_or_create(nom=nom, defaults={'domaine': domaine})[0]
            for nom, domaine in CATEGORIES
        }

    # ------------------------------------------------------------------
    # Incidents
    # ------------------------------------------------------------------
    def _il_y_a(self, jours):
        return self.maintenant - timedelta(days=jours)

    def _creer_incident_cloture(self, cas, *, jours, site, service, declarant, categorie, technicien, equipe=None):
        """Incident cloture il y a `jours` jours, avec une action corrective terminee."""
        incident = Incident.objects.create(
            titre=cas['titre'],
            description=cas['description'],
            date_evenement=self._il_y_a(jours),
            site=site,
            service=service,
            categorie=categorie,
            gravite=cas['gravite'],
            priorite=Incident.Priorite.NORMALE,
            statut=Incident.Statut.CLOTURE,
            declarant=declarant,
            affecte_a=technicien,
            equipe_affectee=equipe,
            echeance=self._il_y_a(jours - 7).date(),
        )
        incident.cloture_le = self._il_y_a(jours - 14)
        incident.save(update_fields=['cloture_le'])

        action = ActionCorrective.objects.create(
            incident=incident,
            type_action=ActionCorrective.Type.CORRECTIVE,
            description=cas['action'],
            responsable=technicien,
            echeance=self._il_y_a(jours - 10).date(),
            statut=ActionCorrective.StatutAction.TERMINEE,
            commentaire_realisation="Action realisee et controlee sur site.",
        )
        action.termine_le = self._il_y_a(jours - 12)
        action.save(update_fields=['termine_le'])
        return incident

    def _creer_incident_declare(self, cas, *, site, service, declarant, categorie):
        """Incident declare il y a 2 jours, en attente de qualification."""
        return Incident.objects.create(
            titre=cas['titre'],
            description=cas['description'],
            date_evenement=self._il_y_a(2),
            site=site,
            service=service,
            categorie=categorie,
            gravite=cas['gravite'],
            priorite=Incident.Priorite.NORMALE,
            statut=Incident.Statut.DECLARE,
            declarant=declarant,
        )
