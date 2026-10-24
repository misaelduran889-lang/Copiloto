@echo off
cd /d "%~dp0"
call .venv\Scripts\activate.bat
pip install pyinstaller
pyinstaller --onefile --noconsole --name Copiloto --add-data "ui;ui" --collect-all uvicorn --collect-all rapidfuzz --collect-all webview --collect-all keyboard launcher_float.py
echo. & echo Listo. Copiloto.exe esta en la carpeta dist\ & pause
