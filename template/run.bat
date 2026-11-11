@echo off
rem Runs the app on the computer (double-click).
cd /d "%~dp0"
where python >nul 2>nul && (python main.py) || (py main.py)
if errorlevel 1 pause
