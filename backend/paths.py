"""
paths.py — Resuelve dónde están la interfaz (solo lectura) y los datos
(escritura), funcione la app como script normal o empaquetada con PyInstaller.

- UI_DIR  : archivos de la interfaz (se incluyen dentro del .exe al compilar).
- DATA_DIR: claves, documentos, historial. SIEMPRE junto al ejecutable / proyecto,
            para que sea escribible y los datos del usuario queden a la vista.
"""
import sys
from pathlib import Path

_FROZEN = getattr(sys, "frozen", False)

if _FROZEN:
    # Ejecutable PyInstaller: la UI va dentro del bundle (_MEIPASS); los datos van
    # junto al .exe/.app para poder escribir y para que el usuario los encuentre.
    BUNDLE = Path(sys._MEIPASS)              # type: ignore[attr-defined]
    UI_DIR = BUNDLE / "ui"
    DATA_DIR = Path(sys.executable).resolve().parent / "CopilotoDatos"
else:
    ROOT = Path(__file__).resolve().parent.parent
    UI_DIR = ROOT / "ui"
    DATA_DIR = ROOT / "data"

DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "uploads").mkdir(parents=True, exist_ok=True)
