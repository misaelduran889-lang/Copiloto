#!/bin/bash
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "[!] Instala Python 3 desde python.org"; read -p "Enter"; exit 1; }
if [ ! -d ".venv" ]; then
  echo "Primera vez: preparando todo, espera 1-2 minutos..."
  python3 -m venv .venv; source .venv/bin/activate
  pip install --upgrade pip; pip install -r backend/requirements.txt
else source .venv/bin/activate; fi
python launcher_float.py
