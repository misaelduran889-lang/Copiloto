// ---------- Utilidades ----------
const $ = (s) => document.querySelector(s);
const $$ = (s) => document.querySelectorAll(s);
const api = async (path, opts = {}) => {
  const r = await fetch(path, { headers: { "Content-Type": "application/json" }, ...opts });
  if (!r.ok && r.status >= 500) throw new Error("Error del servidor");
  return r.json();
};
const toast = (msg) => {
  const t = $("#toast"); t.textContent = msg; t.classList.add("show");
  setTimeout(() => t.classList.remove("show"), 2600);
};

const PROVIDERS = [
  { id: "claude", name: "Claude (Anthropic)", model: "claude-sonnet-4-5", help: "console.anthropic.com" },
  { id: "openai", name: "ChatGPT (OpenAI)", model: "gpt-4o-mini", help: "platform.openai.com" },
  { id: "gemini", name: "Gemini (Google)", model: "gemini-2.0-flash", help: "aistudio.google.com" },
  { id: "grok", name: "Grok (xAI)", model: "grok-2-latest", help: "console.x.ai" },
];

let STATE = { chat: [], settings: {}, configured: {} };

// ---------- Navegación ----------
$$(".nav-btn").forEach((btn) => btn.addEventListener("click", () => {
  $$(".nav-btn").forEach((b) => b.classList.remove("active"));
  $$(".view").forEach((v) => v.classList.remove("active"));
  btn.classList.add("active");
  const view = btn.dataset.view;
  $("#view-" + view).classList.add("active");
  if (view === "docs") loadDocs();
  if (view === "history") loadHistory();
  if (view === "cards") loadCardDocs();
}));

// ---------- CHAT ----------
const chatInput = $("#chat-input");
chatInput.addEventListener("input", () => {
  chatInput.style.height = "auto";
  chatInput.style.height = Math.min(chatInput.scrollHeight, 160) + "px";
});
chatInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); }
});
$("#send-btn").addEventListener("click", sendChat);
// toggles mutuamente exclusivos
$("#use-docs").addEventListener("change", () => { if ($("#use-docs").checked) $("#use-web").checked = false; });
$("#use-web").addEventListener("change", () => { if ($("#use-web").checked) $("#use-docs").checked = false; });

function addMsg(role, text, source) {
  const div = document.createElement("div");
  div.className = "msg " + role;
  div.textContent = text;
  if (source) { const s = document.createElement("span"); s.className = "src"; s.textContent = source; div.appendChild(s); }
  $("#chat-log").appendChild(div);
  $("#chat-log").scrollTop = $("#chat-log").scrollHeight;
  return div;
}

async function sendChat() {
  const q = chatInput.value.trim();
  if (!q) return;
  chatInput.value = ""; chatInput.style.height = "auto";
  addMsg("user", q);
  STATE.chat.push({ role: "user", content: q });
  const thinking = addMsg("ai", "Pensando…"); thinking.classList.add("typing");
  let mode = "tutor";
  if ($("#use-docs").checked) mode = "docs";
  else if ($("#use-web").checked) { mode = "web"; thinking.textContent = "Buscando en la web…"; }
  try {
    const res = await api("/api/chat", {
      method: "POST",
      body: JSON.stringify({ mode, query: q, history: STATE.chat.slice(-8, -1) }),
    });
    thinking.classList.remove("typing");
    thinking.textContent = res.text || "Sin respuesta.";
    if (res.answered_from_docs && res.rag?.chunks?.length) {
      const c = res.rag.chunks[0];
      const s = document.createElement("span"); s.className = "src";
      s.textContent = `📌 Basado en tus documentos (${c.filename}, pág. ${c.page})`;
      thinking.appendChild(s);
    } else if (res.answered_from_web && res.web?.results?.length) {
      const box = document.createElement("div"); box.className = "src";
      box.appendChild(document.createTextNode("🔎 Fuentes (toca para verificar):"));
      res.web.results.forEach((r) => {
        const a = document.createElement("a"); a.href = r.url; a.target = "_blank"; a.rel = "noopener";
        a.textContent = "• " + r.title; a.style.display = "block";
        box.appendChild(a);
      });
      thinking.appendChild(box);
    }
    if (res.ok && !res.keyless) STATE.chat.push({ role: "assistant", content: res.text });
  } catch (e) {
    thinking.classList.remove("typing");
    thinking.textContent = "⚠️ No se pudo conectar con el servidor.";
  }
}

