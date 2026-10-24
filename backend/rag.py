"""
rag.py — Modo Documentos.

- Extrae texto de PDF, DOCX y TXT.
- Lo trocea en fragmentos con número de página.
- Busca los fragmentos más parecidos a la pregunta con rapidfuzz (sin API de pago,
  sin modelos pesados: funciona en cualquier laptop).
- El índice se guarda en data/index.json para que sobreviva al reinicio.

Decide si la pregunta "tiene relación" con los documentos midiendo la puntuación
del mejor fragmento: si es baja, el router responderá de forma general.
"""
import json
import re
from pathlib import Path
from rapidfuzz import fuzz
from .paths import DATA_DIR

INDEX_FILE = DATA_DIR / "index.json"
UPLOAD_DIR = DATA_DIR / "uploads"

# Umbral: por debajo de esto consideramos que la pregunta NO va de los documentos.
RELEVANCE_THRESHOLD = 55.0


def _load_index() -> list[dict]:
    if INDEX_FILE.exists():
        try:
            return json.loads(INDEX_FILE.read_text("utf-8"))
        except Exception:
            return []
    return []


def _save_index(chunks: list[dict]) -> None:
    INDEX_FILE.write_text(json.dumps(chunks, ensure_ascii=False), "utf-8")


_INDEX: list[dict] = _load_index()


# ---------- Extracción de texto ----------
def extract_pages(path: Path) -> list[str]:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _pdf_pages(path)
    if ext == ".docx":
        return _docx_pages(path)
    if ext in (".txt", ".md"):
        return [path.read_text("utf-8", errors="ignore")]
    raise ValueError(f"Formato no soportado: {ext}")


def _pdf_pages(path: Path) -> list[str]:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    return [(p.extract_text() or "") for p in reader.pages]


def _docx_pages(path: Path) -> list[str]:
    import docx
    d = docx.Document(str(path))
    text = "\n".join(p.text for p in d.paragraphs)
    # DOCX no tiene páginas fiables; troceamos por bloques de ~1500 caracteres.
    blocks, cur = [], ""
    for para in text.split("\n"):
        cur += para + "\n"
        if len(cur) > 1500:
            blocks.append(cur)
            cur = ""
    if cur.strip():
        blocks.append(cur)
    return blocks or [text]


def _chunk_page(text: str, size: int = 600, overlap: int = 100) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks, i = [], 0
    while i < len(text):
        chunks.append(text[i:i + size])
        i += size - overlap
    return chunks


# ---------- Indexar ----------
def add_document(filename: str, pages: list[str]) -> dict:
    global _INDEX
    _INDEX = [c for c in _INDEX if c["filename"] != filename]  # reindexar si ya existía
    chars = 0
    for page_no, page_text in enumerate(pages, start=1):
        for chunk in _chunk_page(page_text):
            chars += len(chunk)
            _INDEX.append({"filename": filename, "page": page_no, "text": chunk})
    _save_index(_INDEX)
    return {"pages": len(pages), "chars": chars}


def remove_document(filename: str) -> None:
    global _INDEX
    _INDEX = [c for c in _INDEX if c["filename"] != filename]
    _save_index(_INDEX)


# ---------- Buscar ----------
def search(query: str, top_k: int = 4) -> dict:
    """Devuelve {relevant: bool, chunks: [...], best_score: float}."""
    if not _INDEX or not query.strip():
        return {"relevant": False, "chunks": [], "best_score": 0.0}
    q = query.lower()
    scored = []
    for c in _INDEX:
        score = fuzz.token_set_ratio(q, c["text"].lower())
        scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:top_k]
    best = top[0][0] if top else 0.0
    chunks = [
        {"filename": c["filename"], "page": c["page"], "text": c["text"], "score": round(s, 1)}
        for s, c in top
    ]
    return {"relevant": best >= RELEVANCE_THRESHOLD, "chunks": chunks, "best_score": round(best, 1)}
