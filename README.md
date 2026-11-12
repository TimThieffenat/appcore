# appcore — the shared base of the apps

The code shared by **RiffFinder**, **PerfectPitch** and the apps to come:
Python + PySide6 (Qt), designed for a **phone in landscape** (or in
**portrait**, as each app chooses) and usable on desktop, built for Android with Qt's tool.

Each app includes it as a **git submodule** in its `appcore/` folder and only
writes what is its own. A fix here (error report, sound, Android build…)
serves every app.

## What the base provides

| Module | Role |
|---|---|
| `boot.py` | start-up: error report installed first, language, symbols font, theme, window, rebuilt when the language changes, data taken over from a former name |
| `main_window.py` | the window: icon rail on the left (size adjusted to the screen) or, in portrait, navigation bar at the bottom with the home page standing out; pause / resume in the background (Android), Back key (to the home page) |
| `page_settings.py` | the Settings page: the Pro version and its unlock code, language, theme, note names, instrument, error report; each app adds its own rows |
| `pro.py`, `pro_ui.py`, `bridge.py` | the paid Pro version (`PRO_PRODUCT`): one-time Google Play purchase checked at start-up and on return, unlock code for Google Play's reviewers, purchase buttons, pages reserved to Pro (wall, gold padlock); the file bridge with the Java side |
| `app.py` | what the base knows about the app: the constants of its `app_info.py` (with their default values) |
| `i18n.py`, `locales/` | translations: `tr()`, `ntr()` (plurals), `N_()`; 6 languages (en fr es it pt de) for the base's texts |
| `crash_report.py` | the app's log and error report (Python errors, native crashes, Android exit reasons), sent by email in one gesture |
| `style.py` | light (pastel) and dark (neon) themes, following the phone; an app adds its own style sheet |
| `icons.py` | icons drawn in code (rail, cards); an app registers its own |
| `ui_common.py`, `touch_combo.py`, `touch_input.py` | touch interface tools: finger-friendly drop-down lists, fields with "Done", scrolling rows, panels |
| `sound.py`, `audio_player.py`, `guitar_synth.py`, `sounds/` | sound: recorded steel and nylon guitars, synthesised soft keys, mixing, playback with highlighting, cache |
| `music_theory.py`, `chord_shapes.py` | notes, degrees, scales, chords, tunings, Do Ré Mi / C D E; playable guitar chord shapes (no Qt) |
| `symbol_font.py`, `symbol_font_data.py` | built-in symbols font (♭ ♯ → ✓ ★…): never empty boxes |
| `app_signals.py` | shared signals: settings changed, language changed, user data changed, paid version changed |
| `android/` | the whole Android build: test APK, signed AAB for Google Play, fixes to Qt's tool, slimming, 16 KB pages, Java activity (screen kept on, exit reasons, file picker, file bridge, Google Play Billing for the Pro version) — see **ANDROID.md** |
| `templates/github/workflows/` | the GitHub Actions workflows (APK, AAB, key), the same for every app |
| `template/` | the template of a new app (see below) |
| `tools/` | development tools: new app, translation check, interface check, symbols font |
| `tests/` | tests of the base, without Qt |

## An app on the base

```
MyApp/
  appcore/            <- this repository (git submodule)
  app_info.py         <- name, version, languages, sound, Android package, permissions…
  main.py             <- the rail's pages (pages()), the style sheet (QSS)
  android/java/       <- optional: the app's Java (AppHooks.java…)
  page_*.py           <- the app's pages
  page_settings.py    <- the base's Settings page + the app's settings
  icons.py            <- the app's icons (registered in the base)
  locales/<code>.py   <- translations of the app's texts
  tools/i18n_data.py  <- the texts of its data tables (for i18n_check)
  tests/              <- its tests without Qt
  store/, icon.png    <- Google Play listing, icon
  .github/workflows/  <- copies of appcore/templates/github/workflows/
```

### The hooks

