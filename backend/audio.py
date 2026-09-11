"""
audio.py — binaural beats / brainwave frequency generator.

What is this? The left ear hears one frequency, the right ear hears a
slightly different one — the brain perceives the difference as a "beat".
Example:
  left = 210 Hz, right = 220 Hz  ->  the brain senses 10 Hz (Alpha, calm).

The WAV file is generated in pure Python (numpy) — no external audio needed.
Edit presets in config.BRAIN_PRESETS.
"""
import wave
from pathlib import Path

import numpy as np

from . import config

SAMPLE_RATE = 44100
VOLUME = 0.28           # comfortable volume (0.0 - 1.0)
FADE_SECONDS = 20       # soft fade at start/end (avoids sudden loud sound)


def generate_brain_wave(preset: str, minutes: float = 10, out_path: Path | None = None) -> Path:
    """
    Generate a binaural-beat WAV file.
    preset  : a key from config.BRAIN_PRESETS (focus/calm/fresh/deep/earth)
    minutes : how long the audio should be
    """
    if preset not in config.BRAIN_PRESETS:
        raise ValueError(f"Unknown preset: {preset}")

    beat_hz = config.BRAIN_PRESETS[preset]["hz"]
    base = config.BRAIN_BASE_FREQ

    total_samples = int(SAMPLE_RATE * minutes * 60)
    t = np.arange(total_samples) / SAMPLE_RATE

    # Left: base freq, Right: base + beat
    left = np.sin(2 * np.pi * base * t)
    right = np.sin(2 * np.pi * (base + beat_hz) * t)

    # Soft fade in/out
    fade = np.ones(total_samples)
    fade_samples = int(SAMPLE_RATE * FADE_SECONDS)
    fade_samples = min(fade_samples, total_samples // 2)
    fade[:fade_samples] = np.linspace(0, 1, fade_samples)
    fade[-fade_samples:] = np.linspace(1, 0, fade_samples)

    left = (left * fade * VOLUME)
    right = (right * fade * VOLUME)

    # 16-bit stereo WAV
    stereo = np.empty((total_samples, 2), dtype=np.int16)
    stereo[:, 0] = (left * 32767).astype(np.int16)
    stereo[:, 1] = (right * 32767).astype(np.int16)

    if out_path is None:
        out_path = config.BRAIN_DIR / f"{preset}_{int(minutes)}min.wav"
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)          # 16-bit
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(stereo.tobytes())

    return out_path
