/* ============================================================
   BookSmart — frontend logic (vanilla JS, no frameworks)
   ============================================================ */

// ---------- state ----------
const state = {
  books: [],
  currentBook: null,
  page: 1,
  pageText: "",       // raw text of the current page (for word context)
  fontSize: 16.5,
  tab: "chat",
  brainAudio: null,   // dedicated Audio element for brain frequencies
  brainPreset: null,
  brainMinutes: 10,
};

// ---------- helpers ----------
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: opts.body && !(opts.body instanceof FormData) ? { "Content-Type": "application/json" } : {},
    ...opts,
    body: opts.body instanceof FormData ? opts.body : opts.body ? JSON.stringify(opts.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || "Something went wrong");
  return data;
}

function toast(msg, ms = 4000) {
  const t = $("#toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(t._h);
  t._h = setTimeout(() => (t.hidden = true), ms);
}

function esc(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function showView(name) {
  $$(".view").forEach((v) => (v.hidden = v.id !== `view-${name}`));
  $$(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
}

// ============================================================
// HEALTH / LLM status
// ============================================================
async function refreshHealth() {
  try {
    const h = await api("/api/health");
    const dot = $("#llm-dot");
    dot.className = "dot " + (h.llm ? "on" : "off");
    $("#llm-name").textContent = h.llm ? (h.llm_model || "connected") : "offline — start llamafile";
    $("#set-llm-status").innerHTML = h.llm
      ? `<span style="color:var(--ok)">● Connected</span> — model: <code>${esc(h.llm_model || "auto")}</code>`
      : `<span style="color:var(--err)">● Offline</span> — start llamafile/Ollama (URL: <code>${esc(h.llm_url)}</code>)`;
    return h;
  } catch (e) {
    $("#llm-name").textContent = "server offline?";
    return null;
  }
}

// Settings → "Test AI connection" button
$("#btn-llm-test").addEventListener("click", async () => {
  const out = $("#set-llm-test");
  const btn = $("#btn-llm-test");
  btn.disabled = true;
  out.textContent = "⏳ Asking the local AI a tiny question… (a thinking model can take 30s–3min — please wait)";
  try {
    const d = await api("/api/ai/test");
    out.innerHTML = `✅ Working! Model <code>${esc(d.model)}</code> replied in ${d.seconds}s:<br>“${esc(d.reply)}”`;
  } catch (e) {
    out.textContent = "❌ " + e.message;
  } finally {
    btn.disabled = false;
  }
});

// ============================================================
// LIBRARY
// ============================================================
async function loadBooks() {
  try {
    state.books = await api("/api/books");
  } catch (e) {
    toast("Couldn't load books: " + e.message);
    return;
  }
  const grid = $("#books-grid");
  grid.innerHTML = "";
  $("#empty-state").hidden = state.books.length > 0;

  state.books.forEach((b) => {
    const card = document.createElement("div");
    card.className = "book-card";
    const progress = b.page_count ? Math.round((b.progress / b.page_count) * 100) : 0;
    const letter = (b.title || "?").trim().charAt(0).toUpperCase();
    card.innerHTML = `
      <button class="book-del" title="Delete">🗑</button>
      <div class="book-cover">${letter}</div>
      <h4>${esc(b.title)}</h4>
      <div class="meta">${esc(b.author)} · ${b.page_count} pages · ${esc(b.source)}</div>
      <div class="book-progress"><i style="width:${progress}%"></i></div>`;
    card.addEventListener("click", () => openReader(b));
    card.querySelector(".book-del").addEventListener("click", async (e) => {
      e.stopPropagation();
      if (!confirm(`Delete "${b.title}"?`)) return;
      await api(`/api/books/${b.id}`, { method: "DELETE" });
      toast("Book deleted 🗑");
      loadBooks();
    });
    grid.appendChild(card);
  });
}

// upload
$("#btn-upload").addEventListener("click", () => $("#file-input").click());
$("#file-input").addEventListener("change", async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  const fd = new FormData();
  fd.append("file", file);
  toast("Uploading… ⏳");
  try {
    const b = await api("/api/books/upload", { method: "POST", body: fd });
    toast(`"${b.title}" added to your library ✅ (${b.page_count} pages)`);
    loadBooks();
  } catch (err) {
    toast("Upload failed: " + err.message);
  }
  e.target.value = "";
});

// gutenberg store panel
$("#btn-show-search").addEventListener("click", () => {
  const p = $("#store-panel");
  p.hidden = !p.hidden;
  if (!p.hidden) $("#gutenberg-search").focus();
});

$("#btn-gutenberg-go").addEventListener("click", doGutenbergSearch);
$("#gutenberg-search").addEventListener("keydown", (e) => e.key === "Enter" && doGutenbergSearch());

async function doGutenbergSearch() {
  const q = $("#gutenberg-search").value.trim();
  if (!q) return;
  const box = $("#gutenberg-results");
  box.innerHTML = `<p class="hint">Searching Gutenberg (70,000+ free books)…</p>`;
  try {
    const data = await api(`/api/library/search?q=${encodeURIComponent(q)}`);
    box.innerHTML = "";
    if (!data.results.length) {
      box.innerHTML = `<p class="hint">Nothing found — check the spelling or try the English title.</p>`;
      return;
    }
    data.results.forEach((r) => {
      const el = document.createElement("div");
      el.className = "gb-item";
      el.innerHTML = `
        <div>
          <div class="t">${esc(r.title)}</div>
          <div class="a">${esc(r.authors || "Unknown")} · ${r.langs.join(", ")} · ⬇ ${r.downloads}</div>
        </div>
        <button class="btn primary sm download-btn">⬇ Add</button>`;
      el.querySelector(".download-btn").addEventListener("click", async (ev) => {
        ev.target.disabled = true;
        ev.target.textContent = "Downloading…";
        try {
          const b = await api("/api/library/download", { method: "POST", body: { gutenberg_id: r.id } });
          toast(`"${b.title}" added ✅`);
          loadBooks();
          $("#store-panel").hidden = true;
        } catch (err) {
          toast("Download failed: " + err.message);
          ev.target.disabled = false;
          ev.target.textContent = "⬇ Add";
        }
      });
      box.appendChild(el);
    });
  } catch (e) {
    box.innerHTML = `<p class="hint" style="color:var(--err)">${esc(e.message)}</p>`;
  }
}

// ============================================================
// READER
// ============================================================
async function openReader(book) {
  try {
    state.currentBook = await api(`/api/books/${book.id}`);
  } catch (e) {
    return toast("Couldn't open the book: " + e.message);
  }
  state.page = Math.max(1, Math.min(state.currentBook.progress || 1, state.currentBook.page_count));
  $("#reader-title").textContent = state.currentBook.title;
  showView("reader");
  loadPage();
  loadNotes();
  resetChat();
  resetWords();
}

async function loadPage() {
  const b = state.currentBook;
  try {
    const p = await api(`/api/books/${b.id}/page/${state.page}`);
    state.pageText = p.text || "";
    $("#page-content").style.fontSize = state.fontSize + "px";
    // Long words become clickable (for the AI explainer)
    const wrapped = esc(p.text).replace(/([A-Za-z\u0900-\u097F]{7,})/g, '<pw data-w="$1">$1</pw>');
    $("#page-content").innerHTML = wrapped || "<i style='color:var(--dim)'>This page has no text.</i>";
    $("#page-counter").textContent = `${p.page} / ${p.total}`;
    $("#reader-pageinfo").textContent = `page ${p.page} / ${p.total}`;
    api(`/api/books/${b.id}/progress/${state.page}`).catch(() => {});
    attachWordClicks();
  } catch (e) {
    $("#page-content").textContent = "Couldn't load the page: " + e.message;
  }
}

function attachWordClicks() {
  // click a long word -> hard-word explainer popover
  $$("#page-content pw").forEach((el) =>
    el.addEventListener("click", () => openWordPop(el.dataset.w, el.getBoundingClientRect()))
  );
}

// extract the sentence/paragraph around a clicked word, so the AI
// explains the word IN ITS REAL CONTEXT (much better answers)
function contextAround(word) {
  const t = state.pageText || "";
  const i = t.toLowerCase().indexOf(word.toLowerCase());
  if (i === -1) return t.slice(0, 600) || `The word "${word}" appears in the book.`;
  const start = Math.max(0, i - 350);
  return t.slice(start, i + word.length + 350);
}

$("#page-prev").addEventListener("click", () => { if (state.page > 1) { state.page--; loadPage(); } });
$("#page-next").addEventListener("click", () => { if (state.page < state.currentBook.page_count) { state.page++; loadPage(); } });
$("#btn-back").addEventListener("click", () => { showView("library"); loadBooks(); });

$("#font-up").addEventListener("click", () => { state.fontSize = Math.min(26, state.fontSize + 1.5); $("#page-content").style.fontSize = state.fontSize + "px"; });
$("#font-down").addEventListener("click", () => { state.fontSize = Math.max(12, state.fontSize - 1.5); $("#page-content").style.fontSize = state.fontSize + "px"; });

// keyboard navigation
document.addEventListener("keydown", (e) => {
  if ($("#view-reader").hidden || !state.currentBook) return;
  if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
  if (e.key === "ArrowRight") $("#page-next").click();
  if (e.key === "ArrowLeft") $("#page-prev").click();
});

// word popover
function openWordPop(word, rect) {
  const pop = $("#word-pop");
  $("#wp-word").textContent = word;
  $("#wp-body").className = "wp-body loading";
  $("#wp-body").textContent = "🤖 Asking the local AI… (thinking model — can take 30s–2min)";
  pop.hidden = false;
  // position near the click (kept inside the window)
  const px = Math.min(window.innerWidth - 340, Math.max(10, rect.left));
  const py = Math.min(window.innerHeight - 220, Math.max(10, rect.bottom + 8));
  pop.style.left = px + "px";
  pop.style.top = py + "px";

  // LLM explain (with the real sentence around the word as context)
  api("/api/ai/explain", { method: "POST", body: { word, context: contextAround(word), lang: state.currentBook.lang } })
    .then((d) => { $("#wp-body").className = "wp-body"; $("#wp-body").textContent = d.answer; })
    .catch((e) => { $("#wp-body").className = "wp-body"; $("#wp-body").textContent = "⚠️ " + e.message; });

  // pronounce button
  $("#wp-speak").onclick = async () => {
    try {
      const d = await api("/api/tts/word", { method: "POST", body: { word, lang: "auto" } });
      playUrl(d.audio_url, `🔊 ${word}`);
    } catch (e) { toast(e.message); }
  };
}
$("#wp-close").addEventListener("click", () => ($("#word-pop").hidden = true));
document.addEventListener("click", (e) => {
  if (!$("#word-pop").hidden && !e.target.closest("#word-pop") && !e.target.closest("pw")) $("#word-pop").hidden = true;
});

// ============================================================
// TTS AUDIO — the reading player (brain audio is fully separate)
// ============================================================
const playerAudio = $("#player-audio");

function playUrl(url, label) {
  playerAudio.src = url;
  $("#player-label").textContent = label;
  $("#player-bar").hidden = false;
  playerAudio.play().catch(() => toast("Audio couldn't start — click the play button in the bar"));
}
$("#player-close").addEventListener("click", () => {
  playerAudio.pause();
  playerAudio.src = "";
  $("#player-bar").hidden = true;
});

$("#btn-tts").addEventListener("click", async () => {
  const b = state.currentBook;
  if (!b) return;
  const btn = $("#btn-tts");
  btn.disabled = true;
  toast("Creating page audio… (takes a few seconds)");
  try {
    const d = await api("/api/tts/page", { method: "POST", body: { book_id: b.id, page: state.page, lang: "auto" } });
    playUrl(d.audio_url, `🎧 Listening — page ${state.page}`);
  } catch (e) { toast(e.message); }
  finally { btn.disabled = false; }
});

// ============================================================
// BRAIN FREQUENCIES — dedicated section, separate from reading
// ============================================================
let BRAIN_META = {};   // filled from /api/health

function brainLabel(key) {
  const p = BRAIN_META[key];
  return p ? `${p.emoji} ${p.label}` : key;
}

async function renderBrain() {
  const h = await refreshHealth();
  BRAIN_META = (h && h.presets) || {};
  const grid = $("#brain-grid");
  grid.innerHTML = "";

  Object.entries(BRAIN_META).forEach(([key, p]) => {
    const playing = state.brainPreset === key;
    const card = document.createElement("div");
    card.className = "brain-card";
    card.innerHTML = `
      <div class="bc-head"><h3>${p.emoji} ${esc(p.label)}</h3><span class="hz">${p.hz} Hz</span></div>
      <p>${esc(p.desc)}</p>
      <div class="bc-controls">
        <select class="bc-min" title="Duration">
          <option value="5">5 min</option>
          <option value="10" selected>10 min</option>
          <option value="20">20 min</option>
          <option value="30">30 min</option>
        </select>
        <button class="brain-play ${playing ? "live" : ""}" data-preset="${key}">
          ${playing ? "⏹ Stop" : "▶ Play"}
        </button>
      </div>`;
    card.querySelector(".brain-play").addEventListener("click", async () => {
      if (state.brainPreset === key) {
        stopBrain();
      } else {
        const minutes = parseInt(card.querySelector(".bc-min").value) || 10;
        await playBrain(key, minutes);
      }
      renderBrain(); // refresh play/stop button states
    });
    grid.appendChild(card);
  });
  updateBrainNow();
}

async function playBrain(preset, minutes) {
  stopBrain(true);
  const label = brainLabel(preset);
  toast(`🧠 Preparing ${label} (${minutes} min)…`);
  try {
    const url = `/api/audio/brain/${preset}?minutes=${minutes}`;
    state.brainAudio = new Audio(url);
    state.brainAudio.loop = true;
    state.brainPreset = preset;
    state.brainMinutes = minutes;
    await state.brainAudio.play();
    updateBrainNow();
    toast(`🧠 ${label} playing · ${minutes} min — put your headphones on!`);
  } catch (e) {
    state.brainPreset = null;
    toast("Couldn't play the brain audio — try again (click fixes most browser blocks)");
  }
}

function stopBrain(silent = false) {
  if (state.brainAudio) {
    state.brainAudio.pause();
    state.brainAudio.src = "";
    state.brainAudio = null;
  }
  state.brainPreset = null;
  if (!silent) {
    updateBrainNow();
    if (!$("#view-brain").hidden) renderBrain();
  }
}

function updateBrainNow() {
  const bar = $("#brain-now");
  if (state.brainPreset) {
    bar.hidden = false;
    $("#brain-now-label").textContent = `🧠 Now playing: ${brainLabel(state.brainPreset)} · ${state.brainMinutes} min`;
  } else {
    bar.hidden = true;
  }
}

$("#brain-now-stop").addEventListener("click", () => stopBrain());
$("#brain-stop-all").addEventListener("click", () => { stopBrain(); toast("Brain audio stopped ⏹"); });

// ============================================================
// PANEL TABS
// ============================================================
$$(".tab").forEach((t) =>
  t.addEventListener("click", () => {
    state.tab = t.dataset.tab;
    $$(".tab").forEach((x) => x.classList.toggle("active", x === t));
    $$(".tab-pane").forEach((p) => p.classList.toggle("active", p.id === `tab-${t.dataset.tab}`));
  })
);

// ---------- chat ----------
function resetChat() {
  $("#chat-log").innerHTML = `<div class="msg ai">Hi! 👋 Ask me anything about this book — I'll answer only from its pages. (Thinking model: replies can take 30s–3min.)</div>`;
}
$("#chat-send").addEventListener("click", sendChat);
$("#chat-input").addEventListener("keydown", (e) => e.key === "Enter" && sendChat());

async function sendChat() {
  const q = $("#chat-input").value.trim();
  if (!q || !state.currentBook) return;
  const btn = $("#chat-send");
  btn.disabled = true;
  $("#chat-input").value = "";
  const log = $("#chat-log");
  log.insertAdjacentHTML("beforeend", `<div class="msg user">${esc(q)}</div>`);
  const loading = document.createElement("div");
  loading.className = "msg ai";
  loading.textContent = "🤖 Thinking… (local AI, please wait · 30s–3min)";
  log.appendChild(loading);
  log.scrollTop = log.scrollHeight;
  try {
    const d = await api("/api/ai/chat", { method: "POST", body: { book_id: state.currentBook.id, question: q, lang: state.currentBook.lang } });
    loading.innerHTML = `${esc(d.answer)}<span class="src">📖 Source: ${(d.pages || []).map((p) => "page " + p).join(", ")}</span>`;
  } catch (e) {
    loading.textContent = "⚠️ " + e.message;
  } finally {
    btn.disabled = false;
  }
  log.scrollTop = log.scrollHeight;
}

$("#chat-summarize").addEventListener("click", () => pageTask("/api/ai/summarize", { kind: "page" }, "summary", $("#chat-summarize")));
$("#chat-makenotes").addEventListener("click", () => pageTask("/api/ai/notes", {}, "notes", $("#chat-makenotes")));

async function pageTask(path, extra, key, btn) {
  if (!state.currentBook) return;
  btn.disabled = true;
  toast(`${key === "summary" ? "Summary" : "Notes"} — the AI is working on it… (30s–3min, thinking model)`, 6000);
  try {
    const pageData = await api(`/api/books/${state.currentBook.id}/page/${state.page}`);
    const d = await api(path, { method: "POST", body: { text: pageData.text, lang: state.currentBook.lang, ...extra } });
    const log = $("#chat-log");
    log.insertAdjacentHTML("beforeend", `<div class="msg ai">${esc(d[key] || d.summary || d.notes)}</div>`);
    log.scrollTop = log.scrollHeight;
    if (key === "notes") {
      // auto-save the AI notes
      await api("/api/notes", { method: "POST", body: { book_id: state.currentBook.id, title: `AI Notes · Page ${state.page}`, content: d.notes, page: state.page, kind: "ai" } });
      loadNotes();
      toast("AI notes saved 📒");
    }
  } catch (e) { toast(e.message, 6000); }
  finally { btn.disabled = false; }
}

// ---------- notes ----------
$("#note-save").addEventListener("click", async () => {
  const content = $("#note-content").value.trim();
  if (!content || !state.currentBook) return toast("Write something first!");
  await api("/api/notes", { method: "POST", body: { book_id: state.currentBook.id, title: $("#note-title").value || "Note", content, page: state.page, kind: "manual" } });
  $("#note-content").value = "";
  loadNotes();
  toast("Note saved ✅");
});

async function loadNotes() {
  if (!state.currentBook) return;
  const notes = await api(`/api/notes?book_id=${state.currentBook.id}`);
  const list = $("#notes-list");
  list.innerHTML = "";
  if (!notes.length) {
    list.innerHTML = `<p class="hint">No notes yet.</p>`;
    return;
  }
  notes.forEach((n) => {
    const el = document.createElement("div");
    el.className = "note-item";
    el.innerHTML = `
      <button class="note-del" title="Delete">🗑</button>
      <h5>${esc(n.title)} ${n.kind === "ai" ? '<span style="color:var(--accent2)">🤖</span>' : ""}</h5>
      <p>${esc(n.content)}</p>
      <span class="np">📄 page ${n.page}</span>`;
    el.querySelector(".note-del").addEventListener("click", async () => {
      await api(`/api/notes/${n.id}`, { method: "DELETE" });
      loadNotes();
    });
    list.appendChild(el);
  });
}

// ---------- hard words ----------
function resetWords() {
  $("#words-list").innerHTML = `<p class="hint">Use the button above to pull out this page's hard words.</p>`;
}
$("#btn-hardwords").addEventListener("click", async () => {
  if (!state.currentBook) return;
  const btn = $("#btn-hardwords");
  btn.disabled = true;
  const box = $("#words-list");
  box.innerHTML = `<p class="hint">🔍 Asking the AI… (thinking model — 30s–3min)</p>`;
  try {
    const pageData = await api(`/api/books/${state.currentBook.id}/page/${state.page}`);
    const d = await api("/api/ai/hardwords", { method: "POST", body: { text: pageData.text, lang: state.currentBook.lang } });
    box.innerHTML = "";
    const blocks = d.words.split(/\n(?=WORD:)/i).filter((b) => b.trim());
    blocks.forEach((b) => {
      const w = (b.match(/WORD:\s*(.+)/i) || [])[1]?.trim() || "word";
      const m = (b.match(/MEANING:\s*(.+)/i) || [])[1]?.trim() || "";
      const ex = (b.match(/EXAMPLE:\s*(.+)/i) || [])[1]?.trim() || "";
      const el = document.createElement("div");
      el.className = "word-item";
      el.innerHTML = `
        <div class="w">
          <strong>${esc(w)}</strong>
          <button class="icon-btn sm speak-btn" title="Pronounce">🔊</button>
        </div>
        ${m ? `<p><b>Meaning:</b> ${esc(m)}</p>` : ""}
        ${ex ? `<p><b>Example:</b> ${esc(ex)}</p>` : ""}`;
      el.querySelector(".speak-btn").addEventListener("click", async () => {
        try {
          const d = await api("/api/tts/word", { method: "POST", body: { word: w, lang: "auto" } });
          playUrl(d.audio_url, `🔊 ${w}`);
        } catch (e) { toast(e.message); }
      });
      box.appendChild(el);
    });
    if (!box.children.length) {
      box.innerHTML = `<p class="hint">The AI returned nothing readable — try again.</p>`;
    }
  } catch (e) {
    box.innerHTML = `<p class="hint" style="color:var(--err)">⚠️ ${esc(e.message)}</p>`;
  } finally {
    btn.disabled = false;
  }
});

// ============================================================
// NAV & INIT
// ============================================================
$$(".nav-btn").forEach((b) =>
  b.addEventListener("click", () => {
    showView(b.dataset.view);
    if (b.dataset.view === "brain") renderBrain();
    if (b.dataset.view === "settings") refreshHealth();
  })
);

(async function init() {
  refreshHealth();
  loadBooks();
})();
