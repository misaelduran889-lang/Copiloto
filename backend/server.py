"""
server.py — Servidor local de Copiloto (FastAPI, puerto 8765).
Sirve la interfaz y expone la API. Todo corre en la computadora del usuario.
"""
import os
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import security, store, rag, ai_router, web_search
from .paths import UI_DIR, DATA_DIR

UPLOAD_DIR = DATA_DIR / "uploads"

app = FastAPI(title="Copiloto")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


# ---------------- Modelos de petición ----------------
class ChatRequest(BaseModel):
    mode: str = "tutor"          # tutor | docs | interview | web
    query: str
    provider: str | None = None
    history: list | None = None


class KeyRequest(BaseModel):
    provider: str
    api_key: str


class SettingsRequest(BaseModel):
    default_provider: str | None = None
    models: dict | None = None
    ollama_url: str | None = None


class FlashcardRequest(BaseModel):
    filename: str | None = None
    count: int = 8
    provider: str | None = None


# ---------------- Claves y ajustes ----------------
@app.get("/api/keys/status")
async def keys_status():
    return security.status()


@app.post("/api/keys")
async def save_key(req: KeyRequest):
    security.set_key(req.provider, req.api_key)
    return {"ok": True}


@app.post("/api/settings")
async def save_settings(req: SettingsRequest):
    current = security.get_settings()
    if req.default_provider is not None:
        current["default_provider"] = req.default_provider
    if req.models is not None:
        current["models"] = {**current.get("models", {}), **req.models}
    if req.ollama_url is not None:
        current["ollama_url"] = req.ollama_url
    security.set_settings(current)
    return {"ok": True, "settings": current}


# ---------------- Chat (tutor / documentos / entrevista) ----------------
@app.post("/api/chat")
async def chat(req: ChatRequest):
    if not req.query.strip():
        raise HTTPException(400, "Pregunta vacía")
    rag_result = None
    web_result = None
    web_context = None
    mode = req.mode

    # ¿Hay una IA lista? (clave guardada, u Ollama local)
    settings = security.get_settings()
    provider = req.provider or settings.get("default_provider", "gemini")
    has_ai = provider == "ollama" or bool(security.get_key(provider))

    if mode == "docs":
        rag_result = rag.search(req.query, top_k=4)
        if not rag_result["relevant"]:
            mode = "tutor"
    elif mode == "web" or not has_ai:
        # Sin IA, SIEMPRE buscamos en la web (gratis, sin clave).
        mode = "web"
        web_result = web_search.search(req.query, max_results=4)
        if web_result["results"]:
            web_context = web_search.format_for_ai(web_result)
        elif has_ai:
            mode = "tutor"

    # KEYLESS: sin IA -> devolvemos directamente lo que encontró la web + fuentes.
    if not has_ai:
        if web_result and web_result["results"]:
            text = web_result["results"][0]["snippet"]
        else:
            text = ("No encontré resultados en la web para eso. Prueba con otras palabras, "
                    "o pon una clave de IA (o usa Ollama) en Ajustes para conversar.")
        store.add_history(req.mode, req.query, text, meta={"keyless": True})
        return {"ok": True, "text": text, "provider": "web", "rag": rag_result,
                "web": web_result, "answered_from_docs": False,
                "answered_from_web": bool(web_result and web_result.get("results")),
                "keyless": True}

    result = await ai_router.generate(
        mode=mode, query=req.query, rag=rag_result,
        history=req.history, provider=req.provider, web_context=web_context,
    )
    if result.get("ok"):
        store.add_history(req.mode, req.query, result["text"],
                          meta={"provider": result.get("provider"),
                                "used_docs": bool(rag_result and rag_result["relevant"])})
    return {
        **result,
        "rag": rag_result,
        "web": web_result,
        "answered_from_docs": bool(rag_result and rag_result["relevant"]),
        "answered_from_web": bool(web_result and web_result.get("results")),
    }


# ---------------- Documentos ----------------
@app.post("/api/upload")
async def upload(file: UploadFile = File(...)):
    dest = UPLOAD_DIR / file.filename
    dest.write_bytes(await file.read())
    try:
        pages = rag.extract_pages(dest)
    except ValueError as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, str(e))
    info = rag.add_document(file.filename, pages)
    store.upsert_document(file.filename, info["pages"], info["chars"])
    return {"ok": True, "filename": file.filename, **info}


@app.get("/api/documents")
async def documents():
    return {"documents": store.list_documents()}


@app.delete("/api/documents/{filename}")
async def delete_document(filename: str):
    rag.remove_document(filename)
    store.delete_document(filename)
    (UPLOAD_DIR / filename).unlink(missing_ok=True)
    return {"ok": True}


# ---------------- Flashcards ----------------
@app.post("/api/flashcards")
async def flashcards(req: FlashcardRequest):
    docs = store.list_documents()
    if not docs:
        raise HTTPException(400, "Sube al menos un documento primero.")
    target = req.filename or docs[0]["filename"]
    probe = rag.search(target, top_k=6)
    context = "\n\n".join(c["text"] for c in probe["chunks"]) if probe["chunks"] else ""
    if not context:
        # tomar cualquier fragmento del archivo
        hits = [c for c in rag._INDEX if c["filename"] == target][:6]
        context = "\n\n".join(c["text"] for c in hits)
    prompt = (
        f"A partir de este material de estudio, crea {req.count} flashcards "
        f"(pregunta y respuesta) para memorizar lo esencial. Devuelve SOLO líneas "
        f"con el formato:\nP: <pregunta>\nR: <respuesta>\n\nMATERIAL:\n{context}"
    )
    result = await ai_router.generate(mode="tutor", query=prompt, provider=req.provider)
    cards = _parse_flashcards(result.get("text", ""))
    return {"ok": result.get("ok", False), "filename": target, "cards": cards,
            "raw": result.get("text", "")}


def _parse_flashcards(text: str) -> list[dict]:
    cards, q = [], None
    for line in text.splitlines():
        s = line.strip()
        if s.upper().startswith("P:"):
            q = s[2:].strip()
        elif s.upper().startswith("R:") and q:
            cards.append({"q": q, "a": s[2:].strip()})
            q = None
    return cards


# ---------------- Historial ----------------
@app.get("/api/history")
async def history():
    return {"history": store.list_history()}


@app.get("/api/history/{item_id}")
async def history_item(item_id: int):
    item = store.get_history_item(item_id)
    if not item:
        raise HTTPException(404, "No encontrado")
    return item


@app.delete("/api/history/{item_id}")
async def delete_history(item_id: int):
    store.delete_history(item_id)
    return {"ok": True}


# ---------------- Servir la interfaz (siempre al final) ----------------
app.mount("/", StaticFiles(directory=str(UI_DIR), html=True), name="ui")
