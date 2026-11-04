from django.contrib import admin
from .models import (
    Incident, CategorieIncident, ActionCorrective,
    Commentaire, PieceJointe, HistoriqueAction, Notification,
)


class ActionCorrectiveInline(admin.TabularInline):
    model = ActionCorrective
    extra = 0


class CommentaireInline(admin.TabularInline):
    model = Commentaire
    extra = 0
    readonly_fields = ('auteur', 'cree_le')


class PieceJointeInline(admin.TabularInline):
    model = PieceJointe
    extra = 0


@admin.register(Incident)
class IncidentAdmin(admin.ModelAdmin):
    list_display = ('reference', 'titre', 'categorie', 'gravite', 'priorite', 'statut', 'declarant', 'cree_le')
    list_filter = ('statut', 'gravite', 'priorite', 'categorie', 'site')
    search_fields = ('reference', 'titre', 'description')
    readonly_fields = ('reference', 'cree_le', 'modifie_le', 'cloture_le')
    inlines = [ActionCorrectiveInline, CommentaireInline, PieceJointeInline]
    date_hierarchy = 'cree_le'


@admin.register(CategorieIncident)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ('nom', 'domaine', 'actif')
    list_filter = ('domaine', 'actif')


@admin.register(HistoriqueAction)
class HistoriqueAdmin(admin.ModelAdmin):
    list_display = ('horodatage', 'incident', 'action', 'utilisateur')
    list_filter = ('action',)
    readonly_fields = ('incident', 'utilisateur', 'action', 'ancien_valeur', 'nouvelle_valeur', 'horodatage')


admin.site.register(ActionCorrective)
admin.site.register(Notification)
