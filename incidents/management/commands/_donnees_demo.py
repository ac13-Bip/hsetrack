"""
Jeu de donnees de demonstration utilise par la commande
charger_donnees_test. Fichier prefixe par "_" : Django ne le considere
pas comme une commande.
"""
from accounts.models import User
from incidents.models import CategorieIncident, Incident

Role = User.Role
Domaine = CategorieIncident.Domaine

# cle -> (nom, adresse, services)
SITES = {
    'casa': ("Usine de Casablanca", 'Zone industrielle, Casablanca', ['Production', 'Logistique', 'Maintenance']),
    'tanger': ("Usine de Tanger", 'Zone franche, Tanger', ['Production', 'Logistique']),
    'agadir': ("Usine d'Agadir", 'Zone industrielle, Agadir', ['Production', 'Logistique']),
}

# (username, role, prenom, nom, cle du site, service)
UTILISATEURS = [
    ('employe1', Role.EMPLOYE, 'Ahmed', 'Benali', 'casa', 'Production'),
    ('employe2', Role.EMPLOYE, 'Yassine', 'Lahlou', 'tanger', 'Production'),
    ('employe3', Role.EMPLOYE, 'Imane', 'Berrada', 'agadir', 'Production'),
    ('hse1', Role.RESPONSABLE_HSE, 'Fatima', 'Alaoui', 'casa', 'Maintenance'),
    ('tech1', Role.TECHNICIEN, 'Karim', 'Sami', 'casa', 'Maintenance'),
    ('admin1', Role.ADMIN, 'Sara', 'Idrissi', 'casa', 'Logistique'),
    ('direction1', Role.DIRECTION, 'Mohamed', 'Tazi', 'casa', 'Production'),
]
MOT_DE_PASSE = 'password123'

CATEGORIES = [
    ('Chute de plain-pied', Domaine.SECURITE),
    ('Coupure', Domaine.SECURITE),
    ('Bruleure', Domaine.SECURITE),
    ('Pollution sonore', Domaine.ENVIRONNEMENT),
    ('Deversement chimique', Domaine.ENVIRONNEMENT),
    ('Probleme sanitaire', Domaine.HYGIENE),
]

