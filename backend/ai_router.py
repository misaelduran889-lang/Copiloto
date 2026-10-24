"""
ai_router.py — El "cerebro". Enruta la consulta al proveedor elegido usando la
clave API del usuario (guardada cifrada). Soporta:

    - claude  -> API de Anthropic
    - openai  -> API de OpenAI (y cualquier endpoint compatible)
    - gemini  -> API de Google Gemini
    - grok    -> API de xAI (compatible con OpenAI)
    - ollama  -> modelo LOCAL y gratis (no necesita clave)

El tono es de PROFESOR: explica paso a paso, en español, claro, para que el
usuario comprenda de verdad. En modo Documentos, responde pegado a los
fragmentos y cita la fuente (archivo + página).
"""
import httpx
from . import security

# Modelos por defecto (el usuario los puede cambiar en Ajustes).
DEFAULT_MODELS = {
    "claude": "claude-sonnet-4-5",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-3.8-flash",
    "grok": "grok-2-latest",
    "ollama": "llama3.1",
}

OLLAMA_DEFAULT_URL = "http://127.0.0.1:11434"


# ---------------- Prompts (personalidad del copiloto) ----------------
TUTOR_SYSTEM = (
    "Eres Copiloto, el asistente de estudio personal de un estudiante de "
    "Administración Aeronáutica en República Dominicana. Hablas SIEMPRE en español "
    "claro y cercano. Tu objetivo es que la persona COMPRENDA, como lo haría un "
    "profesor excelente y paciente.\n\n"
    "Reglas:\n"
    "- Explica paso a paso. Si piden 'cómo hacer X', da pasos numerados concretos.\n"
    "- Usa ejemplos sencillos y aterrizados al mundo real (preferible, aeronáutico).\n"
    "- No inventes datos. Si no estás seguro, dilo y propone cómo verificarlo.\n"
    "- Sé directo y útil; evita relleno. Termina invitando a la siguiente duda.\n"
)

DOCS_SYSTEM = (
    TUTOR_SYSTEM
    + "\nAhora respondes APOYÁNDOTE en fragmentos de los documentos del usuario que "
    "te paso abajo. Prioriza esa información. Al final añade SIEMPRE una línea de "
    "fuente con este formato exacto:\n"
    "📌 Fuente: [NOMBRE_ARCHIVO] (pág. [N])\n"
    "Si la pregunta no se responde con los fragmentos, dilo y responde con tu "
    "conocimiento general, aclarando que no venía en los documentos."
)

INTERVIEW_SYSTEM = (
    "Eres un entrenador de comunicación oral. Ayudas al usuario a practicar "
    "entrevistas y exposiciones en español para perder el pánico escénico. "
    "Analiza la respuesta que te den y devuelve EXACTAMENTE este formato:\n\n"
    "PUNTUACIÓN: N/100\n"
    "CLARIDAD: una frase.\n"
    "ORDEN: una frase.\n"
    "MULETILLAS: lista las que notes (o 'ninguna').\n"
    "CONTENIDO: una frase sobre si respondió lo preguntado.\n"
    "CONSEJO: un consejo concreto para mejorar.\n"
    "SIGUIENTE PREGUNTA: una nueva pregunta para seguir practicando.\n\n"
    "Sé honesto pero motivador. No regales la puntuación."
)

WEB_SYSTEM = (
    TUTOR_SYSTEM
    + "\nAhora tienes RESULTADOS DE BÚSQUEDA WEB en vivo. Responde apoyándote en ellos, "
    "con tus palabras y en tono claro. Al final añade SIEMPRE las fuentes así:\n"
    "🔎 Fuentes:\n- [Título] (enlace)\n"
    "Si los resultados no alcanzan, dilo y complementa con tu conocimiento general."
)

SYSTEM_BY_MODE = {
    "tutor": TUTOR_SYSTEM,
    "docs": DOCS_SYSTEM,
    "interview": INTERVIEW_SYSTEM,
    "web": WEB_SYSTEM,
}


def _model_for(provider: str) -> str:
    settings = security.get_settings()
    models = settings.get("models", {})
    return models.get(provider) or DEFAULT_MODELS.get(provider, "")