- **`app_info.py`**: nothing but constants (the Android scripts read it without
  running the app). They are all described in `template/app_info.py`; only `NAME`
  is required. `ORIENTATION = "portrait"` puts the app in portrait (navigation
  bar at the bottom, APK in portrait); `HOME_PAGE` is the home page
  (its position or its icon's name; opened at start-up, standing out in the bottom bar, Back returns to it);
  `window.set_nav_visible(False)` hides the rail or the bar (full-screen game).
- **`main.py`**:
  ```python
  import sys
  from appcore import boot          # first: installs the error report

  QSS = """QLabel#hero {{ font-size: 30px; color: {accent_text}; }}"""

  def pages():                      # (N_() label, icon, page class)
      import icons                  # the app's icons
      from appcore.i18n import N_
      from page_home import HomePage
      from page_settings import SettingsPage
      return [(N_("Home"), "home", HomePage), (N_("Settings"), "settings", SettingsPage)]

  def setup(app):                   # optional: before the theme and the window
      ...

  if __name__ == "__main__":
      sys.exit(boot.run(pages, qss=QSS, setup=setup))
  ```
  `boot.run` also accepts `started(window)` (once the window is shown:
  reminders…), `on_language(code)` (when the language changes, before
  the window is rebuilt) and `window_class` (a subclass of
  `appcore.main_window.MainWindow`, for example to open a sheet from
  any page, like PerfectPitch's Pro sheet).
- **A page** is a `QWidget` (objectName `"page"`); it can have
  `app_paused()` / `app_resumed()` (background) and `handle_key(event)`
  (keys; otherwise Back returns to the home page). It listens to
  `bus.settings_changed` to follow a setting.
- **Settings**: a subclass of `appcore.page_settings.SettingsPage`, which
  overrides `rows()` (the order of the rows: `pro_rows()`, `language_row()`,
  `theme_row()`, `notation_row()`, `sound_row()`, `report_row()` and its own),
  possibly `SOUND_LABEL`, `sound_demo()` and `credits()`. `save(key,
  value)` saves and notifies the pages. For an instrument reserved some other
  way: `voice_text(key)` (its name in the list), `voice_refused(key)` (what
  happens when it is chosen without the right to it) and
  `sound.set_voice_filter(fn)`; `fill_sounds()` rebuilds the list.
- **Pro version** (one-time purchase on Google Play): `PRO_PRODUCT = "pro"` in
  `app_info.py` (the product ID of the Play Console) and the base does the
  rest: purchase checked at start-up and when the app comes back, price,
  buy / restore (`pro.py`), the Java side and Google Play Billing in the APK,
  the "<App> Pro" row and the unlock code for Google Play's reviewers in the
  settings (`pro_rows()`, `UNLOCK_CODE_SHA256`, made by
  `python appcore/tools/unlock_code.py`), the instruments of `PRO_VOICES`
  marked "(Pro)". What Pro opens is up to the app: `pro.is_pro()`, and
  `pro_ui.gate(PageClass, WallClass)` for a page reserved to Pro (its "wall"
  until bought, a gold padlock on its icon; `pro_ui.PurchaseControls` gives the
  status line and the purchase buttons). "Discover Pro" calls the window's
  `open_pro()` (by default the first Pro page; a `window_class` can open a
  sheet instead, like PerfectPitch). On a computer, "Unlock" is free (tests);
  `<APP>_PRO=1` / `0` (e.g. `RIFFFINDER_PRO`) forces it.
- **Icons**: `register("name", drawer)` in the app's `icons.py`; the drawer
  draws on a 24 × 24 grid with the pen already set.
- **Style sheet**: `QSS` in `main.py` (or `style.add_qss()`), with the
  theme's colours in braces (`{accent_text}`, `{pink_soft}`, `{gold}`…,
  see `THEMES` in `style.py`) and the sheet's own braces doubled.
- **Extending a base module**: an app can keep a module of the same name
  that takes the base's one and adds its tools, for example RiffFinder's
  `ui_common.py` (capo, tuning, left-handed) or PerfectPitch's `sound.py`
  (play a question):
  ```python
  from appcore.ui_common import *   # noqa: F403 — the base's tools
  def capo(settings): ...
  ```
  Elsewhere, the app imports the base directly: `from appcore import i18n`,
  `from appcore.style import current_palette`…
- **Translations**: the base's texts are translated in `appcore/locales/`,
  the app's in its `locales/`; an app entry replaces the base's
  (PerfectPitch uses "tu" with the player in the French error report, the
  base uses "vous").
- **Sound**: `sound.synth()` (the instrument from the settings), `sound.playback()`,
  `guitar_synth.Performance` (what the app builds: PCM, duration, events
  to highlight), `guitar_synth.arpeggio(...)` to try an instrument,
  `chord_shapes.best_voicing(...)` for playable guitar chords.
- **Signals** (`app_signals.bus`): `settings_changed`, `language_changed`,
  `profile_changed` (user data), `pro_changed` (paid version).
- **Android, Java side**: an app can have its Java in
  `android/java/<package>/`; an `AppHooks.java` there (static methods `onCreate`,
  `onResume`, `onCommand`, `onRequestPermissionsResult`) is called by the base's
  activity. Python talks to Java through files (`bridge.py`):
  `bridge.request("reminder:update")` reaches `AppHooks.onCommand`, and the
  app's Java answers with `Bridge.put("section", json)` (read back by
  `bridge.state()`). Its Java libraries go in `GRADLE_DEPENDENCIES`, the
  permissions they add in `LIBRARY_PERMISSIONS` (`app_info.py`).
