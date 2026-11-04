from django.db import models
from django.contrib.auth.models import AbstractUser


class Site(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    adresse = models.TextField(blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Site"
        ordering = ['nom']

    def __str__(self):
        return self.nom


class Service(models.Model):
    nom = models.CharField(max_length=100)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='services')

    class Meta:
        verbose_name = "Service"
        unique_together = ('nom', 'site')
        ordering = ['site', 'nom']

    def __str__(self):
        return f"{self.nom} ({self.site.nom})"


class User(AbstractUser):
    class Role(models.TextChoices):
        EMPLOYE = 'EMPLOYE', 'Employe / Declarant'
        RESPONSABLE_HSE = 'RESP_HSE', 'Responsable HSE'
        TECHNICIEN = 'TECHNICIEN', 'Responsable operationnel / Technicien'
        ADMIN = 'ADMIN', 'Administrateur'
        DIRECTION = 'DIRECTION', 'Direction / Manager'

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.EMPLOYE, verbose_name="Role")
    service = models.ForeignKey(
        Service, on_delete=models.SET_NULL, null=True, blank=True, related_name='employes'
    )
    telephone = models.CharField(max_length=20, blank=True)

    def est_employe(self):
        return self.role == self.Role.EMPLOYE

    def est_responsable_hse(self):
        return self.role == self.Role.RESPONSABLE_HSE

    def est_technicien(self):
        return self.role == self.Role.TECHNICIEN

    def est_admin_metier(self):
        return self.role == self.Role.ADMIN

    def est_direction(self):
        return self.role == self.Role.DIRECTION

    def a_acces_global(self):
        return self.est_responsable_hse() or self.est_admin_metier() or self.est_direction()

    def peut_gerer_incidents(self):
        return self.est_responsable_hse() or self.est_admin_metier()

    def peut_administrer(self):
        return self.est_admin_metier() or self.is_staff

    @property
    def site(self):
        return self.service.site if self.service_id else None

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"


class Equipe(models.Model):
    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    site = models.ForeignKey(Site, on_delete=models.CASCADE, related_name='equipes', null=True, blank=True)
    responsable = models.ForeignKey(
        'User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='equipes_dirigees', verbose_name="Responsable de l'equipe"
    )
    membres = models.ManyToManyField('User', related_name='equipes', blank=True)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Equipe"
        ordering = ['nom']

    def __str__(self):
        return self.nom
