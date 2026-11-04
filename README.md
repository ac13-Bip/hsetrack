# HSETrack v2

Plateforme web de déclaration et de suivi des incidents HSE (Hygiène, Sécurité, Environnement) : déclaration, qualification, actions correctives/préventives, clôture, notifications, tableau de bord et suggestions automatiques (priorité, incidents similaires).

Développée avec Django 5.2 et Bootstrap 5, sans dépendance scientifique : le module « intelligence » est écrit en pur Python.

## Installation

```bash
python -m venv venv
venv\Scripts\activate            # Windows (Linux/macOS : source venv/bin/activate)
pip install -r requirements.txt
python manage.py migrate
python manage.py charger_donnees_test   # optionnel : jeu de démonstration
python manage.py runserver
```

L'application est alors accessible sur http://127.0.0.1:8000/.

> ⚠️ `charger_donnees_test` **supprime tous les incidents existants** avant de recréer le jeu de démonstration.

### Comptes de démonstration

| Identifiant | Rôle | Mot de passe |
|---|---|---|
| `admin` | Superutilisateur | `admin` |
| `employe1`, `employe2`, `employe3` | Employé (Casablanca, Tanger, Agadir) | `password123` |
| `hse1` | Responsable HSE | `password123` |
| `tech1` | Technicien | `password123` |
| `admin1` | Administrateur | `password123` |
| `direction1` | Direction | `password123` |

## Tests

```bash
python manage.py test
```

## Structure du projet

```
config/          Paramètres et URLs principales
accounts/        Utilisateurs, rôles, sites, services, équipes ; administration des comptes
incidents/       Cœur métier
  models.py        Incident, actions, commentaires, pièces jointes, historique, notifications
  services.py      Règles de transition d'état (déclarer, affecter, démarrer, terminer, clôturer)
  permissions.py   Visibilité des incidents selon le rôle (point d'entrée unique)
  signals.py       Historisation automatique et notifications
  views.py         Vues minces : validation des requêtes puis appel des services
  management/      Commande charger_donnees_test (+ données dans _donnees_demo.py)
  tests/           Tests des services, permissions, vues, pages et notifications
dashboard/       Tableau de bord par rôle et statistiques globales
intelligence/    Suggestion de priorité et détection d'incidents similaires (pur Python)
templates/       Gabarits HTML
static/css/      Feuille de style (custom.css)
```

## Rôles

| Rôle | Accès |
|---|---|
| Employé | Déclare des incidents ; voit les incidents de son site |
| Technicien | Voit les incidents qui le concernent ; réalise les actions qui lui sont affectées |
| Responsable HSE | Qualifie, affecte, crée les actions et clôture ; voit tous les sites |
| Administrateur | Comme le responsable HSE, plus la gestion des comptes |
| Direction | Consultation globale et statistiques |

## Configuration

Les paramètres par défaut conviennent au développement local. Pour un autre environnement, définir :

| Variable | Rôle | Par défaut |
|---|---|---|
| `DJANGO_SECRET_KEY` | Clé secrète Django | clé de développement (à ne pas utiliser en production) |
| `DJANGO_DEBUG` | `1` active le mode debug, `0` le désactive | `1` |
| `DJANGO_ALLOWED_HOSTS` | Hôtes autorisés, séparés par des virgules | `127.0.0.1,localhost` |