- **Interface check**: the app's `tools/smoke_extra.py` adds its own
  tour (`prepare()`, `before_theme(theme)`, `tour(...)`,
  `tour_language(...)`, all optional, see `tools/smoke_test.py`).

## Creating a new app

```
python appcore/tools/new_app.py MyApp D:\Projects\MyApp --description "A metronome trainer"
```

(from the folder of an existing app, or of the base). The template is copied with
the app's name, the GitHub workflows added, and — if git is there — a repository
created with the base as a submodule (same URL as the current base). The app
starts at once (`python main.py`, or double-click `run.bat`): an example home
page and the settings. Next: create the repository on GitHub,
`git remote add origin …`, `git push -u origin main`, and in the app
`python tools/make_icon.py`.

## Tools (from an app's folder)

| Command | Role |
|---|---|
| `appcore\tools\smoke_test.bat` | everything at once (double-click): tests of the base and of the app, translations, interface check; results in `build\smoke\console.log` |
| `python appcore/tools/smoke_test.py` | opens the app off screen (850 × 390 in landscape, 390 × 844 in portrait), each page in dark and in light, the error report, the desktop format, then each other language; screenshots in `build/smoke/`; the app's own tour in `tools/smoke_extra.py` (optional) |
| `python appcore/tools/i18n_check.py` | the base's and the app's texts to translate, what is missing, what is no longer used (`--list`: all the app's texts, ready to paste; `--core`: the base alone) |
| `python appcore/tools/unlock_code.py` | a new unlock code for Google Play's reviewers and its `UNLOCK_CODE_SHA256` line (`--check CODE`: does it open this version?) |
| `python -m unittest discover -s appcore/tests -t .` | tests of the base |
| `python appcore/tools/build_font.py` | rebuilds the app's symbols font (`--core`: the base's); needs fonttools and DejaVu Sans |
| `bash appcore/android/build_apk.sh` | APK (Linux / WSL), see ANDROID.md |

## Changing the base

The base is changed from any app, in its `appcore/` folder:

```
cd D:\Projects\RiffFinder\appcore
(change, test with appcore\tools\smoke_test.bat)
git commit -am "Error report: …"
git push
cd ..
git commit -am "Update appcore"          (the app records the new version of the base)
```

Then in the other apps:

```
cd D:\Projects\PerfectPitch
git submodule update --remote appcore    (the latest version of the base)
appcore\tools\smoke_test.bat             (check)
git commit -am "Update appcore"
```

Each app keeps the version of the base it recorded: a published app does not
change until its base is updated. After cloning an app:
`git clone --recurse-submodules <url>`, or `git submodule update --init`.

Rules to keep the base shareable:
- nothing specific to one app in `appcore/`: what varies goes through
  `app_info.py` or through a hook (pages, `rows()`, `register`, `QSS`…);
- displayed text goes through `tr()` and is translated in `appcore/locales/`
  (the 5 languages: `python appcore/tools/i18n_check.py --core`);
- code, comments and documentation of the base are written in English;
- a change that breaks an app (function name, setting) is made in
  all apps at the same time, or keeps the old name.
