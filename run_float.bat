@echo off
title Copiloto (flotante)
cd /d "%~dp0"
where python >nul 2>nul || (echo [!] Instala Python desde python.org y marca "Add to PATH". & pause & exit /b)
if not exist ".venv" (
  echo Primera vez: preparando todo, espera 1-2 minutos...
  python -m venv .venv
  call .venv\Scripts\activate.bat
  python -m pip install --upgrade pip
  python -m pip install -r backend\requirements.txt
) else ( call .venv\Scripts\activate.bat )
python launcher_float.py
pause
