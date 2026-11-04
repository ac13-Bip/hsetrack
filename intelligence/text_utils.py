"""
Outils de comparaison de texte en PUR PYTHON (aucune dependance externe :
ni numpy, ni scikit-learn). Choix delibere : le cahier des charges exclut
explicitement "l'analyse predictive complexe basee sur apprentissage
profond" (section 4.2), un sac-de-mots + similarite cosinus est largement
suffisant pour "suggerer une priorite" et "detecter des incidents
similaires" (section 6.6), tout en restant 100% fiable a l'execution -
le projet precedent avait rencontre un probleme de DLL bloquee (scipy)
qui rendait scikit-learn indisponible sur certains postes Windows.
"""
import math
import re
from collections import Counter

MOTS_VIDES = {
    'le', 'la', 'les', 'un', 'une', 'des', 'de', 'du', 'au', 'aux', 'a',
    'et', 'ou', 'est', 'sont', 'etait', 'ete', 'en', 'dans', 'sur', 'sous',
    'avec', 'sans', 'pour', 'par', 'ce', 'cette', 'ces', 'qui', 'que', 'quoi',
    'son', 'sa', 'ses', 'nous', 'vous', 'ils', 'elle', 'il', 'on', 'se', 'pas',
    'plus', 'tres', 'fait', 'faire', 'apres', 'avant', 'lors', 'lorsque',
}

_RE_MOT = re.compile(r"[a-zàâäéèêëïîôöùûüç]+")


def tokeniser(texte):
    """Decoupe un texte en mots significatifs (minuscules, sans mots vides)."""
    mots = _RE_MOT.findall(texte.lower())
    return [m for m in mots if len(m) > 2 and m not in MOTS_VIDES]


def vectoriser(texte):
    """Sac-de-mots : Counter {mot: occurrences}."""
    return Counter(tokeniser(texte))


def similarite_cosinus(vecteur_a, vecteur_b):
    """
    Similarite cosinus entre deux sacs-de-mots, calculee a la main :
    cos(A, B) = (A . B) / (||A|| * ||B||)
    Retourne un score entre 0.0 (rien en commun) et 1.0 (identique).
    """
    if not vecteur_a or not vecteur_b:
        return 0.0

    mots_communs = set(vecteur_a) & set(vecteur_b)
    produit_scalaire = sum(vecteur_a[mot] * vecteur_b[mot] for mot in mots_communs)
    if produit_scalaire == 0:
        return 0.0

    norme_a = math.sqrt(sum(v * v for v in vecteur_a.values()))
    norme_b = math.sqrt(sum(v * v for v in vecteur_b.values()))
    return produit_scalaire / (norme_a * norme_b)
