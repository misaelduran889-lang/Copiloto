#!/bin/bash
cd "$(dirname "$0")"
source .venv/bin/activate
pip install pyinstaller
pyinstaller --onefile --windowed --name Copiloto --add-data "ui:ui" --collect-all uvicorn --collect-all rapidfuzz --collect-all webview --collect-all keyboard launcher_float.py
echo "" ; echo "Listo. Copiloto esta en la carpeta dist/"
