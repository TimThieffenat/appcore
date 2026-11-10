@echo off
rem Full check of an app: tests, translations, off-screen interface.
rem Double-click from appcore\tools\ (or run from anywhere):
rem the app is the folder above appcore\. Results in the app's build\smoke\.
rem "smoke_test.bat nopause": without waiting for a key at the end (scripts).
cd /d "%~dp0..\.."
if not exist build\smoke mkdir build\smoke
if exist build\smoke\smoke.log del build\smoke\smoke.log
set PY=python
where python >nul 2>nul || set PY=py
(
  %PY% --version
  %PY% -c "import PySide6; print('PySide6', PySide6.__version__)"
  %PY% -m unittest discover -s appcore\tests -t .
  if exist tests %PY% -m unittest discover tests
  %PY% appcore\tools\i18n_check.py
  %PY% appcore\tools\smoke_test.py
) > build\smoke\console.log 2>&1
findstr /b /c:"OK" build\smoke\smoke.log >nul 2>nul && (echo Check OK) || (echo ERROR: see build\smoke\console.log)
echo Done: see build\smoke\console.log and the screenshots in build\smoke\
if not "%1"=="nopause" pause
