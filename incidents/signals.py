"""
Tracabilite automatique (section 7 : "Toute modification significative
doit etre historisee"). Implementee en signals plutot que dans les vues
ou la couche service : ainsi AUCUNE modification d'incident ne peut
echapper a l'historisation, qu'elle vienne d'une vue, d'une commande ou
de l'admin Django.
"""
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from accounts.models import User

from .models import HistoriqueAction, Incident, Notification

_etat_avant = {}

CHAMPS_SUIVIS = {
    'statut': 'Statut',
    'gravite': 'Gravite',
    'priorite': 'Priorite',
    'affecte_a': 'Affectation (personne)',
    'equipe_affectee': 'Affectation (equipe)',
    'echeance': 'Echeance',
    'categorie': 'Categorie',
}


def _responsables_hse_actifs():
    return User.objects.filter(role=User.Role.RESPONSABLE_HSE, is_active=True)


def _valeur_lisible(incident, champ):
    valeur = getattr(incident, champ, None)
    if valeur is None:
        return ""
    methode_display = getattr(incident, f"get_{champ}_display", None)
    return str(methode_display()) if methode_display else str(valeur)


@receiver(pre_save, sender=Incident)
def memoriser_etat_avant(sender, instance, **kwargs):
    if instance.pk:
        try:
            ancien = Incident.objects.get(pk=instance.pk)
            _etat_avant[instance.pk] = {c: _valeur_lisible(ancien, c) for c in CHAMPS_SUIVIS}
        except Incident.DoesNotExist:
            pass


@receiver(post_save, sender=Incident)
def historiser_changements(sender, instance, created, **kwargs):
    utilisateur = getattr(instance, '_utilisateur_courant', None)

    if created:
        HistoriqueAction.objects.create(
            incident=instance, utilisateur=instance.declarant,
            action="Declaration de l'incident", nouvelle_valeur=instance.get_statut_display()
        )
        _notifier_nouvelle_declaration(instance)
        return

    ancien_etat = _etat_avant.pop(instance.pk, None)
    if not ancien_etat:
        return

    a_change = False
    for champ, libelle in CHAMPS_SUIVIS.items():
        ancienne = ancien_etat.get(champ, "")
        nouvelle = _valeur_lisible(instance, champ)
        if ancienne != nouvelle:
            a_change = True
            HistoriqueAction.objects.create(
                incident=instance, utilisateur=utilisateur, action=f"Modification : {libelle}",
                ancien_valeur=ancienne or "(vide)", nouvelle_valeur=nouvelle or "(vide)",
            )

            if champ == 'statut' and instance.statut == Incident.Statut.CLOTURE and not instance.cloture_le:
                Incident.objects.filter(pk=instance.pk).update(cloture_le=timezone.now())

            if champ == 'affecte_a' and instance.affecte_a:
                Notification.objects.create(
                    destinataire=instance.affecte_a, incident=instance, niveau=Notification.Niveau.INFO,
                    message=f"Un incident vous a ete affecte : {instance.titre} ({instance.reference})",
                )

    if a_change and instance.est_critique():
        _notifier_incidents_critiques(instance)


def _notifier_nouvelle_declaration(incident):
    """
    Le responsable HSE doit TOUJOURS savoir qu'un nouvel incident attend
    sa qualification (section 6.3) : une notification est systematiquement
    envoyee a la declaration, avec un niveau ALERTE si l'incident est
    deja critique, INFO sinon.
    """
    if incident.est_critique():
        _notifier_incidents_critiques(incident)
        return

    for resp in _responsables_hse_actifs():
        Notification.objects.create(
            destinataire=resp, incident=incident, niveau=Notification.Niveau.INFO,
            message=f"Nouvel incident declare : {incident.titre} ({incident.reference}) - a qualifier.",
        )


def _notifier_incidents_critiques(incident):
    """Alerte immediate des responsables HSE pour un incident critique (regle de gestion section 7)."""
    for resp in _responsables_hse_actifs():
        deja_alerte = Notification.objects.filter(
            destinataire=resp, incident=incident, message__startswith="INCIDENT CRITIQUE"
        ).exists()
        if not deja_alerte:
            Notification.objects.create(
                destinataire=resp, incident=incident, niveau=Notification.Niveau.ALERTE,
                message=f"INCIDENT CRITIQUE : {incident.titre} ({incident.reference})",
            )
