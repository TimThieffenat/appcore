"""Traduction : français (voir appcore/i18n.py).

Clé : le texte anglais du code ; valeur : sa traduction (un pluriel :
(singulier, pluriel)). Les champs {nom} doivent rester tels quels.
python appcore/tools/i18n_check.py dit ce qui manque après un changement de
texte (--list les donne tous, prêts à copier ici). Les textes du socle
(réglages, rapport d'erreur, accords…) sont traduits dans appcore/locales/ ;
une entrée ici remplace celle du socle."""
# ruff: noqa: E501

T = {
    # --- main.py
    'Home': 'Accueil',
    # --- page_home.py
    'Play': 'Jouer',
    'Root': 'Tonique',
    'Welcome': 'Bienvenue',
}
