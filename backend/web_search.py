"""
web_search.py — Búsqueda web GRATIS, sin claves de pago.

Fuentes (en orden):
  1. Wikipedia en español (API oficial, confiable, con enlace a la página).
  2. DuckDuckGo (resultados HTML) como respaldo para temas que no estén en Wikipedia.

Devuelve resultados con título, enlace y resumen, para que el copiloto responda
"pegado a la fuente" y SIEMPRE cite de dónde salió. Todo corre en la computadora
del usuario; aquí no hay API de pago.
"""
import re
import json
import urllib.parse
import httpx

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Copiloto/1.0"}
TIMEOUT = 6.0


def search(query: str, max_results: int = 4) -> dict:
    clean = re.sub(r"[¿?¡!]", "", query or "").strip()
    if not clean:
        return {"query": "", "results": [], "source": None}
    results = _wikipedia(clean, max_results)
    source = "wikipedia"
    if not results:
        results = _duckduckgo(clean, max_results)
        source = "duckduckgo"
    return {"query": clean, "results": results, "source": source if results else None}


def _wikipedia(query: str, max_results: int) -> list:
    try:
        with httpx.Client(timeout=TIMEOUT, headers=HEADERS, follow_redirects=True) as c:
            # 1) buscar títulos relevantes
            url = ("https://es.wikipedia.org/w/api.php?action=query&list=search"
                   f"&srsearch={urllib.parse.quote(query)}&format=json&utf8=1&srlimit={max_results}")
            data = c.get(url).json()
            items = data.get("query", {}).get("search", [])
            if not items:
                return []
            out = []
            for it in items[:max_results]:
                title = it["title"]
                # 2) traer un extracto limpio de cada página
                ex_url = ("https://es.wikipedia.org/w/api.php?action=query&prop=extracts"
                          "&exintro=1&explaintext=1&format=json&utf8=1&redirects=1"
                          f"&titles={urllib.parse.quote(title)}")
                ex = c.get(ex_url).json()
                pages = ex.get("query", {}).get("pages", {})
                extract = ""
                for _, p in pages.items():
                    extract = (p.get("extract") or "").strip()
                if not extract:
                    extract = re.sub(r"<[^>]+>", "", it.get("snippet", ""))
                link = f"https://es.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                out.append({"title": title, "url": link, "snippet": extract[:700]})
            return out
    except Exception:
        return []


def _duckduckgo(query: str, max_results: int) -> list:
    try:
        with httpx.Client(timeout=TIMEOUT, headers=HEADERS, follow_redirects=True) as c:
            r = c.post("https://html.duckduckgo.com/html/", data={"q": query})
            html = r.text
        blocks = re.findall(
            r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>.*?'
            r'(?:class="result__snippet"[^>]*>(.*?)</a>)?',
            html, re.DOTALL)
        out = []
        for href, title, snip in blocks[:max_results]:
            title = re.sub(r"<[^>]+>", "", title).strip()
            snip = re.sub(r"<[^>]+>", "", snip or "").strip()
            # DDG envuelve la URL real en un redirect; la extraemos
            m = re.search(r"uddg=([^&]+)", href)
            real = urllib.parse.unquote(m.group(1)) if m else href
            if title:
                out.append({"title": title, "url": real, "snippet": snip[:500]})
        return out
    except Exception:
        return []


def format_for_ai(result: dict) -> str:
    """Convierte los resultados en contexto para el modelo, con enlaces citables."""
    if not result.get("results"):
        return ""
    lines = []
    for i, r in enumerate(result["results"], 1):
        lines.append(f"[{i}] {r['title']}\n{r['snippet']}\nEnlace: {r['url']}")
    return "RESULTADOS DE BÚSQUEDA WEB (úsalos y cita el enlace):\n\n" + "\n\n".join(lines)
