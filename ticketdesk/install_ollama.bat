@echo off
cd /d "%~dp0"
if not exist logs mkdir logs
echo [%time%] Installing Ollama (official, via winget)... > logs\ollama.txt
winget install --id Ollama.Ollama -e --silent --accept-source-agreements --accept-package-agreements >> logs\ollama.txt 2>&1
set "OLLAMA=%LOCALAPPDATA%\Programs\Ollama\ollama.exe"
if not exist "%OLLAMA%" (
  echo ollama.exe not found. Install by hand from ollama.com/download, then run this again. >> logs\ollama.txt
  type logs\ollama.txt
  timeout /t 60
  exit /b 1
)
if exist "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe" start "" "%LOCALAPPDATA%\Programs\Ollama\ollama app.exe"
timeout /t 15 /nobreak >nul
"%OLLAMA%" pull gemma3:4b >> logs\ollama.txt 2>&1
"%OLLAMA%" list >> logs\ollama.txt 2>&1
type logs\ollama.txt
echo Next: MODEL_TRIAGE=ollama:gemma3:4b in .env, then run_ui.bat
timeout /t 30
