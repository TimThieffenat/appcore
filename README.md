# appcore — le socle commun des apps

Le code partagé par **RiffFinder**, **PerfectPitch** et les apps à venir :
Python + PySide6 (Qt), pensé pour un **téléphone en paysage** et utilisable sur
ordinateur, compilé pour Android avec l'outil de Qt.

Chaque app l'inclut comme **sous-module git** dans son dossier `appcore/` et
n'écrit que ce qui lui est propre. Une correction ici (rapport d'erreur, son,
compilation Android…) sert à toutes les apps.

## Ce que fournit le socle

| Module | Rôle |
|---|---|
| `boot.py` | le démarrage : rapport d'erreur installé en premier, langue, police de symboles, thème, fenêtre, reconstruction quand la langue change, reprise des données d'un ancien nom |
| `main_window.py` | la fenêtre : rail d'icônes à gauche (taille ajustée à l'écran), pages à droite, pause / reprise en arrière-plan (Android), touche Retour |
| `page_settings.py` | la page Réglages : langue, thème, noms des notes, instrument, rapport d'erreur ; chaque app y ajoute ses lignes |
| `app.py` | ce que le socle sait de l'app : les constantes de son `app_info.py` (avec leurs valeurs par défaut) |
| `i18n.py`, `locales/` | traductions : `tr()`, `ntr()` (pluriels), `N_()` ; 6 langues (en fr es it pt de) pour les textes du socle |
| `crash_report.py` | journal de l'app et rapport d'erreur (erreurs Python, plantages natifs, causes d'arrêt d'Android), envoyé par e-mail en un geste |
| `style.py` | thèmes clair (pastel) et sombre (néon), suivant le téléphone ; une app ajoute sa feuille de style |
| `icons.py` | icônes dessinées en code (rail, cartes) ; une app enregistre les siennes |
| `ui_common.py`, `touch_combo.py`, `touch_input.py` | outils d'interface tactile : listes déroulantes au doigt, champs avec « Terminé », rangées qui défilent, panneaux |
| `sound.py`, `audio_player.py`, `guitar_synth.py`, `sounds/` | le son : guitares acier et nylon enregistrées, clavier doux synthétisé, mixage, lecture avec surlignage, cache |
| `music_theory.py`, `chord_shapes.py` | notes, degrés, gammes, accords, accordages, Do Ré Mi / C D E ; formes d'accords jouables à la guitare (sans Qt) |
| `symbol_font.py`, `symbol_font_data.py` | police de symboles intégrée (♭ ♯ → ✓ ★…) : jamais de carrés vides |
| `app_signals.py` | signaux partagés : réglages changés, langue changée, données de l'utilisateur changées, version payante changée |
| `android/` | toute la compilation Android : APK de test, AAB signé pour Google Play, correctifs de l'outil de Qt, allègement, pages de 16 Ko, activité Java (écran allumé, causes des arrêts, sélecteur de fichiers) — voir **ANDROID.md** |
| `templates/github/workflows/` | les recettes GitHub Actions (APK, AAB, clé), les mêmes pour toutes les apps |
| `template/` | le modèle d'une nouvelle app (voir plus bas) |
| `tools/` | outils de développement : nouvelle app, vérification des traductions, essai de l'interface, police de symboles |
| `tests/` | tests du socle, sans Qt |

## Une app sur le socle

```
MonApp/
  appcore/            <- ce dépôt (sous-module git)
  app_info.py         <- nom, version, langues, son, paquet Android, autorisations…
  main.py             <- les pages du rail (pages()), la feuille de style (QSS)
  android/java/       <- facultatif : le Java de l'app (AppHooks.java…)
  page_*.py           <- les pages de l'app
  page_settings.py    <- la page Réglages du socle + les réglages de l'app
  icons.py            <- les icônes de l'app (enregistrées dans le socle)
  locales/<code>.py   <- les traductions des textes de l'app
  tools/i18n_data.py  <- les textes de ses tableaux de données (pour i18n_check)
  tests/              <- ses tests sans Qt
  store/, icon.png    <- fiche Google Play, icône
  .github/workflows/  <- copies de appcore/templates/github/workflows/
```

