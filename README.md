# 📚 BookSmart — Read, Listen, Take Notes (100% Local)

Drop any PDF/TXT book in, read it in a professional reader, understand hard words and
build notes with a **local AI** (your Qwen3-4B via llamafile), **listen** to any page,
and use **binaural brain frequencies** to focus while reading and refresh your mind after.
Everything runs on your own PC — **no data ever leaves your machine.**

```
┌────────────────────────── BookSmart ──────────────────────────┐
│  frontend/  → HTML + CSS + JS  (professional dark UI, English)│
│  backend/   → FastAPI (Python) : all APIs + logic             │
│  storage/   → books, page cache, audio, database              │
└───────────────────────────────────────────────────────────────┘
```

---

## 🚀 Step-by-step: run BookSmart on your PC

### Step 0 — Install tools (once)
1. **Python 3.10+** → https://www.python.org/downloads/ (tick ✅ *Add to PATH* during install!)
2. **VS Code** → https://code.visualstudio.com/ (+ extensions: *Python*, *Pylance*)
3. Open this `book-smart` folder in VS Code: `File → Open Folder`.

---

### 🖱️ THE EASY WAY — one master button (recommended)

Set it up **once**, then it's a single double-click forever:

1. Open **`START-BOOKSMART.bat`** (right-click → Edit, or open in VS Code)
2. At the very top, fix the two paths to **your** llamafile + model files
3. Save. Done! From now on just **double-click `START-BOOKSMART.bat`** — it will:
   - 🤖 start your Qwen3 AI (llamafile in its own window) — and *wait* until the model is ready
   - 🐍 create the Python environment automatically (first run only)
   - 🚀 start the BookSmart app and **open your browser** for you
4. To stop everything: double-click **`STOP-BOOKSMART.bat`** ✋

> 🍎🐧 Mac/Linux: `./start-booksmart.sh` to start, `./stop-booksmart.sh` to stop
> (same idea — set the 2 paths at the top of the file first).

---

### 🔧 THE MANUAL WAY (only if you like doing it step-by-step)

### Step 1 — Start llamafile + Qwen3-4B (for the AI features)
You have `qwen3-4b-thinking-2507.Q4_K_M.gguf` + `llamafile-0.10.5`. In a terminal:
```bat
:: go to the folder that has your model
cd /d C:\path\to\your\model-folder

:: start llamafile as a SERVER (OpenAI-compatible API on port 8080)
:: NOTE: the --server flag is REQUIRED, otherwise only a terminal chat opens
llamafile.exe -m qwen3-4b-thinking-2507.Q4_K_M.gguf --server --host 0.0.0.0 --port 8080 --jinja
```
> 💡 Easier: the project has `start_llm.bat` — set the 2 paths in it and double-click!

✅ Test: open `http://localhost:8080/v1/models` in your browser — JSON means the AI is ready.

> 🧠 **About your model:** Qwen3-4B-**Thinking** "thinks" before it answers (a hidden
> `<think>…</think>` reasoning block). Two consequences:
> 1. **Answers take 30 seconds – 3 minutes. That's normal**, not a bug.
> 2. BookSmart automatically **strips the thinking block** so you only see the final answer.
>
> Prefer **Ollama** instead? `ollama serve` + `ollama run qwen3`, then change
> `LLM_BASE_URL` in `backend/config.py` to `http://127.0.0.1:11434/v1`.

### Step 2 — Create the Python environment
In VS Code's terminal (``Ctrl + ` ``):
```bat
cd book-smart
python -m venv .venv
.venv\Scripts\activate          :: Windows
:: source .venv/bin/activate    :: Mac/Linux

pip install -r requirements.txt
```

### Step 3 — Start the app 🎉
```bat
python run.py
```
Open in your browser: **http://localhost:8000** — done, BookSmart is ready! ✅

### Step 4 — Test everything once
0. **One-click?** If you used `START-BOOKSMART.bat`, skip Steps 1–3 — everything is already running.
1. **Add a book** → `＋ Add Book` → upload any PDF
   (for a quick test: `python scripts/sample_book.py` creates a sample PDF)
