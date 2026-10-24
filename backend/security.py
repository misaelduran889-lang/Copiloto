"""
security.py — Guarda las claves API del usuario CIFRADAS y LOCALES.

Usa cryptography.Fernet. La clave de cifrado se genera una sola vez y se guarda
en data/secret.key (permisos 600 en Mac/Linux). Las claves de los proveedores
(Claude, OpenAI, Gemini, Grok) nunca se guardan en texto plano.
"""
import os
import json
from cryptography.fernet import Fernet
from .paths import DATA_DIR

KEY_FILE = DATA_DIR / "secret.key"
VAULT_FILE = DATA_DIR / "keys.vault"


def _load_or_create_master_key() -> bytes:
    if KEY_FILE.exists():
        return KEY_FILE.read_bytes()
    master = Fernet.generate_key()
    KEY_FILE.write_bytes(master)
    try:
        os.chmod(KEY_FILE, 0o600)
    except Exception:
        pass  # Windows no siempre soporta chmod; el archivo queda en la carpeta local del usuario
    return master


_fernet = Fernet(_load_or_create_master_key())


def _read_vault() -> dict:
    if not VAULT_FILE.exists():
        return {}
    try:
        raw = _fernet.decrypt(VAULT_FILE.read_bytes())
        return json.loads(raw.decode("utf-8"))
    except Exception:
        return {}


def _write_vault(data: dict) -> None:
    blob = _fernet.encrypt(json.dumps(data).encode("utf-8"))
    VAULT_FILE.write_bytes(blob)
    try:
        os.chmod(VAULT_FILE, 0o600)
    except Exception:
        pass


def set_key(provider: str, api_key: str) -> None:
    """Guarda (cifrada) la clave de un proveedor."""
    vault = _read_vault()
    if api_key:
        vault[provider] = api_key
    else:
        vault.pop(provider, None)
    _write_vault(vault)


def get_key(provider: str) -> str:
    return _read_vault().get(provider, "")


def set_settings(settings: dict) -> None:
    """Guarda ajustes NO secretos (proveedor por defecto, modelo, url de Ollama)."""
    vault = _read_vault()
    vault["_settings"] = settings
    _write_vault(vault)


def get_settings() -> dict:
    return _read_vault().get("_settings", {})


def status() -> dict:
    """Qué proveedores tienen clave guardada (sin revelar la clave)."""
    vault = _read_vault()
    providers = ["claude", "openai", "gemini", "grok"]
    return {
        "configured": {p: bool(vault.get(p)) for p in providers},
        "settings": vault.get("_settings", {}),
    }