// ---------- DOCUMENTOS ----------
const dropzone = $("#dropzone"), fileInput = $("#file-input");
dropzone.addEventListener("click", () => fileInput.click());
dropzone.addEventListener("dragover", (e) => { e.preventDefault(); dropzone.style.borderColor = "var(--accent)"; });
dropzone.addEventListener("dragleave", () => dropzone.style.borderColor = "");
dropzone.addEventListener("drop", (e) => { e.preventDefault(); dropzone.style.borderColor = ""; if (e.dataTransfer.files[0]) uploadFile(e.dataTransfer.files[0]); });
fileInput.addEventListener("change", () => { if (fileInput.files[0]) uploadFile(fileInput.files[0]); });

async function uploadFile(file) {
  toast("Subiendo " + file.name + "…");
  const fd = new FormData(); fd.append("file", file);
  try {
    const r = await fetch("/api/upload", { method: "POST", body: fd });
    const data = await r.json();
    if (data.ok) { toast(`✓ ${data.filename} indexado (${data.pages} págs)`); loadDocs(); }
    else toast("⚠️ " + (data.detail || "No se pudo subir"));
  } catch { toast("⚠️ Error al subir"); }
}

async function loadDocs() {
  const { documents } = await api("/api/documents");
  const list = $("#doc-list");
  list.innerHTML = documents.length ? "" : '<p class="hint">Aún no has subido documentos.</p>';
  documents.forEach((d) => {
    const el = document.createElement("div"); el.className = "item";
    el.innerHTML = `<div><div class="title">📄 ${d.filename}</div>
      <div class="meta">${d.pages} págs · ${(d.chars / 1000).toFixed(1)}k caracteres</div></div>`;
    const btn = document.createElement("button"); btn.className = "icon-btn"; btn.textContent = "Eliminar";
    btn.onclick = async () => { await api("/api/documents/" + encodeURIComponent(d.filename), { method: "DELETE" }); loadDocs(); };
    el.appendChild(btn); list.appendChild(el);
  });
}

// ---------- PRÁCTICA ----------
$("#practice-start").addEventListener("click", async () => {
  const topic = $("#practice-topic").value.trim() || "cultura general aeronáutica";
  const box = $("#practice-question"); box.classList.remove("hidden"); box.textContent = "Generando pregunta…";
  const res = await api("/api/chat", {
    method: "POST",
    body: JSON.stringify({ mode: "tutor", query: `Hazme UNA sola pregunta de entrevista/examen sobre: ${topic}. Devuelve solo la pregunta.` }),
  });
  box.textContent = "🎤 " + (res.text || "¿Puedes presentarte?").trim();
  $("#practice-composer").style.display = "flex";
  $("#practice-feedback").innerHTML = "";
});

$("#practice-send").addEventListener("click", async () => {
  const ans = $("#practice-input").value.trim();
  if (!ans) return;
  const question = $("#practice-question").textContent.replace("🎤 ", "");
  const fb = $("#practice-feedback");
  fb.innerHTML = '<div class="fb-card typing">Evaluando tu respuesta…</div>';
  const res = await api("/api/chat", {
    method: "POST",
    body: JSON.stringify({ mode: "interview", query: `PREGUNTA: ${question}\nMI RESPUESTA: ${ans}` }),
  });
  renderFeedback(res.text || "");
  $("#practice-input").value = "";
});

