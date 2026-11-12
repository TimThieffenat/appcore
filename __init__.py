"""appcore: the shared base of the apps (PySide6, phone in landscape or portrait + desktop).

Start-up, window with an icon rail, settings, themes, translations, error
report, sound (recorded guitars, keyboard), touch controls, symbols font, and
the whole Android build (android/). Each app includes it as a git submodule
in its `appcore/` folder and only writes what is its own
(see README.md).

This file imports nothing: `from appcore import app` works without Qt (tools, tests).
"""

VERSION = "1.1.0"
