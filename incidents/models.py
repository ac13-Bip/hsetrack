from django.db import models
from django.conf import settings
from django.utils import timezone


class CategorieIncident(models.Model):
    """Categorie/type d'incident (ex: Chute, Incendie, Pollution...)."""

    class Domaine(models.TextChoices):
        HYGIENE = 'HYGIENE', 'Hygiene'
        SECURITE = 'SECURITE', 'Securite'
        ENVIRONNEMENT = 'ENVIRONNEMENT', 'Environnement'

    nom = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    domaine = models.CharField(max_length=20, choices=Domaine.choices, default=Domaine.SECURITE)
    actif = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Categorie d'incident"
        verbose_name_plural = "Categories d'incidents"
        ordering = ['domaine', 'nom']

    def __str__(self):
        return f"[{self.get_domaine_display()}] {self.nom}"


class Incident(models.Model):
    """Modele central : un evenement HSE declare, qualifie, traite puis cloture."""

    class Gravite(models.IntegerChoices):
        FAIBLE = 1, 'Faible'
        MODEREE = 2, 'Moderee'
        IMPORTANTE = 3, 'Importante'
        CRITIQUE = 4, 'Critique'

    class Priorite(models.IntegerChoices):
        BASSE = 1, 'Basse'
        NORMALE = 2, 'Normale'
        HAUTE = 3, 'Haute'
        URGENTE = 4, 'Urgente'

    class Statut(models.TextChoices):
        DECLARE = 'DECLARE', 'Declare'
        EN_ANALYSE = 'EN_ANALYSE', 'En analyse'
        AFFECTE = 'AFFECTE', 'Affecte'
        EN_TRAITEMENT = 'EN_TRAITEMENT', 'En traitement'
        RESOLU = 'RESOLU', 'Resolu'
        CLOTURE = 'CLOTURE', 'Cloture'

    STATUTS_OUVERTS = [Statut.DECLARE, Statut.EN_ANALYSE, Statut.AFFECTE, Statut.EN_TRAITEMENT]
    STATUTS_A_QUALIFIER = [Statut.DECLARE, Statut.EN_ANALYSE]
    STATUTS_TERMINES = [Statut.RESOLU, Statut.CLOTURE]

    reference = models.CharField(max_length=20, unique=True, editable=False, help_text="Generee automatiquement")
    titre = models.CharField(max_length=200)
    description = models.TextField(
        help_text="Decrivez les circonstances, ce qui s'est passe, les consequences observees"
    )

    date_evenement = models.DateTimeField(
        verbose_name="Date et heure de l'incident", help_text="Quand l'incident s'est-il produit ?"
    )
    site = models.ForeignKey('accounts.Site', on_delete=models.PROTECT, related_name='incidents')
    service = models.ForeignKey(
        'accounts.Service', on_delete=models.PROTECT, related_name='incidents', null=True, blank=True
    )
    lieu_precis = models.CharField(max_length=200, blank=True, help_text="Ex : Atelier 3, ligne d'assemblage B")

    categorie = models.ForeignKey(CategorieIncident, on_delete=models.PROTECT, related_name='incidents')
    gravite = models.IntegerField(choices=Gravite.choices, default=Gravite.MODEREE, verbose_name="Niveau de gravite")
    priorite = models.IntegerField(choices=Priorite.choices, default=Priorite.NORMALE, verbose_name="Niveau de priorite")

    statut = models.CharField(max_length=20, choices=Statut.choices, default=Statut.DECLARE)

    declarant = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='incidents_declares'
    )
    affecte_a = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='incidents_a_traiter', verbose_name="Affecte a (personne)"
    )
    equipe_affectee = models.ForeignKey(
        'accounts.Equipe', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='incidents_affectes', verbose_name="Affecte a (equipe)"
    )
    echeance = models.DateField(null=True, blank=True, help_text="Date limite de traitement")

    cree_le = models.DateTimeField(auto_now_add=True)
    modifie_le = models.DateTimeField(auto_now=True)
    cloture_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Incident"
        ordering = ['-cree_le']
        indexes = [
            models.Index(fields=['statut']),
            models.Index(fields=['gravite']),
            models.Index(fields=['-cree_le']),
        ]

    def __str__(self):
        return f"{self.reference} - {self.titre}"

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self._prochaine_reference()
        super().save(*args, **kwargs)

    @classmethod
    def _prochaine_reference(cls):
        """
        INC-<annee>-<numero> : numero = plus grand numero de l'annee + 1.
        Base sur le maximum (et non sur un comptage) pour ne jamais
        reattribuer une reference apres suppression d'un incident. Le
        numero etant sur 5 chiffres, l'ordre alphabetique suffit.
        """
        prefixe = f"INC-{timezone.now().year}-"
        derniere = (
            cls.objects.filter(reference__startswith=prefixe)
            .order_by('-reference').values_list('reference', flat=True).first()
        )
        numero = int(derniere.rsplit('-', 1)[1]) + 1 if derniere else 1
        return f"{prefixe}{numero:05d}"

    def est_critique(self):
        return self.gravite == self.Gravite.CRITIQUE

    def est_cloture(self):
        return self.statut == self.Statut.CLOTURE

    def est_en_retard(self):
        if not self.echeance or self.statut in self.STATUTS_TERMINES:
            return False
        return self.echeance < timezone.now().date()

    def delai_traitement_jours(self):
        if self.cloture_le:
            return (self.cloture_le - self.cree_le).days
        return None


