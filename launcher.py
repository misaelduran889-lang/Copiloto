"""
launcher.py — Arranca Copiloto y lo abre como una ventana de aplicación.

Qué hace:
  1. Levanta el servidor local (FastAPI/uvicorn) en el puerto 8765.
  2. Intenta abrir una ventana tipo app con Edge o Chrome (--app=...).
     Si no encuentra ninguno, abre la pestaña en tu navegador normal.

Funciona en Windows y Mac. Doble clic en run.bat (Windows) o run.command (Mac),
o desde la terminal:  python launcher.py
"""
import os
import sys
import time
import threading
import subprocess
import webbrowser
import shutil
from pathlib import Path

import uvicorn

PORT = 8765
URL = f"http://127.0.0.1:{PORT}"
ROOT = Path(__file__).resolve().parent

# Para que 'from backend...' funcione siempre, sin importar desde dónde se ejecute.
sys.path.insert(0, str(ROOT))


def start_server():
    from backend.server import app
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")


def find_browser():
    """Devuelve (ruta, es_app). Busca Edge o Chrome para abrir en modo app."""
    candidates = []
    if sys.platform.startswith("win"):
        candidates = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        ]
    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        ]
    else:  # Linux
        for name in ("google-chrome", "chromium", "chromium-browser", "microsoft-edge"):
            p = shutil.which(name)
            if p:
                candidates.append(p)
    for c in candidates:
        if os.path.exists(c):
            return c
    return None


def open_app_window():
    time.sleep(1.6)  # dar tiempo a que el servidor levante
    browser = find_browser()
    profile = ROOT / "data" / "app_profile"
    if browser:
        cmd = [browser, f"--app={URL}", f"--user-data-dir={profile}", "--window-size=440,820"]
        try:
            subprocess.Popen(cmd)
            return
        except Exception:
            pass
    webbrowser.open(URL)  # último recurso: navegador normal


if __name__ == "__main__":
    threading.Thread(target=open_app_window, daemon=True).start()
    print(f"Copiloto corriendo en {URL}")
    print("Desde el teléfono (misma red Wi-Fi): abre http://TU_IP_LOCAL:8765")
    print("Cierra esta ventana para apagar Copiloto.")
    start_server()
