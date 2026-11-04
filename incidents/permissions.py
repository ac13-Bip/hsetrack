"""
Regles d'acces aux incidents par role (section 7 du cahier des charges :
"Un utilisateur n'accede qu'aux informations autorisees selon son role").

Point d'entree UNIQUE pour la visibilite des incidents : la liste, le
detail et le tableau de bord appellent tous incidents_visibles() pour
garantir une regle identique partout (eviter toute incoherence entre
ces ecrans).

REGLES :
- Responsable HSE, Administrateur, Direction : acces a tout, tous sites
  confondus (supervision/reporting global).
- Employe avec un service/site renseigne : voit l'historique complet des
  incidents de SON site (pas seulement ceux qu'il a personnellement
  declares).
- Tout autre cas (Technicien, Employe sans site) : voit les incidents
  qu'il a declares, ceux qui lui sont affectes directement, ceux affectes
  a une equipe dont il est membre, et ceux pour lesquels il est
  responsable d'au moins une action corrective/preventive.
"""
from django.db.models import Q

from .models import Incident


def incidents_visibles(user):
    """QuerySet des incidents que `user` est autorise a voir."""
    if user.a_acces_global():
        return Incident.objects.all()

    if user.est_employe() and user.service_id:
        return Incident.objects.filter(site=user.service.site)

    return Incident.objects.filter(
        Q(declarant=user)
        | Q(affecte_a=user)
        | Q(equipe_affectee__membres=user)
        | Q(actions__responsable=user)
    ).distinct()


def peut_voir_incident(user, incident):
    """Predicat d'acces a UN incident donne, coherent avec incidents_visibles()."""
    return incidents_visibles(user).filter(pk=incident.pk).exists()
