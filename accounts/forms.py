from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import Service, User


def _services_par_site():
    return Service.objects.select_related('site').order_by('site__nom', 'nom')


class UtilisateurCreationForm(UserCreationForm):
    """
    Creation d'un compte directement depuis l'application (section 6.1 :
    "Creation, modification et desactivation de comptes"), pour eviter a
    l'administrateur de devoir passer par l'interface technique /admin/.
    """
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'role', 'service', 'telephone']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service'].required = False
        self.fields['service'].queryset = _services_par_site()


class UtilisateurUpdateForm(forms.ModelForm):
    """Modification d'un compte existant (role, service, statut actif)."""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'role', 'service', 'telephone', 'is_active']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['service'].queryset = _services_par_site()
