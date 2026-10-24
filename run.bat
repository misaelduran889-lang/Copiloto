@echo off
title Copiloto
cd /d "%~dp0"
echo ===============================
echo    Iniciando Copiloto...
echo ===============================
where python >nul 2>nul
if errorlevel 1 (
  echo [!] No se encontro Python. Instalalo desde python.org y marca "Add to PATH".
  pause
  exit /b
)
if not exist ".venv" (
  echo Primera vez: preparando el entorno, espera un momento...
  python -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  python -m pip install -r backend\requirements.txt
) else (
  call .venv\Scripts\activate.bat
)
python launcher.py
pause
