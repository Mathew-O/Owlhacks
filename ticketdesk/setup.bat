@echo off
cd /d "%~dp0"
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
if not exist logs mkdir logs
if not exist .env copy .env.example .env
python -m tests.smoke
echo.
echo Setup done. Next: run_ui.bat
pause