2. **Read** → click a book card → flip pages (`←` `→` or keyboard arrows)
3. **Hard word** → click any long word in the reader → AI meaning (in real context) + 🔊 pronunciation
4. **Listen** → 🎧 button → audio of the page
5. **AI Chat** → ask the book anything in the right panel
6. **Summary / Notes** → `✍️ Summarize` / `📒 Make notes` buttons
7. **Brain Frequencies** → left sidebar → its own dedicated section → play any preset (**headphones required!**)
8. **Free books** → `🌐 Download Free Books` → search → Add
9. **AI not sure?** → Settings → `⚡ Test AI connection` — it asks the model a tiny question and shows the reply time.

---

## 🧠 Brain Frequencies Guide

| Preset | Hz | When to use |
|---|---|---|
| 🎯 Focus | 18 Hz (Beta) | Concentration while reading |
| 🌿 Calm | 10 Hz (Alpha) | Relaxed, peaceful reading |
| ✨ Fresh Mind | 6 Hz (Theta) | AFTER reading — refresh your mind |
| 🧘 Deep Peace | 2 Hz (Delta) | Deep relaxation / almost sleep |
| 🌍 Earth | 7.83 Hz | Grounding (Schumann resonance) |

> ⚠️ **Wear headphones** — binaural beats only work when each ear hears a different frequency.
> If you have epilepsy/migraine, ask a doctor first.

---

## 🛠️ Troubleshooting the local AI

| Problem | Fix |
|---|---|
| Sidebar says **offline** | llamafile is not running → start it (see Step 1). Check `--server` is in the command. |
| `⚡ Test AI connection` fails | Open `http://localhost:8080/v1/models` in a browser. No JSON? llamafile isn't serving. |
| Answers take long | Normal for a **thinking** model — 30s–3min depending on your CPU/RAM. |
| Empty/weird answers | Already handled: BookSmart strips `<think>` blocks and retries with more tokens. |
| Port 8080 busy | Start llamafile on another port and update `LLM_BASE_URL` in `backend/config.py`. |

---

## 🗂️ Project structure

```
book-smart/
├── backend/
│   ├── main.py        → FastAPI server (all API endpoints)
│   ├── config.py      → Settings (LLM URL, voices, presets) ← EDIT HERE
│   ├── database.py    → SQLite (books, notes, progress)
│   ├── llm.py         → Local LLM client + thinking-model fix
│   ├── pdf_engine.py  → PDF/TXT reading + page cache
│   ├── tts.py         → Text-to-Speech (listen to pages)
│   ├── audio.py       → Binaural beats generator (numpy)
│   └── library.py     → Project Gutenberg search/download
├── frontend/
│   ├── index.html     → UI structure (English)
│   ├── style.css      → Dark professional theme
│   └── app.js         → All UI logic
├── storage/           → books, audio, page cache, database
├── scripts/
│   ├── sample_book.py → creates a test PDF
│   └── mock_llm.py    → fake LLM server to test the app without a model
├── START-BOOKSMART.bat→ 🖱️ ONE master button — starts AI + app + browser (Windows)
├── STOP-BOOKSMART.bat → stops everything (Windows)
├── start-booksmart.sh → same one-click start (Mac/Linux)
├── stop-booksmart.sh  → stop everything (Mac/Linux)
├── requirements.txt   → Python packages
└── run.py             → App starter (used by the master button)
```

---

## 🗺️ Roadmap

- [ ] **Phase 2** · ChromaDB embeddings — meaning-based answers (not just keyword search)
- [ ] **Phase 3** · Highlights + underline, auto flashcards
- [ ] **Phase 4** · Piper TTS (fully offline audio)
- [ ] **Phase 5** · Reading streaks, daily goals, stats dashboard
- [ ] **Phase 6** · Spaced-repetition revision mode
- [ ] **Phase 7** · Android/desktop build (Tauri) — still fully local

---

## ⚖️ Legal note (important!)

Downloadable books come from **Project Gutenberg** — 100% **copyright-free** public-domain
books (70,000+). Downloading/sharing copyrighted books without permission is illegal —
the PDF upload feature is meant for **your own** books only.

---

Made with ❤️ by suraj · FastAPI · Vanilla JS — all on your PC, all local.
