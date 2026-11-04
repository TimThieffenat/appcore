"""appcore : le socle commun des apps (PySide6, téléphone en paysage + ordinateur).

Démarrage, fenêtre à rail d'icônes, réglages, thèmes, traductions, rapport
d'erreur, son (guitares enregistrées, clavier), contrôles tactiles, police de
symboles, et toute la compilation Android (android/). Chaque app l'inclut
comme sous-module git dans son dossier `appcore/` et n'écrit que ce qui lui
est propre (voir README.md).

Ce fichier n'importe rien : `from appcore import app` marche sans Qt (outils, tests).
"""

VERSION = "1.0.0"
