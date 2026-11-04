from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AdminPasswordChangeForm
from django.shortcuts import get_object_or_404, redirect, render

from .forms import UtilisateurCreationForm, UtilisateurUpdateForm
from .models import Site, User


def administrateur_requis(vue):
    """
    Reserve une vue aux utilisateurs habilites a administrer la plateforme
    (section 5 : role Administrateur). Les autres sont renvoyes vers le
    tableau de bord avec un message explicite.
    """
    @wraps(vue)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not request.user.peut_administrer():
            messages.error(request, "Action reservee a l'administrateur.")
            return redirect('dashboard:index')
        return vue(request, *args, **kwargs)
    return wrapper


@login_required
def profile_view(request):
    return render(request, 'accounts/profile.html', {'user': request.user})


@administrateur_requis
def gestion_utilisateurs(request):
    """Vue d'administration des comptes et referentiels (section 6.1)."""
    if request.method == 'POST' and 'toggle_user' in request.POST:
        cible = get_object_or_404(User, pk=request.POST.get('user_id'))
        if cible != request.user:
            cible.is_active = not cible.is_active
            cible.save(update_fields=['is_active'])
            etat = "active" if cible.is_active else "desactive"
            messages.success(request, f"Compte {cible.get_full_name() or cible.username} {etat}.")
        return redirect('accounts:gestion_utilisateurs')

    contexte = {
        'utilisateurs': User.objects.select_related('service__site').order_by('last_name', 'first_name'),
        'sites': Site.objects.prefetch_related('services').filter(actif=True),
        'roles': User.Role.choices,
    }
    return render(request, 'accounts/gestion_utilisateurs.html', contexte)


@administrateur_requis
def creer_utilisateur(request):
    """Creation d'un compte directement depuis l'application."""
    if request.method == 'POST':
        form = UtilisateurCreationForm(request.POST)
        if form.is_valid():
            utilisateur = form.save()
            messages.success(request, f"Compte {utilisateur.username} cree avec succes.")
            return redirect('accounts:gestion_utilisateurs')
    else:
        form = UtilisateurCreationForm()

    return render(request, 'accounts/utilisateur_form.html', {'form': form, 'mode': 'creation'})


@administrateur_requis
def modifier_utilisateur(request, pk):
    """Modification d'un compte existant (role, service, statut)."""
    utilisateur = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = UtilisateurUpdateForm(request.POST, instance=utilisateur)
        if form.is_valid():
            form.save()
            messages.success(request, f"Compte {utilisateur.username} mis a jour.")
            return redirect('accounts:gestion_utilisateurs')
    else:
        form = UtilisateurUpdateForm(instance=utilisateur)

    return render(request, 'accounts/utilisateur_form.html', {
        'form': form, 'mode': 'modification', 'utilisateur': utilisateur,
    })


@administrateur_requis
def reinitialiser_mot_de_passe(request, pk):
    """Reinitialisation du mot de passe d'un utilisateur par l'administrateur."""
    utilisateur = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        form = AdminPasswordChangeForm(utilisateur, request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, f"Mot de passe de {utilisateur.username} reinitialise.")
            return redirect('accounts:gestion_utilisateurs')
    else:
        form = AdminPasswordChangeForm(utilisateur)

    return render(request, 'accounts/utilisateur_form.html', {
        'form': form, 'mode': 'mot_de_passe', 'utilisateur': utilisateur,
    })
