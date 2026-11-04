"""
Vues de l'app incidents. Volontairement minces : la decision metier vit
dans services.py (transitions d'etat) et permissions.py (visibilite),
les vues se contentent de valider la requete/le formulaire et d'appeler
ces deux modules. Les controles d'acces par role affichent un message
clair (messages.error + redirect) plutot qu'une redirection silencieuse
vers la page de connexion.
"""
import json
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from accounts.models import Equipe, User
from intelligence.similarity_detector import recommander_actions, trouver_similaires

from . import services
from .forms import ActionCorrectiveForm, CommentaireForm, IncidentForm, IncidentQualificationForm
from .models import ActionCorrective, Incident, Notification
from .permissions import incidents_visibles, peut_voir_incident
from .services import ActionNonAutorisee


def gestion_incidents_requise(vue):
    """
    Reserve une vue d'incident (`pk` dans l'URL) au responsable HSE et a
    l'administrateur. Les autres roles sont renvoyes vers le detail de
    l'incident avec un message explicite.
    """
    @wraps(vue)
    @login_required
    def wrapper(request, pk, *args, **kwargs):
        if not request.user.peut_gerer_incidents():
            messages.error(request, "Action reservee au responsable HSE et a l'administrateur.")
            return redirect('incidents:detail', pk=pk)
        return vue(request, pk, *args, **kwargs)
    return wrapper


# ============================================================
# LISTE DES INCIDENTS
# ============================================================
@login_required
def liste_incidents(request):
    """Liste paginee et filtrable, scopee par role (section 7)."""
    queryset = incidents_visibles(request.user).select_related(
        'site', 'service', 'categorie', 'declarant', 'affecte_a'
    )

    statut = request.GET.get('statut')
    gravite = request.GET.get('gravite')
    recherche = request.GET.get('q')

    if statut:
        queryset = queryset.filter(statut=statut)
    else:
        # Par defaut, la rubrique "Incidents" ne montre que les incidents en
        # cours : les clotures ont leur propre rubrique dediee
        # (incidents:clotures) pour eviter de les afficher deux fois.
        queryset = queryset.exclude(statut=Incident.Statut.CLOTURE)
    if gravite:
        queryset = queryset.filter(gravite=gravite)
    if recherche:
        queryset = queryset.filter(
            Q(titre__icontains=recherche) | Q(description__icontains=recherche) | Q(reference__icontains=recherche)
        )

    page_obj = Paginator(queryset, 20).get_page(request.GET.get('page'))

    return render(request, 'incidents/liste.html', {
        'page_obj': page_obj,
        'statuts': Incident.Statut.choices,
        'gravites': Incident.Gravite.choices,
        'filtres_actifs': {'statut': statut, 'gravite': gravite, 'q': recherche},
    })


# ============================================================
# DECLARATION D'UN INCIDENT
# ============================================================
@login_required
def declarer_incident(request):
    """Pattern Post-Redirect-Get (section 6.2)."""
    if request.method == 'POST':
        form = IncidentForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            incident = services.declarer_incident(
                incident=form.save(commit=False),
                declarant=request.user,
                fichiers=request.FILES.getlist('pieces_jointes'),
            )
            messages.success(
                request,
                f"Incident {incident.reference} declare avec succes. "
                f"Priorite suggeree par l'IA : {incident.get_priorite_display()}",
            )
            return redirect('incidents:detail', pk=incident.pk)
    else:
        form = IncidentForm(user=request.user)

    return render(request, 'incidents/declarer.html', {'form': form})


# ============================================================
# DETAIL D'UN INCIDENT
# ============================================================
@login_required
def detail_incident(request, pk):
    incident = get_object_or_404(
        Incident.objects.select_related('site', 'service', 'categorie', 'declarant', 'affecte_a'), pk=pk
    )

    if not peut_voir_incident(request.user, incident):
        messages.error(request, "Vous n'avez pas acces a cet incident.")
        return redirect('incidents:liste')

    if request.method == 'POST' and 'ajouter_commentaire' in request.POST:
        if incident.est_cloture():
            messages.error(request, "Incident cloture : ajout de commentaire impossible (lecture seule).")
            return redirect('incidents:detail', pk=pk)
        comm_form = CommentaireForm(request.POST)
        if comm_form.is_valid():
            commentaire = comm_form.save(commit=False)
            commentaire.incident = incident
            commentaire.auteur = request.user
            commentaire.save()
            messages.success(request, "Commentaire ajoute.")
            return redirect('incidents:detail', pk=pk)
    else:
        comm_form = CommentaireForm()

    return render(request, 'incidents/detail.html', {
        'incident': incident,
        'comm_form': comm_form,
        'actions': incident.actions.select_related('responsable').all(),
        'commentaires': incident.commentaires.select_related('auteur').all(),
        'pieces_jointes': incident.pieces_jointes.all(),
        'historique': incident.historique.select_related('utilisateur').all(),
        'incidents_similaires': trouver_similaires(incident, k=3),
        'actions_recommandees': recommander_actions(incident, k=3),
        'lecture_seule': incident.est_cloture(),
    })


