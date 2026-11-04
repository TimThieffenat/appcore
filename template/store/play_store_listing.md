# __APP_NAME__ — Google Play listing

Texts for the Play Console (Main store listing). Keep the limits.

## English

**App name (30 max):** __APP_NAME__
**Short description (80 max):**

**Full description (4000 max):**

…

No account, no ads, no internet permission: everything stays on your device.
If something goes wrong, you can send an error report from your own email app,
only if you want to.

## Français

**Nom (30 max) :** __APP_NAME__
**Description courte (80 max) :**

**Description complète (4000 max) :**

…

## Graphics

- Icon 512 × 512: `store/play_icon_512.png` (`python tools/make_icon.py`)
- Feature graphic 1024 × 500: `store/feature_graphic_1024x500.png`
- Screenshots: `python appcore/tools/smoke_test.py` writes them in `build/smoke/`
  (phone 850 × 390; take real phone screenshots for the store if possible)

## Data safety (Play Console)

No data collected, no data shared (the error report is sent by the user's own
email app). Privacy policy: `store/privacy_policy.html` (publish it, e.g. GitHub Pages).
