"""
Detection d'incidents similaires/recurrents et recommandation d'actions
a partir de cas anterieurs (section 6.6), via une similarite cosinus en
pur Python (cf. text_utils.py) sur le titre + la description, avec un
bonus si la categorie est identique.
"""
from incidents.models import ActionCorrective, Incident

from .text_utils import similarite_cosinus, vectoriser

SEUIL_SIMILARITE = 0.1
BONUS_MEME_CATEGORIE = 0.15
# Nombre maximum d'incidents (les plus recents) compares a chaque appel :
# borne le cout du calcul, fait en Python a chaque affichage d'une fiche.
NB_MAX_CANDIDATS = 500


def _texte(incident):
    return f"{incident.titre} {incident.description}"


def trouver_similaires(incident, k=3):
    """Retourne jusqu'a `k` tuples (incident_similaire, score_pourcentage)."""
    candidats = (
        Incident.objects.exclude(pk=incident.pk)
        .only('pk', 'reference', 'titre', 'description', 'categorie_id')
        .order_by('-cree_le')[:NB_MAX_CANDIDATS]
    )

    vecteur_ref = vectoriser(_texte(incident))
    resultats = []
    for autre in candidats:
        score = similarite_cosinus(vecteur_ref, vectoriser(_texte(autre)))
        if incident.categorie_id and autre.categorie_id == incident.categorie_id:
            score += BONUS_MEME_CATEGORIE
        score = min(score, 1.0)
        if score >= SEUIL_SIMILARITE:
            resultats.append((autre, round(score * 100)))

    resultats.sort(key=lambda paire: paire[1], reverse=True)
    return resultats[:k]


def recommander_actions(incident, k=3):
    """
    Propose jusqu'a `k` actions deja realisees sur des incidents similaires,
    pour aider le responsable HSE a qualifier rapidement le traitement.
    """
    recommandations = []
    for autre, score in trouver_similaires(incident, k=10):
        for action in autre.actions.filter(statut=ActionCorrective.StatutAction.TERMINEE):
            recommandations.append({
                'type': action.get_type_action_display(),
                'type_code': action.type_action,
                'description': action.description,
                'score_pertinence': score,
                'incident_source': autre.reference,
            })
            if len(recommandations) >= k:
                return recommandations
    return recommandations
