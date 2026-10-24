"""
store.py — Historial de sesiones y metadatos de documentos en SQLite local.
Todo queda en data/copiloto.db, en la computadora del usuario.
"""
import sqlite3
import json
import time
from .paths import DATA_DIR

DB_PATH = DATA_DIR / "copiloto.db"


def _conn():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    return c


def init_db():
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL,
                mode TEXT,
                title TEXT,
                question TEXT,
                answer TEXT,
                meta TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                filename TEXT PRIMARY KEY,
                ts REAL,
                pages INTEGER,
                chars INTEGER
            )
        """)


def add_history(mode: str, question: str, answer: str, title: str = "", meta: dict | None = None) -> int:
    with _conn() as c:
        cur = c.execute(
            "INSERT INTO history (ts, mode, title, question, answer, meta) VALUES (?,?,?,?,?,?)",
            (time.time(), mode, title or question[:60], question, answer, json.dumps(meta or {})),
        )
        return cur.lastrowid


def list_history(limit: int = 50) -> list[dict]:
    with _conn() as c:
        rows = c.execute(
            "SELECT id, ts, mode, title, question, answer FROM history ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def get_history_item(item_id: int) -> dict | None:
    with _conn() as c:
        r = c.execute("SELECT * FROM history WHERE id=?", (item_id,)).fetchone()
        return dict(r) if r else None


def delete_history(item_id: int) -> None:
    with _conn() as c:
        c.execute("DELETE FROM history WHERE id=?", (item_id,))


def upsert_document(filename: str, pages: int, chars: int) -> None:
    with _conn() as c:
        c.execute(
            "INSERT OR REPLACE INTO documents (filename, ts, pages, chars) VALUES (?,?,?,?)",
            (filename, time.time(), pages, chars),
        )


def list_documents() -> list[dict]:
    with _conn() as c:
        rows = c.execute("SELECT filename, ts, pages, chars FROM documents ORDER BY ts DESC").fetchall()
        return [dict(r) for r in rows]


def delete_document(filename: str) -> None:
    with _conn() as c:
        c.execute("DELETE FROM documents WHERE filename=?", (filename,))


init_db()