class ActionCorrective(models.Model):
    """Action corrective ou preventive liee a un incident, affectee a un technicien."""

    class Type(models.TextChoices):
        CORRECTIVE = 'CORRECTIVE', 'Action corrective'
        PREVENTIVE = 'PREVENTIVE', 'Action preventive'

    class StatutAction(models.TextChoices):
        A_FAIRE = 'A_FAIRE', 'A faire'
        EN_COURS = 'EN_COURS', 'En cours'
        TERMINEE = 'TERMINEE', 'Terminee'
        ANNULEE = 'ANNULEE', 'Annulee'

    STATUTS_ACTIFS = [StatutAction.A_FAIRE, StatutAction.EN_COURS]

    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='actions')
    type_action = models.CharField(max_length=15, choices=Type.choices, default=Type.CORRECTIVE)
    description = models.TextField()
    responsable = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='actions_assignees'
    )
    echeance = models.DateField()
    statut = models.CharField(max_length=15, choices=StatutAction.choices, default=StatutAction.A_FAIRE)
    commentaire_realisation = models.TextField(blank=True, verbose_name="Compte rendu de realisation")

    cree_le = models.DateTimeField(auto_now_add=True)
    termine_le = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Action corrective/preventive"
        ordering = ['echeance']

    def __str__(self):
        return f"{self.get_type_action_display()} - {self.description[:50]}"

    def est_en_retard(self):
        if self.statut not in self.STATUTS_ACTIFS:
            return False
        return self.echeance < timezone.now().date()


class Commentaire(models.Model):
    """Commentaire libre sur un incident (echanges, comptes rendus)."""
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='commentaires')
    auteur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    contenu = models.TextField()
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['cree_le']

    def __str__(self):
        return f"Commentaire de {self.auteur} sur {self.incident.reference}"


def chemin_piece_jointe(instance, filename):
    """media/incidents/INC-2026-00001/photo.jpg : un dossier par incident."""
    return f'incidents/{instance.incident.reference}/{filename}'


class PieceJointe(models.Model):
    """Photo, document ou constat lie a un incident."""
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='pieces_jointes')
    fichier = models.FileField(upload_to=chemin_piece_jointe)
    nom_original = models.CharField(max_length=255)
    uploade_par = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    uploade_le = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom_original


class HistoriqueAction(models.Model):
    """
    Journal automatique de toutes les modifications significatives d'un
    incident (statut, gravite, priorite, affectation, echeance, categorie).
    Alimente par les signals (cf. signals.py) : aucune saisie manuelle.
    """
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, related_name='historique')
    utilisateur = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    action = models.CharField(max_length=100)
    ancien_valeur = models.CharField(max_length=200, blank=True)
    nouvelle_valeur = models.CharField(max_length=200, blank=True)
    horodatage = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-horodatage']
        verbose_name = "Entree d'historique"

    def __str__(self):
        return f"{self.horodatage:%d/%m/%Y %H:%M} - {self.action}"


class Notification(models.Model):
    """Notification adressee a un utilisateur, liee ou non a un incident."""

    class Niveau(models.TextChoices):
        INFO = 'INFO', 'Information'
        ALERTE = 'ALERTE', 'Alerte critique'

    destinataire = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='notifications')
    incident = models.ForeignKey(Incident, on_delete=models.CASCADE, null=True, blank=True)
    niveau = models.CharField(max_length=10, choices=Niveau.choices, default=Niveau.INFO)
    message = models.CharField(max_length=300)
    lue = models.BooleanField(default=False)
    cree_le = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-cree_le']

    def __str__(self):
        return f"Notif pour {self.destinataire}: {self.message[:50]}"
