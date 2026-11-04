from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Site, Service, Equipe


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'role', 'service', 'is_active')
    list_filter = ('role', 'service__site', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')

    fieldsets = UserAdmin.fieldsets + (
        ('Informations HSE', {'fields': ('role', 'service', 'telephone')}),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Informations HSE', {'fields': ('role', 'service', 'telephone')}),
    )


@admin.register(Site)
class SiteAdmin(admin.ModelAdmin):
    list_display = ('nom', 'adresse', 'actif')
    list_filter = ('actif',)
    search_fields = ('nom',)


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('nom', 'site')
    list_filter = ('site',)
    search_fields = ('nom',)


@admin.register(Equipe)
class EquipeAdmin(admin.ModelAdmin):
    list_display = ('nom', 'site', 'responsable', 'actif')
    list_filter = ('site', 'actif')
    search_fields = ('nom',)
    filter_horizontal = ('membres',)


admin.site.site_header = "Administration HSETrack"
admin.site.site_title = "HSETrack Admin"
admin.site.index_title = "Pilotage de la plateforme"