function renderFeedback(text) {
  const fb = $("#practice-feedback");
  const scoreMatch = text.match(/PUNTUACIÓN:\s*(\d+)/i);
  fb.innerHTML = "";
  if (scoreMatch) {
    const ring = document.createElement("div"); ring.className = "score-ring";
    ring.textContent = scoreMatch[1] + " / 100"; fb.appendChild(ring);
  }
  const card = document.createElement("div"); card.className = "fb-card"; card.textContent = text; fb.appendChild(card);
}

// ---------- FLASHCARDS ----------
async function loadCardDocs() {
  const { documents } = await api("/api/documents");
  const sel = $("#cards-doc");
  sel.innerHTML = documents.map((d) => `<option value="${d.filename}">${d.filename}</option>`).join("")
    || '<option value="">(sube un documento primero)</option>';
}
$("#cards-gen").addEventListener("click", async () => {
  const filename = $("#cards-doc").value;
  if (!filename) { toast("Sube un documento primero"); return; }
  const area = $("#cards-area"); area.innerHTML = '<p class="hint typing">Generando flashcards…</p>';
  const res = await api("/api/flashcards", { method: "POST", body: JSON.stringify({ filename, count: 8 }) });
  area.innerHTML = "";
  if (!res.cards?.length) { area.innerHTML = '<p class="hint">No se pudieron generar. Revisa tu clave en Ajustes.</p>'; return; }
  res.cards.forEach((c) => {
    const card = document.createElement("div"); card.className = "flashcard";
    card.innerHTML = `<div class="flashcard-inner">
      <div class="flashcard-face"><span class="tag">PREGUNTA</span>${c.q}</div>
      <div class="flashcard-face flashcard-back"><span class="tag">RESPUESTA</span>${c.a}</div></div>`;
    card.onclick = () => card.classList.toggle("flipped");
    area.appendChild(card);
  });
});

// ---------- HISTORIAL ----------
async function loadHistory() {
  const { history } = await api("/api/history");
  const list = $("#history-list");
  list.innerHTML = history.length ? "" : '<p class="hint">Aún no hay sesiones guardadas.</p>';
  history.forEach((h) => {
    const el = document.createElement("div"); el.className = "item";
    const date = new Date(h.ts * 1000).toLocaleString("es-DO");
    el.innerHTML = `<div style="cursor:pointer;flex:1"><div class="title">${h.title}</div>
      <div class="meta">${h.mode} · ${date}</div></div>`;
    el.querySelector("div").onclick = async () => {
      const item = await api("/api/history/" + h.id);
      $$(".nav-btn")[0].click();
      $("#chat-log").innerHTML = ""; STATE.chat = [];
      addMsg("user", item.question); addMsg("ai", item.answer);
    };
    const del = document.createElement("button"); del.className = "icon-btn"; del.textContent = "✕";
    del.onclick = async () => { await api("/api/history/" + h.id, { method: "DELETE" }); loadHistory(); };
    el.appendChild(del); list.appendChild(el);
  });
}

// ---------- AJUSTES ----------
function renderKeyInputs() {
  const c = $("#keys-container"); c.innerHTML = "";
  PROVIDERS.forEach((p) => {
    const configured = STATE.configured[p.id];
    const model = STATE.settings.models?.[p.id] || p.model;
    const card = document.createElement("div"); card.className = "settings-card";
    card.innerHTML = `
      <label>${p.name} — clave API <span style="color:var(--muted)">(${p.help})</span></label>
      <div class="key-row">
        <span class="dot ${configured ? "on" : ""}"></span>
        <input type="password" data-key="${p.id}" placeholder="${configured ? "•••• guardada (deja vacío para conservar)" : "Pega tu clave aquí"}" />
      </div>
      <input class="model-input" data-model="${p.id}" value="${model}" placeholder="modelo" />`;
    c.appendChild(card);
  });
}

