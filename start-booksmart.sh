#!/usr/bin/env bash
# ============================================================
#   BookSmart — ONE-CLICK START  (App + Local AI together)
#
#   ONE-TIME SETUP:
#     1. Edit the 2 paths below (where YOUR llamafile + model are)
#     2. chmod +x start-booksmart.sh stop-booksmart.sh
#     3. Run:  ./start-booksmart.sh
# ============================================================
LLAMAFILE_EXE="/path/to/llamafile-0.10.5/llamafile"
MODEL_FILE="/path/to/qwen3-4b-thinking-2507.Q4_K_M.gguf"
LLM_PORT=8080
APP_PORT=8000
# ============================================================

cd "$(dirname "$0")"
PID_FILE=".booksmart.pids"
: > "$PID_FILE"

echo
echo "  ================================================"
echo "     BookSmart  —  starting everything for you..."
echo "  ================================================"
echo

llm_ready() { curl -sf -m 2 "http://127.0.0.1:${LLM_PORT}/v1/models" >/dev/null 2>&1; }
app_ready() { curl -sf -m 1 "http://127.0.0.1:${APP_PORT}/api/health" >/dev/null 2>&1; }

# ---------------- 1) LOCAL AI (llamafile + Qwen3) ----------------
if [[ -x "$LLAMAFILE_EXE" && -f "$MODEL_FILE" ]]; then
  if llm_ready; then
    echo "  [AI]  Already running on port ${LLM_PORT} — reusing it ✔"
  else
    echo "  [AI]  Starting llamafile (Qwen3-4B)... first load takes 1-3 min."
    "$LLAMAFILE_EXE" -m "$MODEL_FILE" --server --host 127.0.0.1 \
        --port "$LLM_PORT" --jinja --ctx-size 8192 > llm.log 2>&1 &
    echo $! >> "$PID_FILE"
    echo -n "  [AI]  Waiting for the model to load"
    for _ in $(seq 1 90); do
      llm_ready && { echo; echo "  [AI]  Ready ✔ — Qwen3 is live on port ${LLM_PORT}"; break; }
      echo -n "."; sleep 2
    done
    llm_ready || { echo; echo "  [AI]  Still loading — continuing anyway (check llm.log)."; }
  fi
else
  echo "  [AI]  llamafile/model path not set — edit the top of this file."
  echo "  [AI]  Continuing WITHOUT AI (reading / TTS / notes still work)..."
fi
echo

# ---------------- 2) PYTHON ENV (first run auto-setup) ----------------
if [[ ! -x .venv/bin/python ]]; then
  echo "  [APP] First run — creating Python environment (one time, 1-2 min)..."
  python3 -m venv .venv
  ./.venv/bin/pip install -q --upgrade pip
  ./.venv/bin/pip install -q -r requirements.txt
fi
echo "  [APP] Python environment ready ✔"
echo

# ---------------- 3) START THE APP ----------------
./.venv/bin/python run.py > app.log 2>&1 &
APP_PID=$!
echo "$APP_PID" >> "$PID_FILE"

echo "  [APP] BookSmart is starting on http://localhost:${APP_PORT}"
for _ in $(seq 1 40); do app_ready && break; sleep 1; done

echo
echo "  ================================================"
echo "    ✅  EVERYTHING IS RUNNING!"
echo
echo "      Browser : http://localhost:${APP_PORT}"
echo "      Logs    : tail -f app.log   /   llm.log"
echo "      Stop    : ./stop-booksmart.sh"
echo "  ================================================"
echo

# open browser (linux: xdg-open, mac: open) — ignore failures
( command -v xdg-open >/dev/null && xdg-open "http://localhost:${APP_PORT}" >/dev/null 2>&1 ) || \
( command -v open      >/dev/null && open      "http://localhost:${APP_PORT}" >/dev/null 2>&1 ) || true

# keep this window attached to the app; Ctrl+C or stop script ends it
wait "$APP_PID"
