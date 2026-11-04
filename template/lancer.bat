@echo off
rem Lance l'app sur l'ordinateur (double-clic).
cd /d "%~dp0"
where python >nul 2>nul && (python main.py) || (py main.py)
if errorlevel 1 pause