### Les points d'accroche

- **`app_info.py`** : rien que des constantes (les scripts Android le lisent sans
  lancer l'app). Toutes sont décrites dans `template/app_info.py` ; seul `NAME`
  est obligatoire.
- **`main.py`** :
  ```python
  import sys
  from appcore import boot          # en premier : installe le rapport d'erreur

  QSS = """QLabel#hero {{ font-size: 30px; color: {accent_text}; }}"""

  def pages():                      # (libellé N_(), icône, classe de la page)
      import icons                  # les icônes de l'app
      from appcore.i18n import N_
      from page_home import HomePage
      from page_settings import SettingsPage
      return [(N_("Home"), "home", HomePage), (N_("Settings"), "settings", SettingsPage)]

  def setup(app):                   # facultatif : avant le thème et la fenêtre
      ...

  if __name__ == "__main__":
      sys.exit(boot.run(pages, qss=QSS, setup=setup))
  ```
  `boot.run` accepte aussi `started(window)` (une fois la fenêtre affichée :
  achats, rappels…), `on_language(code)` (quand la langue change, avant la
  reconstruction de la fenêtre) et `window_class` (une sous-classe de
  `appcore.main_window.MainWindow`, par exemple pour ouvrir une fiche depuis
  n'importe quelle page, comme la fiche Pro de PerfectPitch).
- **Une page** est un `QWidget` (objectName `"page"`) ; elle peut avoir
  `app_paused()` / `app_resumed()` (arrière-plan) et `handle_key(event)`
  (touches ; sinon Retour ramène à la première page). Elle écoute
  `bus.settings_changed` pour suivre un réglage.
- **Réglages** : sous-classe de `appcore.page_settings.SettingsPage`, qui
  redéfinit `rows()` (l'ordre des lignes : `language_row()`, `theme_row()`,
  `notation_row()`, `sound_row()`, `report_row()` et les siennes),
  éventuellement `SOUND_LABEL`, `sound_demo()` et `credits()`. `save(clé,
  valeur)` enregistre et prévient les pages. Pour un instrument réservé (version
  payante…) : `voice_text(clé)` (son nom dans la liste), `voice_refused(clé)`
  (ce qui se passe quand on le choisit sans y avoir droit) et, dans `sound.py`
  de l'app, `set_voice_filter(fn)` ; `fill_sounds()` refait la liste.
- **Icônes** : `register("nom", dessin)` dans `icons.py` de l'app ; le dessin
  trace sur une grille de 24 × 24 avec le crayon déjà réglé.
- **Feuille de style** : `QSS` de `main.py` (ou `style.add_qss()`), avec les
  couleurs du thème entre accolades (`{accent_text}`, `{pink_soft}`, `{gold}`…,
  voir `THEMES` dans `style.py`) et les accolades de la feuille doublées.
- **Compléter un module du socle** : une app peut garder un module du même nom
  qui reprend celui du socle et ajoute ses outils, par exemple le `ui_common.py`
  de RiffFinder (capo, accordage, gaucher) ou le `sound.py` de PerfectPitch
  (jouer une question) :
  ```python
  from appcore.ui_common import *   # noqa: F403 — les outils du socle
  def capo(settings): ...
  ```
  Ailleurs, l'app importe le socle directement : `from appcore import i18n`,
  `from appcore.style import current_palette`…
- **Traductions** : les textes du socle sont traduits dans `appcore/locales/`,
  ceux de l'app dans son `locales/` ; une entrée de l'app remplace celle du
  socle (PerfectPitch tutoie le joueur dans le rapport d'erreur, le socle
  vouvoie).
- **Son** : `sound.synth()` (l'instrument des réglages), `sound.playback()`,
  `guitar_synth.Performance` (ce que l'app fabrique : PCM, durée, événements
  pour surligner), `guitar_synth.arpeggio(...)` pour essayer un instrument,
  `chord_shapes.best_voicing(...)` pour des accords de guitare jouables.
- **Signaux** (`app_signals.bus`) : `settings_changed`, `language_changed`,
  `profile_changed` (données de l'utilisateur), `pro_changed` (version payante).
- **Android, côté Java** : une app peut avoir son Java dans
  `android/java/<paquet>/` ; un `AppHooks.java` (méthodes statiques `onCreate`,
  `onResume`, `onRequestPermissionsResult`) y est appelé par l'activité du
  socle. Ses bibliothèques Java vont dans `GRADLE_DEPENDENCIES`, les
  autorisations qu'elles ajoutent dans `LIBRARY_PERMISSIONS` (`app_info.py`).
- **Essai de l'interface** : `tools/smoke_extra.py` de l'app ajoute son
  parcours (`prepare()`, `before_theme(theme)`, `tour(...)`,
  `tour_language(...)`, tous facultatifs, voir `tools/smoke_test.py`).

## Créer une nouvelle app

```
python appcore/tools/new_app.py MonApp D:\Projects\MonApp --description "A metronome trainer"
```

(depuis le dossier d'une app existante, ou du socle). Le modèle est copié avec
le nom de l'app, les recettes GitHub ajoutées, et — si git est là — un dépôt
créé avec le socle en sous-module (même adresse que le socle actuel). L'app
démarre aussitôt (`python main.py`) : une page d'accueil d'exemple et les
réglages. Ensuite : créer le dépôt sur GitHub, `git remote add origin …`,
`git push -u origin main`, et dans l'app `python tools/make_icon.py`.

## Outils (depuis le dossier d'une app)

| Commande | Rôle |
|---|---|
| `appcore\tools\smoke_test.bat` | tout d'un coup (double-clic) : tests du socle et de l'app, traductions, essai de l'interface ; résultats dans `build\smoke\console.log` |
| `python appcore/tools/smoke_test.py` | ouvre l'app hors écran (850 × 390), chaque page en sombre et en clair, le rapport d'erreur, le format ordinateur ; captures dans `build/smoke/` ; parcours propre à l'app dans `tools/smoke_extra.py` (facultatif) |
| `python appcore/tools/i18n_check.py` | textes à traduire du socle et de l'app, ce qui manque, ce qui ne sert plus (`--list` : tous les textes de l'app, prêts à copier ; `--core` : le socle seul) |
| `python -m unittest discover -s appcore/tests -t .` | tests du socle |
| `python appcore/tools/build_font.py` | refait la police de symboles de l'app (`--core` : celle du socle) ; fonttools et DejaVu Sans nécessaires |
| `bash appcore/android/build_apk.sh` | APK (Linux / WSL), voir ANDROID.md |

## Modifier le socle

Le socle se modifie depuis n'importe quelle app, dans son dossier `appcore/` :

```
cd D:\Projects\RiffFinder\appcore
(modifier, tester avec appcore\tools\smoke_test.bat)
git commit -am "Rapport d'erreur : …"
git push
cd ..
git commit -am "appcore à jour"         (l'app retient la nouvelle version du socle)
```

Puis dans les autres apps :

```
cd D:\Projects\PerfectPitch
git submodule update --remote appcore    (la dernière version du socle)
appcore\tools\smoke_test.bat             (vérifier)
git commit -am "appcore à jour"
```

Chaque app garde la version du socle qu'elle a retenue : une app publiée ne
change pas tant qu'on ne met pas son socle à jour. Après un clone d'une app :
`git clone --recurse-submodules <adresse>`, ou `git submodule update --init`.

Règles pour que le socle reste partageable :
- rien de propre à une app dans `appcore/` : ce qui varie passe par
  `app_info.py` ou par un point d'accroche (pages, `rows()`, `register`, `QSS`…) ;
- un texte affiché passe par `tr()` et se traduit dans `appcore/locales/`
  (les 5 langues : `python appcore/tools/i18n_check.py --core`) ;
- un changement qui casse une app (nom de fonction, réglage) se fait dans
  toutes les apps en même temps, ou garde l'ancien nom.
