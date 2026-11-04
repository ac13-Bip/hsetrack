"""
Tableau de bord (section 6.5). La page d'accueil s'adapte au role pour
rester utile sans surcharger l'utilisateur : chacun voit en priorite ce
qui demande SON action (declarer, qualifier, traiter), pas une liste
brute d'incidents.
"""
import json
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, DurationField, ExpressionWrapper, F
from django.db.models.functions import TruncMonth
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils import timezone

from incidents.models import ActionCorrective, Incident
from incidents.permissions import incidents_visibles

Statut = Incident.Statut


def _actions_en_retard(incidents):
    """Actions non terminees dont l'echeance est depassee, sur les incidents donnes."""
    return ActionCorrective.objects.filter(
        incident__in=incidents,
        echeance__lt=timezone.now().date(),
        statut__in=ActionCorrective.STATUTS_ACTIFS,
    )


def _repartition(queryset, champ, libelles=None):
    """[{champ: valeur, 'total': n}, ...] ; ajoute 'libelle' si un dict de libelles est fourni."""
    lignes = list(queryset.values(champ).annotate(total=Count('id')).order_by(champ if libelles else '-total'))
    if libelles is not None:
        for ligne in lignes:
            ligne['libelle'] = libelles.get(ligne[champ], 'Inconnu')
    return lignes


@login_required
def index(request):
    user = request.user
    base_qs = incidents_visibles(user)

    ouverts = base_qs.filter(statut__in=Incident.STATUTS_OUVERTS)
    contexte = {
        'total': base_qs.count(),
        'ouverts': ouverts.count(),
        'critiques_ouverts': ouverts.filter(gravite=Incident.Gravite.CRITIQUE).count(),
        'clotures': base_qs.filter(statut=Statut.CLOTURE).count(),
        'recents': base_qs.filter(cree_le__gte=timezone.now() - timedelta(days=30)).count(),
        'derniers_incidents': base_qs.select_related('categorie', 'site', 'declarant').order_by('-cree_le')[:5],
    }

    # ===== Files de travail specifiques au role (priorite : facilite d'usage) =====
    if user.peut_gerer_incidents():
        contexte['a_qualifier'] = base_qs.filter(
            statut__in=Incident.STATUTS_A_QUALIFIER
        ).select_related('categorie', 'site').order_by('-cree_le')[:5]
        contexte['actions_en_retard'] = _actions_en_retard(base_qs).select_related('incident', 'responsable')[:5]

    if user.est_technicien():
        contexte['mes_actions'] = ActionCorrective.objects.filter(
            responsable=user, statut__in=ActionCorrective.STATUTS_ACTIFS,
        ).select_related('incident').order_by('echeance')[:8]

    # ===== Graphiques (uniquement utiles si plusieurs incidents) =====
    repartition_statut = _repartition(base_qs, 'statut', dict(Statut.choices))
    contexte['repartition_statut_json'] = json.dumps(repartition_statut)

    return render(request, 'dashboard/index.html', contexte)


@login_required
def statistiques(request):
    """Reporting avance (section 6.5) : reserve a la supervision globale."""
    if not request.user.a_acces_global():
        return HttpResponseForbidden("Acces reserve a la direction et aux responsables HSE.")

    base_qs = Incident.objects.all()

    par_service = _repartition(base_qs, 'service__nom')
    par_site = _repartition(base_qs, 'site__nom')
    par_categorie = _repartition(base_qs, 'categorie__nom')
    par_gravite = _repartition(base_qs, 'gravite', dict(Incident.Gravite.choices))

    par_mois_qs = base_qs.annotate(mois=TruncMonth('cree_le')).values('mois').annotate(total=Count('id')).order_by('mois')
    par_mois_json = [{'mois': i['mois'].strftime('%b %Y') if i['mois'] else '', 'total': i['total']} for i in par_mois_qs]

    delai_moyen = base_qs.filter(statut=Statut.CLOTURE, cloture_le__isnull=False).annotate(
        duree=ExpressionWrapper(F('cloture_le') - F('cree_le'), output_field=DurationField())
    ).aggregate(moyenne=Avg('duree'))['moyenne']

    return render(request, 'dashboard/statistiques.html', {
        'total': base_qs.count(),
        'ouverts': base_qs.filter(statut__in=Incident.STATUTS_OUVERTS).count(),
        'resolus': base_qs.filter(statut=Statut.RESOLU).count(),
        'clotures': base_qs.filter(statut=Statut.CLOTURE).count(),
        'delai_moyen_jours': delai_moyen.days if delai_moyen else 0,
        'actions_en_retard': _actions_en_retard(base_qs).count(),
        'par_service': par_service,
        'par_site': par_site,
        'par_categorie': par_categorie,
        'par_service_json': json.dumps(par_service),
        'par_site_json': json.dumps(par_site),
        'par_categorie_json': json.dumps(par_categorie),
        'par_gravite_json': json.dumps(par_gravite),
        'par_mois_json': json.dumps(par_mois_json),
    })