# Site de Casablanca, par categorie : 2 cas clotures (vocabulaire proche,
# action terminee) + 1 cas declare au vocabulaire similaire, afin que la
# similarite cosinus (intelligence/text_utils.py) ait des incidents a
# rapprocher et des actions terminees a recommander.
INCIDENTS_CASABLANCA = {
    'Chute de plain-pied': {
        'cloture': [
            {
                'titre': "Chute de plain-pied a l'atelier B",
                'description': "Un operateur a glisse sur une flaque d'huile dans l'atelier de production et s'est blesse a la jambe. Intervention medicale legere sur site.",
                'gravite': Incident.Gravite.MODEREE,
                'action': "Installer un revetement antiderapant et afficher une signalisation de sol glissant dans l'atelier B.",
            },
            {
                'titre': "Chute de plain-pied pres de la zone de stockage",
                'description': "Une employee a trebuche sur un cable electrique mal range pres de la zone de stockage et a chute, occasionnant une entorse a la cheville.",
                'gravite': Incident.Gravite.MODEREE,
                'action': "Ranger les cables dans des gaines de protection et organiser un rappel des regles de rangement.",
            },
        ],
        'declare': {
            'titre': "Chute de plain-pied dans le couloir principal",
            'description': "Un technicien a glisse sur le sol mouille du couloir principal suite a une fuite d'eau non signalee, sans blessure grave.",
            'gravite': Incident.Gravite.MODEREE,
        },
    },
    'Coupure': {
        'cloture': [
            {
                'titre': "Coupure a la main sur machine de decoupe",
                'description': "Un operateur s'est coupe la main avec la lame de la machine de decoupe par manque de protection adaptee.",
                'gravite': Incident.Gravite.MODEREE,
                'action': "Installer un carter de protection sur la lame et fournir des gants anti-coupure renforces.",
            },
            {
                'titre': "Coupure au doigt lors du deballage de pieces metalliques",
                'description': "Une employee s'est coupee le doigt sur le bord tranchant d'une piece metallique lors du deballage d'une livraison.",
                'gravite': Incident.Gravite.FAIBLE,
                'action': "Fournir des gants anti-coupure pour les operations de deballage et former les equipes.",
            },
        ],
        'declare': {
            'titre': "Coupure a la main lors de la manipulation d'un outil tranchant",
            'description': "Un technicien s'est coupe la main en manipulant un outil tranchant non range correctement dans l'atelier.",
            'gravite': Incident.Gravite.MODEREE,
        },
    },
    'Bruleure': {
        'cloture': [
            {
                'titre': "Brulure a la main sur surface chaude",
                'description': "Un operateur s'est brule la main en touchant une surface chaude d'une machine non isolee thermiquement.",
                'gravite': Incident.Gravite.MODEREE,
                'action': "Installer une isolation thermique sur la machine et poser une signalisation de surface chaude.",
            },
            {
                'titre': "Brulure legere lors d'une projection de produit chaud",
                'description': "Une employee a recu une projection de liquide chaud sur le bras lors d'une operation de nettoyage, occasionnant une brulure legere.",
                'gravite': Incident.Gravite.MODEREE,
                'action': "Fournir des equipements de protection individuelle adaptes et revoir la procedure de nettoyage.",
            },
        ],
        'declare': {
            'titre': "Brulure au contact d'une surface chaude en zone de production",
            'description': "Un technicien s'est brule le bras au contact d'une surface chaude non protegee en zone de production.",
            'gravite': Incident.Gravite.MODEREE,
        },
    },
    'Pollution sonore': {
        'cloture': [
            {
                'titre': "Depassement du niveau sonore autorise en zone de production",
                'description': "Des mesures ont revele un depassement du seuil sonore reglementaire a proximite de la ligne de production, genant le voisinage.",
                'gravite': Incident.Gravite.MODEREE,
                'action': "Installer des panneaux acoustiques et planifier la maintenance des equipements bruyants.",
            },
            {
                'titre': "Nuisance sonore liee au fonctionnement d'un compresseur",
                'description': "Le fonctionnement continu d'un compresseur a genere une nuisance sonore signalee par plusieurs employes du service voisin.",
                'gravite': Incident.Gravite.FAIBLE,
                'action': "Deplacer le compresseur dans un local isole acoustiquement et planifier un entretien regulier.",
            },
        ],
        'declare': {
            'titre': "Niveau sonore eleve signale pres de la chaine de production",
            'description': "Plusieurs employes ont signale un niveau sonore eleve et persistant a proximite de la chaine de production.",
            'gravite': Incident.Gravite.MODEREE,
        },
    },
    'Deversement chimique': {
        'cloture': [
            {
                'titre': "Deversement chimique lors du transvasement de solvant",
                'description': "Un deversement accidentel de solvant s'est produit lors du transvasement entre deux cuves, contaminant une partie du sol de l'atelier.",
                'gravite': Incident.Gravite.IMPORTANTE,
                'action': "Mettre en place un bac de retention sous les cuves et former les equipes au transvasement securise.",
            },
            {
                'titre': "Fuite de produit chimique au niveau d'un raccord",
                'description': "Une fuite de produit chimique a ete constatee au niveau d'un raccord defectueux sur une cuve de stockage.",
                'gravite': Incident.Gravite.IMPORTANTE,
                'action': "Remplacer le raccord defectueux et mettre en place une inspection periodique des raccords.",
            },
        ],
        'declare': {
            'titre': "Petite fuite de produit chimique detectee pres des cuves de stockage",
            'description': "Une fuite de produit chimique a ete detectee pres des cuves de stockage, sans consequence environnementale majeure pour le moment.",
            'gravite': Incident.Gravite.IMPORTANTE,
        },
    },
    'Probleme sanitaire': {
        'cloture': [
            {
                'titre': "Probleme sanitaire lie a la proprete des sanitaires du site",
                'description': "Plusieurs employes ont signale un manque de proprete recurrent dans les sanitaires du site, posant un risque d'hygiene.",
                'gravite': Incident.Gravite.FAIBLE,
                'action': "Renforcer la frequence de nettoyage des sanitaires et mettre en place un controle hebdomadaire.",
            },
            {
                'titre': "Probleme sanitaire dans la cantine du personnel",
                'description': "Une odeur suspecte et un manque d'hygiene ont ete constates dans la cantine du personnel lors d'une inspection de routine.",
                'gravite': Incident.Gravite.MODEREE,
                'action': "Effectuer un nettoyage approfondi de la cantine et revoir le protocole d'hygiene alimentaire.",
            },
        ],
        'declare': {
            'titre': "Probleme sanitaire signale dans les vestiaires du personnel",
            'description': "Des employes ont signale un probleme d'hygiene et de proprete dans les vestiaires du personnel.",
            'gravite': Incident.Gravite.FAIBLE,
        },
    },
}

