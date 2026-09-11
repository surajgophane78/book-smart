"""
tts.py — Text-to-Speech: listen to a book page & hear word pronunciation.

Uses the free Microsoft Edge neural voices (edge-tts package).
The app is English-only, so one clear English voice is used everywhere.
An internet connection is required. For a fully-offline option
(Piper TTS) see the README roadmap.
"""
import asyncio
import re
import uuid
from pathlib import Path

import edge_tts

from . import config


def _chunk_text(text: str, max_chars: int = config.TTS_MAX_CHARS) -> list[str]:
    """Split long text into smaller chunks at sentence boundaries."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks, current = [], ""
    for s in sentences:
        if len(current) + len(s) + 1 > max_chars:
            if current:
                chunks.append(current)
            # a single sentence longer than max_chars gets hard-split
            while len(s) > max_chars:
                chunks.append(s[:max_chars])
                s = s[max_chars:]
            current = s
        else:
            current = f"{current} {s}".strip()
    if current:
        chunks.append(current)
    return chunks


async def _synth(text: str, voice: str, out_path: Path):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(out_path))


def generate_speech(text: str, lang: str = "auto", tag: str = "speech") -> Path:
    """
    Turn text into an MP3 file and return its path.
    `lang` is kept for API compatibility — the app currently speaks English only.
    """
    voice = config.TTS_VOICE
    chunks = _chunk_text(text)
    if not chunks:
        raise ValueError("No text found to speak.")

    out_path = config.AUDIO_DIR / f"{tag}_{uuid.uuid4().hex[:8]}.mp3"

    if len(chunks) == 1:
        asyncio.run(_synth(chunks[0], voice, out_path))
    else:
        # Multiple chunks -> synthesize each, then join the MP3 bytes
        # (edge-tts chunks share the same codec, so concatenation is safe)
        parts = []
        for ch in chunks:
            f = config.AUDIO_DIR / f"_tmp_{uuid.uuid4().hex[:8]}.mp3"
            asyncio.run(_synth(ch, voice, f))
            parts.append(f.read_bytes())
            f.unlink(missing_ok=True)
        out_path.write_bytes(b"".join(parts))

    return out_path
