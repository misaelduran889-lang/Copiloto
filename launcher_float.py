"""
launcher_float.py — Copiloto como PANEL FLOTANTE TRANSPARENTE siempre encima.

Estilo Cluely: un panel de vidrio translúcido que flota ENCIMA de todo (tu
navegador, un video de YouTube, otra app), que puedes:
  - mover arrastrándolo a donde quieras,
  - esconder en una esquina (se vuelve una burbujita ✦),
  - traer de vuelta tocando la burbuja o con Alt+Espacio.

Es VISIBLE a propósito (aparece en compartir pantalla). Por dentro corre el
servidor local de Copiloto (búsqueda web gratis, documentos, IA opcional).

Ejecutar:  python launcher_float.py
"""
import sys
import time
import threading
from pathlib import Path

import uvicorn
import webview  # pywebview

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

PORT = 8765
URL = f"http://127.0.0.1:{PORT}/?desktop=1"

FULL = (430, 780)     # panel completo
BUBBLE = (64, 64)     # burbuja en la esquina


def start_server():
    from backend.server import app
    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


def wait_server(timeout=15):
    import urllib.request
    start = time.time()
    while time.time() - start < timeout:
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/keys/status", timeout=1)
            return True
        except Exception:
            time.sleep(0.4)
    return False


def _screen_size():
    try:
        s = webview.screens[0]
        return s.width, s.height
    except Exception:
        return 1920, 1080


class Api:
    """Funciones que la interfaz llama con window.pywebview.api.*"""
    def __init__(self):
        self.window = None
        self.tucked = False
        self.last_pos = (None, 60)

    def tuck(self):
        """Esconde el panel como una burbuja en la esquina superior derecha."""
        if not self.window:
            return True
        sw, sh = _screen_size()
        self.window.resize(*BUBBLE)
        try:
            self.window.move(sw - BUBBLE[0] - 20, 20)
        except Exception:
            pass
        self.tucked = True
        return True

    def restore(self):
        """Vuelve al panel completo."""
        if not self.window:
            return False
        self.window.resize(*FULL)
        try:
            sw, _ = _screen_size()
            self.window.move(sw - FULL[0] - 30, 60)
        except Exception:
            pass
        self.tucked = False
        return False

    def hide(self):
        if self.window:
            self.window.hide()

    def close_app(self):
        if self.window:
            self.window.destroy()


def setup_global_hotkey(window):
    """Alt+Espacio para mostrar/ocultar (requiere la librería 'keyboard', opcional)."""
    try:
        import keyboard
    except Exception:
        return
    state = {"visible": True}

    def toggle():
        try:
            window.show() if not state["visible"] else window.hide()
            state["visible"] = not state["visible"]
        except Exception:
            pass

    try:
        keyboard.add_hotkey("alt+space", toggle)
    except Exception:
        pass


if __name__ == "__main__":
    threading.Thread(target=start_server, daemon=True).start()
    if not wait_server():
        print("No se pudo iniciar el servidor de Copiloto.")
        sys.exit(1)

    sw, sh = _screen_size()
    api = Api()
    window = webview.create_window(
        "Copiloto",
        URL,
        js_api=api,
        width=FULL[0], height=FULL[1],
        x=sw - FULL[0] - 30, y=60,     # arranca pegado a la derecha
        frameless=True,
        easy_drag=True,                # mover arrastrando
        on_top=True,                   # SIEMPRE ENCIMA
        resizable=True,
        transparent=True,              # VIDRIO: se ve lo de atrás
        background_color="#00000000",
    )
    api.window = window
    threading.Thread(target=setup_global_hotkey, args=(window,), daemon=True).start()
    webview.start()