# ============================================================
# QUALIFICATION (reservee HSE/Admin)
# ============================================================
@gestion_incidents_requise
def qualifier_incident(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    if incident.est_cloture():
        messages.error(request, "Incident cloture : modification impossible (lecture seule).")
        return redirect('incidents:detail', pk=pk)

    if request.method == 'POST':
        form = IncidentQualificationForm(request.POST, instance=incident)
        if form.is_valid():
            incident_modifie = form.save(commit=False)
            incident_modifie._utilisateur_courant = request.user
            incident_modifie.save()
            messages.success(request, "Incident qualifie avec succes.")
            return redirect('incidents:detail', pk=pk)
    else:
        form = IncidentQualificationForm(instance=incident)

    return render(request, 'incidents/qualifier.html', {'form': form, 'incident': incident})


# ============================================================
# AJOUTER UNE ACTION CORRECTIVE/PREVENTIVE (reservee HSE/Admin)
# ============================================================
@gestion_incidents_requise
def ajouter_action(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    if incident.est_cloture():
        messages.error(request, "Incident cloture : ajout d'action impossible (lecture seule).")
        return redirect('incidents:detail', pk=pk)

    if request.method == 'POST':
        form = ActionCorrectiveForm(request.POST)
        if form.is_valid():
            services.ajouter_action(incident=incident, action=form.save(commit=False), cree_par=request.user)
            messages.success(request, "Action ajoutee, le responsable a ete notifie.")
            return redirect('incidents:detail', pk=pk)
    else:
        form = ActionCorrectiveForm()

    # Correspondance equipe -> techniciens actifs, utilisee par le JS du
    # formulaire pour filtrer la liste des responsables selon l'equipe.
    equipes_techniciens = {
        str(equipe.pk): list(
            equipe.membres.filter(role=User.Role.TECHNICIEN, is_active=True).values_list('pk', flat=True)
        )
        for equipe in Equipe.objects.filter(actif=True)
    }

    return render(request, 'incidents/action_form.html', {
        'form': form, 'incident': incident, 'equipes_techniciens_json': json.dumps(equipes_techniciens),
        'recommandations': recommander_actions(incident, k=3),
    })


# ============================================================
# SUIVI D'UNE ACTION PAR SON RESPONSABLE (technicien)
# ============================================================
@require_POST
@login_required
def demarrer_action(request, pk):
    action = get_object_or_404(ActionCorrective, pk=pk)
    try:
        services.demarrer_action(action=action, utilisateur=request.user)
    except ActionNonAutorisee as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Action demarree : l'incident passe en traitement.")
    return redirect('incidents:detail', pk=action.incident_id)


@require_POST
@login_required
def terminer_action(request, pk):
    action = get_object_or_404(ActionCorrective, pk=pk)
    try:
        _, incident_resolu = services.terminer_action(
            action=action, utilisateur=request.user,
            commentaire_realisation=request.POST.get('commentaire_realisation', ''),
        )
    except ActionNonAutorisee as exc:
        messages.error(request, str(exc))
        return redirect('incidents:detail', pk=action.incident_id)

    if incident_resolu:
        messages.success(request, "Action terminee : toutes les actions sont realisees, l'incident est resolu.")
    else:
        messages.success(request, "Action terminee. D'autres actions restent en cours sur cet incident.")
    return redirect('incidents:detail', pk=action.incident_id)


# ============================================================
# CLOTURER UN INCIDENT (reservee HSE/Admin)
# ============================================================
@require_POST
@gestion_incidents_requise
def cloturer_incident(request, pk):
    incident = get_object_or_404(Incident, pk=pk)
    _, vient_de_cloturer = services.cloturer_incident(incident=incident, utilisateur=request.user)
    if vient_de_cloturer:
        messages.success(request, f"Incident {incident.reference} cloture.")
    else:
        messages.info(request, "Cet incident est deja cloture.")
    return redirect('incidents:detail', pk=pk)


# ============================================================
# INCIDENTS CLOTURES
# - HSE/Admin/Direction : historique complet, tous sites confondus.
# - Autres roles : uniquement les incidents qu'il a lui-meme declares, et
#   seulement s'ils sont rattaches a son site actuel (un employe ayant
#   change de site/service ne doit plus voir l'historique de l'ancien).
# ============================================================
@login_required
def incidents_clotures(request):
    queryset = Incident.objects.filter(statut=Incident.Statut.CLOTURE)

    if not request.user.a_acces_global():
        if not request.user.service_id:
            queryset = queryset.none()
        else:
            queryset = queryset.filter(declarant=request.user, site=request.user.service.site)

    incidents = queryset.select_related(
        'site', 'service', 'categorie', 'declarant', 'affecte_a'
    ).order_by('-cloture_le')
    return render(request, 'incidents/clotures.html', {'incidents': incidents})


# ============================================================
# NOTIFICATIONS
# ============================================================
@login_required
def liste_notifications(request):
    notifs = Notification.objects.filter(destinataire=request.user)
    return render(request, 'incidents/notifications.html', {'notifications': notifs})


@login_required
def marquer_notification_lue(request, pk):
    notif = get_object_or_404(Notification, pk=pk, destinataire=request.user)
    notif.lue = True
    notif.save()
    if notif.incident_id:
        return redirect('incidents:detail', pk=notif.incident_id)
    return redirect('incidents:notifications')


@require_POST
@login_required
def marquer_toutes_lues(request):
    Notification.objects.filter(destinataire=request.user, lue=False).update(lue=True)
    messages.success(request, "Toutes les notifications ont ete marquees comme lues.")
    return redirect('incidents:notifications')
