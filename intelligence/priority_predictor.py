"""
Suggestion automatique du niveau de priorite d'un incident (section 6.6).

Approche a REGLES EXPERTES, transparente et deterministe (donc explicable
a un jury de soutenance) : on combine la gravite declaree, le domaine de
la categorie et la presence de mots-cles d'urgence dans le texte libre.
Pas de boite noire ML pour une regle de gestion qui doit rester auditable.
"""
from incidents.models import Incident
from .text_utils import tokeniser

MOTS_CLES_URGENTS = {
    'feu', 'incendie', 'explosion', 'electrocution', 'electrocute',
    'fuite', 'gaz', 'asphyxie', 'inconscient', 'inconsciente', 'coma',
    'hospitalisation', 'hospitalise', 'grave', 'graves', 'urgence',
    'urgent', 'mortel', 'mortelle', 'deces', 'effondrement', 'chimique',
    'toxique', 'brulure', 'brulures', 'hemorragie', 'fracture',
}


def predire_priorite(incident):
    """
    Calcule un score de 0 a ~7 a partir de la gravite (poids fort), du
    domaine Securite (poids moyen) et des mots-cles d'urgence (poids
    faible cumulatif), puis le projette sur l'echelle Priorite (1 a 4).
    """
    score = incident.gravite * 1.5  # 1.5 a 6

    if incident.categorie_id and incident.categorie.domaine == incident.categorie.Domaine.SECURITE:
        score += 1

    texte = f"{incident.titre} {incident.description}"
    mots = set(tokeniser(texte))
    score += min(len(mots & MOTS_CLES_URGENTS), 3)  # plafonne a +3

    if score >= 7:
        return Incident.Priorite.URGENTE
    if score >= 5:
        return Incident.Priorite.HAUTE
    if score >= 3:
        return Incident.Priorite.NORMALE
    return Incident.Priorite.BASSE
