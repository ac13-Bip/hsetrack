"""
Couche service : regles metier de transition d'etat, independantes du
framework web (testables directement, sans client HTTP).

Les vues restent volontairement minces : elles valident la requete/le
formulaire puis deleguent la decision metier ici. Cela permet de tester
le coeur du cahier des charges (section 7, regles de gestion) sans avoir
a simuler des requetes HTTP, et d'eviter de dupliquer ces regles si un
jour une API ou une commande CLI doit les reutiliser.
"""
from django.utils import timezone

from intelligence.priority_predictor import predire_priorite

from .models import ActionCorrective, Incident, Notification, PieceJointe


class ActionNonAutorisee(Exception):
    """Leve quand un utilisateur tente une transition qui ne lui est pas permise."""


def declarer_incident(*, incident, declarant, fichiers=None):
    """
    Finalise la declaration d'un incident (section 6.2) : assigne le
    declarant, suggere une priorite via le module intelligent, attache les
    pieces jointes. `incident` est une instance non sauvegardee
    (form.save(commit=False)).
    """
    incident.declarant = declarant
    incident.save()

    incident.priorite = predire_priorite(incident)
    incident.save()

    for fichier in (fichiers or []):
        PieceJointe.objects.create(
            incident=incident, fichier=fichier, nom_original=fichier.name, uploade_par=declarant
        )
    return incident


def ajouter_action(*, incident, action, cree_par):
    """
    Cree une action corrective/preventive et notifie le technicien designe.
    Regle de gestion : affecter une action a un technicien revient a
    affecter l'incident lui-meme, qui passe donc automatiquement en AFFECTE
    s'il n'avait pas encore ete pris en charge (DECLARE/EN_ANALYSE). Les
    incidents deja plus avances (EN_TRAITEMENT, RESOLU, CLOTURE) ne
    regressent pas.
    """
    action.incident = incident
    action.save()
    Notification.objects.create(
        destinataire=action.responsable,
        incident=incident,
        niveau=Notification.Niveau.INFO,
        message=f"Une action vous a ete affectee : {action.description[:80]} ({incident.reference})",
    )

    if incident.statut in Incident.STATUTS_A_QUALIFIER:
        incident.statut = Incident.Statut.AFFECTE
        incident._utilisateur_courant = cree_par
        incident.save()

    return action


def demarrer_action(*, action, utilisateur):
    """
    Le technicien demarre son action : EN_COURS, et l'incident passe
    automatiquement en EN_TRAITEMENT (sauf s'il est deja resolu/cloture).
    """
    if utilisateur.id != action.responsable_id:
        raise ActionNonAutorisee("Seul le responsable de cette action peut la demarrer.")
    if action.statut != ActionCorrective.StatutAction.A_FAIRE:
        return action  # deja demarree : operation idempotente, pas d'erreur

    action.statut = ActionCorrective.StatutAction.EN_COURS
    action.save()

    incident = action.incident
    if incident.statut not in Incident.STATUTS_TERMINES:
        incident.statut = Incident.Statut.EN_TRAITEMENT
        incident._utilisateur_courant = utilisateur
        incident.save()
    return action


def terminer_action(*, action, utilisateur, commentaire_realisation=''):
    """
    Le technicien termine son action. Regle de gestion : si TOUTES les
    actions de l'incident sont terminees (ou annulees), l'incident passe
    automatiquement en RESOLU sans intervention du HSE.
    """
    if utilisateur.id != action.responsable_id:
        raise ActionNonAutorisee("Seul le responsable de cette action peut la terminer.")
    if action.statut == ActionCorrective.StatutAction.TERMINEE:
        return action, False  # deja terminee

    action.statut = ActionCorrective.StatutAction.TERMINEE
    action.termine_le = timezone.now()
    action.commentaire_realisation = commentaire_realisation.strip()
    action.save()

    incident = action.incident
    toutes_terminees = not incident.actions.filter(statut__in=ActionCorrective.STATUTS_ACTIFS).exists()

    incident_resolu = False
    if toutes_terminees and incident.statut != Incident.Statut.CLOTURE:
        incident.statut = Incident.Statut.RESOLU
        incident._utilisateur_courant = utilisateur
        incident.save()
        incident_resolu = True

    return action, incident_resolu


def cloturer_incident(*, incident, utilisateur):
    """Cloture definitive : reservee au HSE/Admin (verifie par l'appelant)."""
    if incident.est_cloture():
        return incident, False
    incident.statut = Incident.Statut.CLOTURE
    incident._utilisateur_courant = utilisateur
    incident.save()  # le signal enregistre cloture_le automatiquement

    Notification.objects.create(
        destinataire=incident.declarant,
        incident=incident,
        niveau=Notification.Niveau.INFO,
        message=f"Votre incident {incident.reference} a ete cloture.",
    )
    return incident, True
