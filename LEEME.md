# Copiloto 🛩️ — tu copiloto de estudio

App de escritorio para estudiar: **panel flotante siempre visible** (encima de
todo, incluso en llamadas), tutor paso a paso, responde con tus propios PDFs,
**búsqueda web gratis con fuentes**, práctica de exposición con puntuación,
flashcards, historial y elección de IA con tu propia clave (guardada **cifrada
y local**) — o **100% gratis y autónoma con Ollama**.

> Nota: Copiloto es **visible** a propósito. Aparece en compartir pantalla y en
> llamadas. No se esconde de nadie; es una herramienta de estudio honesta.

## ⭐ Cómo abrirla como PANEL FLOTANTE (lo que pediste)

- **Windows:** doble clic en **`run_float.bat`**
- **Mac:** doble clic en **`run_float.command`**

La primera vez prepara todo (1–2 min). Luego abre un panel pequeño, **siempre
encima**, que puedes **arrastrar** para moverlo. Arriba tiene botones para
**colapsar** (▁), **ocultar** (—, o atajo **Alt+Espacio**) y **cerrar** (✕).

## 100% gratis y autónoma (sin depender de nadie)

En **⚙️ Ajustes** elige **Ollama** como IA. Ollama corre dentro de tu
computadora, gratis y sin clave. Instálalo una vez desde **ollama.com** y baja un
modelo (ej. en terminal: `ollama pull llama3.1`). Así Copiloto no depende de
ninguna API externa. Gemini/Claude/ChatGPT/Grok siguen disponibles si prefieres,
pero esos sí necesitan internet y tu clave.

## Buscar en la web (gratis, con fuentes)

En el chat activa **🌐 Buscar en la web** y pregunta. Busca en **Wikipedia** y
**DuckDuckGo** (sin claves de pago) y responde citando los enlaces.

---

## 1) Qué necesitas una sola vez

- **Python 3.10 o superior** → https://python.org
  - En Windows, al instalar marca la casilla **"Add Python to PATH"**.
- **Una clave API** de al menos una IA (para que el copiloto "piense"):
  - Claude → console.anthropic.com
  - ChatGPT → platform.openai.com
  - Gemini (tiene nivel gratis) → aistudio.google.com
  - Grok → console.x.ai
  - **Ollama** (100% local y gratis, sin clave) → ollama.com

> Sin clave la app abre, pero el chat no responderá. Gemini y Ollama son las
> opciones gratuitas para empezar.

---

## 2) Cómo ejecutarla (modo fácil, recomendado)

### Windows
1. Descomprime la carpeta `copiloto`.
2. **Doble clic en `run.bat`**.
   - La primera vez prepara todo solo (tarda 1–2 min). Las siguientes abre al instante.
3. Se abre la ventana de Copiloto. Ve a **⚙️ Ajustes**, elige tu IA, pega tu clave y **Guardar**.

### Mac
1. Descomprime la carpeta `copiloto`.
2. **Doble clic en `run.command`** (la primera vez: clic derecho → Abrir, para permitirlo).
3. En **⚙️ Ajustes**, pega tu clave y guarda.

### Desde terminal (cualquier sistema)
```bash
cd copiloto
python -m venv .venv
# Windows:  .venv\Scripts\activate
# Mac:      source .venv/bin/activate
pip install -r backend/requirements.txt
python launcher.py
```

Copiloto corre en **http://127.0.0.1:8765**

---

## 3) Usarla en el teléfono 📱

Con la app corriendo en tu laptop, en el teléfono (misma red Wi-Fi) abre:

```
http://IP_DE_TU_LAPTOP:8765
```

Para saber tu IP: en Windows `ipconfig` (busca "IPv4"); en Mac `ipconfig getifaddr en0`.
En el navegador del teléfono: menú → **"Agregar a pantalla de inicio"** y queda como app (PWA).

---

## 4) Probar que funciona (prueba rápida)

1. **Ajustes** → pega tu clave → Guardar. La bolita se pone verde.
2. **💬 Copiloto** → escribe *"¿Qué es un ensayo y cómo lo hago paso a paso?"* → Enviar.
3. **📄 Documentos** → sube un PDF de clase. Vuelve al chat, activa *"Responder con mis documentos"* y pregunta algo de ese PDF: la respuesta cita el archivo y la página.
4. **🎤 Práctica** → escribe un tema → "Nueva pregunta" → responde (texto o 🎙️) → "Evaluar": te da puntuación y consejos.
5. **🗂️ Flashcards** → elige un documento → "Generar".

---

## 5) Crear el instalador (.exe en Windows / .app en Mac)

Esto genera **un solo archivo ejecutable** para abrir sin terminal.

```bash
cd copiloto
# dentro del entorno (.venv activado)
pip install pyinstaller
```

**Windows** (doble clic en `build.bat`, o a mano):
```bat
pyinstaller --onefile --name Copiloto --add-data "ui;ui" --collect-all uvicorn --collect-all rapidfuzz launcher.py
```

**Mac** (doble clic en `build.command`, o a mano):
```bash
pyinstaller --onefile --name Copiloto --add-data "ui:ui" --collect-all uvicorn --collect-all rapidfuzz launcher.py
```

El ejecutable queda en la carpeta **`dist/`** (`Copiloto.exe` o `Copiloto`).
Tus datos (claves, documentos, historial) se guardan en una carpeta
`CopilotoDatos` junto al ejecutable.

> Nota: la diferencia Windows/Mac es solo el separador del `--add-data`
> (`;` en Windows, `:` en Mac). El `.exe` solo se genera en Windows y el
> `.app`/binario de Mac solo en Mac (cada sistema compila el suyo).

---

## 6) Privacidad y seguridad

- Tus claves se cifran con `cryptography.Fernet` y se guardan en
  `data/keys.vault` (o `CopilotoDatos/keys.vault`). **Nunca** en texto plano.
- Tus documentos y tu historial **no salen de tu computadora**. Solo se envía a
  la IA que elijas el texto necesario para responder tu pregunta.
- Si borras `secret.key`, las claves guardadas dejan de poder leerse (tendrás
  que volver a pegarlas).

---

## 7) Estructura del proyecto

```
copiloto/
├── backend/            # Servidor Python (FastAPI)
│   ├── server.py       # API y endpoints
│   ├── ai_router.py    # Conecta con Claude/OpenAI/Gemini/Grok/Ollama
│   ├── rag.py          # Lee tus PDFs y busca lo relevante (modo Documentos)
│   ├── security.py     # Cifrado de claves
│   ├── store.py        # Historial (SQLite)
│   └── paths.py        # Rutas (funciona compilado o no)
├── ui/                 # Interfaz web + PWA
│   ├── index.html · styles.css · app.js
│   └── manifest.json · sw.js · icon.svg
├── launcher.py         # Arranca el servidor y abre la ventana
├── run.bat / run.command
├── build.bat / build.command
└── backend/requirements.txt
```
