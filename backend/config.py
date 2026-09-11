"""
config.py — every BookSmart setting lives here.
Change values to match your PC (or use environment variables).

LLM_BASE_URL is the address of your llamafile / Ollama / LM Studio server:
  - llamafile  : http://127.0.0.1:8080/v1
  - Ollama     : http://127.0.0.1:11434/v1
  - LM Studio  : http://127.0.0.1:1234/v1
"""
import os
from pathlib import Path

# ---------------------------------------------------------------
# Project paths
# ---------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

STORAGE_DIR = BASE_DIR / "storage"
BOOKS_DIR   = STORAGE_DIR / "books"        # uploaded PDFs / downloaded books
PAGES_DIR   = STORAGE_DIR / "pages"        # extracted per-page text cache (fast reading)
AUDIO_DIR   = STORAGE_DIR / "audio"        # generated TTS + brainwave audio
BRAIN_DIR   = AUDIO_DIR / "brain"
DB_PATH     = STORAGE_DIR / "booksmart.db" # SQLite database (books + notes)

for d in (BOOKS_DIR, PAGES_DIR, AUDIO_DIR, BRAIN_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------
# Local LLM  (your Qwen3-4B-Thinking via llamafile)
#
# NOTE: a "thinking" model reasons for a while before answering,
# so 30 seconds – 3 minutes per AI answer is NORMAL. The timeout
# below is generous on purpose — do not lower it too much.
# ---------------------------------------------------------------
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://127.0.0.1:8080/v1")
LLM_API_KEY  = os.getenv("LLM_API_KEY", "none")   # local server — no key needed
LLM_MODEL    = os.getenv("LLM_MODEL", "")          # empty = auto-detect from server
LLM_TIMEOUT  = int(os.getenv("LLM_TIMEOUT", "600"))

# ---------------------------------------------------------------
# Text-to-Speech (free Microsoft Edge voices — needs internet)
# App is English-only, so a single clear English voice is used.
# For a fully-offline option (Piper TTS) see the README.
# ---------------------------------------------------------------
TTS_VOICE = os.getenv("TTS_VOICE", "en-US-AriaNeural")
TTS_MAX_CHARS = 2500   # max characters converted to audio in one go (per page)

# ---------------------------------------------------------------
# Brain frequencies (binaural beats) presets
# Hz = beats per second between left & right ear
# ---------------------------------------------------------------
BRAIN_PRESETS = {
    # focus : 18-30 Hz beta  -> active concentration, alertness
    "focus": {"label": "Focus",      "hz": 18.0,  "emoji": "🎯", "desc": "Deep concentration and alertness while you read (Beta waves)"},
    # calm  : 8-13 Hz alpha  -> relaxed, calm, peaceful reading
    "calm":  {"label": "Calm",       "hz": 10.0,  "emoji": "🌿", "desc": "Relaxed, peaceful reading without stress (Alpha waves)"},
    # fresh : 4-8 Hz theta   -> deep refresh, fresh mind after reading
    "fresh": {"label": "Fresh Mind", "hz": 6.0,   "emoji": "✨", "desc": "Refresh and recharge your mind after reading (Theta waves)"},
    # deep  : 0.5-4 Hz delta -> deepest relaxation
    "deep":  {"label": "Deep Peace", "hz": 2.0,   "emoji": "🧘", "desc": "Deep relaxation and rest, almost sleep (Delta waves)"},
    # schumann resonance 7.83 Hz -> earth's frequency, grounding
    "earth": {"label": "Earth",      "hz": 7.83,  "emoji": "🌍", "desc": "Schumann resonance — grounding, nature's frequency (7.83 Hz)"},
}
BRAIN_BASE_FREQ = 210.0   # left ear carrier (Hz); right ear = base + preset hz
