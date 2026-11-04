# __APP_NAME__

__DESCRIPTION__ — an app in Python + PySide6 (Qt), designed for **phones in
landscape** and also usable on desktop. Built on **appcore**, the shared base
(git submodule in `appcore/`): start-up, icon rail, settings, light / dark
themes, translations, error report, recorded guitars and soft keys, touch
controls, symbols font and the whole Android build come from there.

## Run on a computer

```
git submodule update --init      # once, after cloning (fetches appcore/)
pip install -r requirements.txt
python main.py                   # or double-click lancer.bat
```

Checks (no phone needed): `appcore\tools\smoke_test.bat` (double-click) runs
the tests, the translation check and opens every page off-screen in both
themes, with screenshots in `build/smoke/`.

## Build the Android app

See `appcore/ANDROID.md`: in the cloud with GitHub Actions (Actions › Android
APK), or locally in WSL2 with `bash appcore/android/build_apk.sh`. Everything
specific to the app (name, Google Play package, permissions, signing key…) is
in `app_info.py`.

## Project layout

- `app_info.py` – name, version, languages, sound, Android package and permissions
- `main.py` – the pages of the rail (`pages()`), the app's style sheet (`QSS`)
- `page_home.py` – the home page (example to replace)
- `page_settings.py` – the settings page of the base, plus the app's own settings
- `icons.py` – the app's icons (drawn in code)
- `locales/<code>.py` – translations of the app's texts (those of the base are in
  `appcore/locales/`) · `tools/i18n_data.py` – texts of the data tables
- `tests/` – tests without Qt
- `tools/make_icon.py` – icon and Play Store graphics
- `store/` – Play Store listing and privacy policy
- `.github/workflows/` – APK, AAB (Play Store) and signing key, the same for every app

## Update the base

```
cd appcore
git pull                 # the latest base
cd ..
git add appcore
git commit -m "appcore à jour"
```