$("#save-settings").addEventListener("click", async () => {
  // Guardar claves (solo las que el usuario escribió)
  for (const inp of $$("[data-key]")) {
    if (inp.value.trim()) await api("/api/keys", { method: "POST", body: JSON.stringify({ provider: inp.dataset.key, api_key: inp.value.trim() }) });
  }
  const models = {};
  $$("[data-model]").forEach((inp) => { models[inp.dataset.model] = inp.value.trim(); });
  await api("/api/settings", { method: "POST", body: JSON.stringify({
    default_provider: $("#default-provider").value,
    models,
    ollama_url: $("#ollama-url").value.trim() || "http://127.0.0.1:11434",
  }) });
  toast("✓ Ajustes guardados");
  await loadStatus();
});

async function loadStatus() {
  const s = await api("/api/keys/status");
  STATE.configured = s.configured || {};
  STATE.settings = s.settings || {};
  $("#default-provider").value = STATE.settings.default_provider || "claude";
  $("#ollama-url").value = STATE.settings.ollama_url || "http://127.0.0.1:11434";
  renderKeyInputs();
  const anyKey = Object.values(STATE.configured).some(Boolean);
  const pill = $("#provider-pill");
  if (anyKey) { pill.textContent = "IA: " + (STATE.settings.default_provider || "claude"); pill.classList.add("ok"); }
  else { pill.textContent = "Sin clave"; pill.classList.remove("ok"); }
}

// ---------- VOZ (Web Speech API) ----------
function setupMic(btnSel, targetSel) {
  const btn = $(btnSel);
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) { btn.style.display = "none"; return; }
  const rec = new SR(); rec.lang = "es-ES"; rec.continuous = false; rec.interimResults = true;
  let on = false;
  btn.addEventListener("click", () => { on ? rec.stop() : rec.start(); });
  rec.onstart = () => { on = true; btn.classList.add("rec"); };
  rec.onend = () => { on = false; btn.classList.remove("rec"); };
  rec.onresult = (e) => {
    let txt = ""; for (let i = 0; i < e.results.length; i++) txt += e.results[i][0].transcript;
    $(targetSel).value = txt;
  };
}
setupMic("#mic-btn", "#chat-input");
setupMic("#practice-mic", "#practice-input");

// ---------- Atajo mostrar/ocultar (Alt+Espacio en navegador; el real lo pone el lanzador) ----------
document.addEventListener("keydown", (e) => {
  if (e.altKey && e.code === "Space") { e.preventDefault(); window.focus(); }
});

// ---------- Barra flotante (app de escritorio) ----------
const isDesktop = new URLSearchParams(location.search).get("desktop") === "1";
if (isDesktop) {
  document.body.classList.add("desktop");
  $("#floatbar").classList.remove("hidden");
  const callApi = (fn) => { try { if (window.pywebview?.api?.[fn]) window.pywebview.api[fn](); } catch (e) {} };
  const tuck = () => { // esconder como burbuja en la esquina
    callApi("tuck");
    $("#app").classList.add("hidden");
    $("#floatbar").classList.add("hidden");
    $("#bubble").classList.remove("hidden");
  };
  const restore = () => { // volver al panel completo
    callApi("restore");
    $("#bubble").classList.add("hidden");
    $("#app").classList.remove("hidden");
    $("#floatbar").classList.remove("hidden");
  };
  $("#fb-tuck").addEventListener("click", tuck);
  $("#bubble").addEventListener("click", restore);
  $("#fb-hide").addEventListener("click", () => callApi("hide"));
  $("#fb-close").addEventListener("click", () => { if (confirm("¿Cerrar Copiloto?")) callApi("close_app"); });
}

// ---------- PWA (solo en navegador normal) ----------
if (!isDesktop && "serviceWorker" in navigator) navigator.serviceWorker.register("/sw.js").catch(() => {});

// ---------- Inicio ----------
loadStatus();
