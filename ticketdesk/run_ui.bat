@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
echo Dashboard: http://localhost:8000   (close this window to stop)
python desk.py ui