def _build_messages(mode: str, query: str, rag: dict | None, history: list | None,
                    web_context: str | None = None):
    system = SYSTEM_BY_MODE.get(mode, TUTOR_SYSTEM)
    user_content = query
    if mode == "docs" and rag and rag.get("chunks"):
        ctx = "\n\n".join(
            f"[{c['filename']} · pág. {c['page']}]\n{c['text']}" for c in rag["chunks"]
        )
        user_content = f"FRAGMENTOS DE MIS DOCUMENTOS:\n{ctx}\n\nPREGUNTA:\n{query}"
    elif mode == "web" and web_context:
        user_content = f"{web_context}\n\nPREGUNTA:\n{query}"
    msgs = list(history or [])
    msgs.append({"role": "user", "content": user_content})
    return system, msgs


async def generate(mode: str, query: str, rag: dict | None = None,
                   history: list | None = None, provider: str | None = None,
                   web_context: str | None = None) -> dict:
    settings = security.get_settings()
    provider = provider or settings.get("default_provider", "claude")
    system, msgs = _build_messages(mode, query, rag, history, web_context)
    try:
        if provider == "claude":
            text = await _call_claude(system, msgs)
        elif provider in ("openai", "grok"):
            text = await _call_openai_compatible(provider, system, msgs)
        elif provider == "gemini":
            text = await _call_gemini(system, msgs)
        elif provider == "ollama":
            text = await _call_ollama(system, msgs)
        else:
            return {"ok": False, "text": f"Proveedor desconocido: {provider}"}
        return {"ok": True, "text": text, "provider": provider, "model": _model_for(provider)}
    except httpx.HTTPStatusError as e:
        detail = e.response.text[:400]
        return {"ok": False, "text": f"⚠️ Error del proveedor {provider} ({e.response.status_code}). "
                                     f"Revisa tu clave o el nombre del modelo en Ajustes.\n\n{detail}"}
    except Exception as e:
        return {"ok": False, "text": f"⚠️ No se pudo conectar con {provider}: {e}"}


# ---------------- Llamadas por proveedor ----------------
async def _call_claude(system: str, msgs: list) -> str:
    key = security.get_key("claude")
    if not key:
        raise RuntimeError("Falta la clave de Claude. Ponla en Ajustes.")
    payload = {
        "model": _model_for("claude"),
        "max_tokens": 1500,
        "system": system,
        "messages": [{"role": m["role"], "content": m["content"]} for m in msgs],
    }
    headers = {"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post("https://api.anthropic.com/v1/messages", json=payload, headers=headers)
        r.raise_for_status()
        data = r.json()
        return "".join(b.get("text", "") for b in data.get("content", []))


async def _call_openai_compatible(provider: str, system: str, msgs: list) -> str:
    key = security.get_key(provider)
    if not key:
        raise RuntimeError(f"Falta la clave de {provider}. Ponla en Ajustes.")
    base = "https://api.openai.com/v1" if provider == "openai" else "https://api.x.ai/v1"
    payload = {
        "model": _model_for(provider),
        "messages": [{"role": "system", "content": system}] + msgs,
        "max_tokens": 1500,
    }
    headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(f"{base}/chat/completions", json=payload, headers=headers)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]


async def _call_gemini(system: str, msgs: list) -> str:
    key = security.get_key("gemini")
    if not key:
        raise RuntimeError("Falta la clave de Gemini. Ponla en Ajustes.")
    model = _model_for("gemini")
    contents = []
    for m in msgs:
        role = "user" if m["role"] == "user" else "model"
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    payload = {"system_instruction": {"parts": [{"text": system}]}, "contents": contents}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        return "".join(p.get("text", "") for p in data["candidates"][0]["content"]["parts"])


async def _call_ollama(system: str, msgs: list) -> str:
    settings = security.get_settings()
    base = settings.get("ollama_url", OLLAMA_DEFAULT_URL)
    payload = {
        "model": _model_for("ollama"),
        "messages": [{"role": "system", "content": system}] + msgs,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=120) as client:
        r = await client.post(f"{base}/api/chat", json=payload)
        r.raise_for_status()
        return r.json()["message"]["content"]
