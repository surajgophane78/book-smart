#!/bin/bash
# ============================================================
#  BookSmart LLM Starter (Mac/Linux)
#  Edit the 2 paths below, then:  bash start_llm.sh
# ============================================================
LLAMAFILE_EXE="/path/to/llamafile-0.10.5/llamafile"
MODEL_FILE="/path/to/qwen3-4b-thinking-2507.Q4_K_M.gguf"
PORT=8080

echo "-----------------------------------------------"
echo " BookSmart AI starting on http://localhost:$PORT"
echo " (is window ko BAND mat karna — AI yahi chalta hai)"
echo "-----------------------------------------------"

"$LLAMAFILE_EXE" -m "$MODEL_FILE" --server --host 0.0.0.0 --port "$PORT" --jinja --ctx-size 8192