# Autres sites (Tanger, Agadir) : chaque employe a des incidents clotures
# qu'il a declares sur son site (rubrique "Incidents clotures" cote
# employe) et un incident encore en cours, afin que la liste filtree par
# site ne soit pas vide.
INCIDENTS_AUTRES_SITES = [
    {
        'employe': 'employe2', 'site': 'tanger', 'service': 'Production',
        'cloture': [
            {
                'titre': "Coupure a la main lors du conditionnement",
                'description': "Un operateur s'est coupe la main avec un cutter lors du conditionnement de cartons sur la ligne de Tanger.",
                'categorie': 'Coupure', 'gravite': Incident.Gravite.FAIBLE,
                'action': "Remplacer les cutters par des outils a lame retractable et rappeler les consignes de securite.",
            },
            {
                'titre': "Brulure legere au contact d'un tuyau de vapeur",
                'description': "Une employee s'est legerement brulee en touchant un tuyau de vapeur non isole sur le site de Tanger.",
                'categorie': 'Bruleure', 'gravite': Incident.Gravite.MODEREE,
                'action': "Isoler thermiquement le tuyau et installer une signalisation de danger.",
            },
        ],
        'declare': {
            'titre': "Chute de plain-pied sur sol humide en zone de lavage",
            'description': "Un technicien a glisse sur le sol humide de la zone de lavage du site de Tanger, sans blessure grave.",
            'categorie': 'Chute de plain-pied', 'gravite': Incident.Gravite.FAIBLE,
        },
    },
    {
        'employe': 'employe3', 'site': 'agadir', 'service': 'Production',
        'cloture': [
            {
                'titre': "Deversement chimique lors d'un transfert de cuve",
                'description': "Un deversement de produit chimique s'est produit lors d'un transfert de cuve sur le site d'Agadir.",
                'categorie': 'Deversement chimique', 'gravite': Incident.Gravite.IMPORTANTE,
                'action': "Installer un bac de retention et former les equipes au transfert securise.",
            },
            {
                'titre': "Probleme sanitaire dans les vestiaires du site",
                'description': "Un manque de proprete a ete signale dans les vestiaires du personnel sur le site d'Agadir.",
                'categorie': 'Probleme sanitaire', 'gravite': Incident.Gravite.FAIBLE,
                'action': "Renforcer la frequence de nettoyage et mettre en place un controle hebdomadaire.",
            },
        ],
        'declare': {
            'titre': "Nuisance sonore liee a un nouveau compresseur",
            'description': "Le fonctionnement d'un nouveau compresseur a genere une nuisance sonore signalee par les equipes du site d'Agadir.",
            'categorie': 'Pollution sonore', 'gravite': Incident.Gravite.FAIBLE,
        },
    },
]
