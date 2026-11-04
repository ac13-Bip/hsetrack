from crispy_forms.helper import FormHelper
from crispy_forms.layout import Column, Fieldset, Layout, Row
from django import forms

from accounts.models import Equipe, Service, Site, User

from .models import ActionCorrective, Commentaire, Incident


def _techniciens_actifs():
    return User.objects.filter(role=User.Role.TECHNICIEN, is_active=True)


class IncidentForm(forms.ModelForm):
    """
    Formulaire de declaration d'un incident (section 6.2). Regroupe par
    blocs logiques (Quand/Ou, Quoi, Classification) pour rester lisible
    malgre le nombre de champs - objectif ergonomie/facilite d'usage.

    Les champs `statut`, `priorite`, `affecte_a` ne sont PAS proposes ici :
    ils relevent de la qualification HSE (section 6.3), pas de la
    declaration initiale.
    """
    class Meta:
        model = Incident
        fields = ['titre', 'description', 'date_evenement', 'site', 'service', 'lieu_precis', 'categorie', 'gravite']
        widgets = {
            'date_evenement': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': "Que s'est-il passe ? Circonstances, consequences observees..."}),
            'titre': forms.TextInput(attrs={'placeholder': 'Resume court de l\'incident'}),
            'lieu_precis': forms.TextInput(attrs={'placeholder': "Ex : Atelier 3, ligne d'assemblage B"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Un employe ne peut declarer que sur SON site (section 7). Le champ
        # est verrouille avec disabled=True : Django ignore alors toute
        # valeur postee et reutilise `initial`, donc impossible a contourner
        # meme en manipulant la requete.
        if user is not None and user.est_employe() and user.service_id:
            site = user.service.site
            self.fields['site'].queryset = Site.objects.filter(pk=site.pk)
            self.fields['site'].initial = site
            self.fields['site'].disabled = True
            self.fields['site'].help_text = "Verrouille sur votre site d'affectation."
            self.fields['service'].queryset = Service.objects.filter(site=site)
            self.fields['service'].initial = user.service

        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Fieldset(
                "Quand et ou ?",
                Row(Column('date_evenement', css_class='col-md-6'), Column('lieu_precis', css_class='col-md-6')),
                Row(Column('site', css_class='col-md-6'), Column('service', css_class='col-md-6')),
            ),
            Fieldset(
                "Que s'est-il passe ?",
                'titre',
                'description',
            ),
            Fieldset(
                "Classification",
                Row(Column('categorie', css_class='col-md-6'), Column('gravite', css_class='col-md-6')),
            ),
        )


class IncidentQualificationForm(forms.ModelForm):
    """Qualification reservee au responsable HSE/Admin (section 6.3)."""
    class Meta:
        model = Incident
        fields = ['categorie', 'gravite', 'priorite', 'affecte_a', 'equipe_affectee', 'echeance', 'statut']
        widgets = {'echeance': forms.DateInput(attrs={'type': 'date'})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Seuls les techniciens actifs peuvent etre designes responsables directs
        self.fields['affecte_a'].queryset = _techniciens_actifs()


class ActionCorrectiveForm(forms.ModelForm):
    """
    Creation d'une action corrective/preventive (reservee HSE/Admin).
    Le champ `equipe` n'existe pas sur le modele : c'est une aide a la
    saisie qui filtre (en JS cote template) la liste des techniciens du
    champ `responsable` selon l'equipe choisie. Jamais sauvegarde.
    """
    equipe = forms.ModelChoiceField(
        queryset=Equipe.objects.filter(actif=True), required=False,
        label="Equipe / Service", help_text="Filtre la liste des techniciens ci-dessous.",
    )

    field_order = ['type_action', 'description', 'equipe', 'responsable', 'echeance']

    class Meta:
        model = ActionCorrective
        fields = ['type_action', 'description', 'responsable', 'echeance']
        widgets = {
            'echeance': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['responsable'].queryset = _techniciens_actifs()


class CommentaireForm(forms.ModelForm):
    class Meta:
        model = Commentaire
        fields = ['contenu']
        widgets = {'contenu': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Votre commentaire...'})}
        labels = {'contenu': ''}
