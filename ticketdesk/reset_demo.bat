@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
python desk.py reset
pause
