#!/bin/bash
# Copiloto — lanzador para Mac. Doble clic (quizá tengas que permitirlo en
# Preferencias > Seguridad la primera vez).
cd "$(dirname "$0")"
echo "==============================="
echo "   Iniciando Copiloto..."
echo "==============================="
if ! command -v python3 &>/dev/null; then
  echo "[!] No se encontro Python 3. Instalalo desde python.org"
  read -p "Enter para salir"
  exit 1
fi
if [ ! -d ".venv" ]; then
  echo "Primera vez: preparando el entorno, espera un momento..."
  python3 -m venv .venv
  source .venv/bin/activate
  pip install --upgrade pip
  pip install -r backend/requirements.txt
else
  source .venv/bin/activate
fi
python launcher.py
