"""
llm.py — client for your LOCAL LLM (llamafile + Qwen3-4B-Thinking).

llamafile / Ollama / LM Studio all expose an OpenAI-compatible API,
so we use the `openai` Python package pointed at the local URL.
If the LLM is not running, the app still works — AI features just
show as "offline".
"""
import re
import time
from functools import lru_cache

from openai import OpenAI

from . import config


class LLMError(Exception):
    """Raised when the LLM cannot be reached or returns nothing useful."""


@lru_cache(maxsize=1)
def get_client() -> OpenAI:
    return OpenAI(
        base_url=config.LLM_BASE_URL,
        api_key=config.LLM_API_KEY,
        timeout=config.LLM_TIMEOUT,
    )


def is_available() -> bool:
    """Is the LLM server up and answering?"""
    try:
        get_client().models.list()
        return True
    except Exception:
        return False


def active_model() -> str | None:
    """Detect which model the server is running (auto-detect)."""
    try:
        models = get_client().models.list()
        for m in models.data:
            return m.id
    except Exception:
        pass
    return config.LLM_MODEL or None


# ------------------------------------------------------------------
# THINKING-MODEL FIX  (this is what makes Qwen3-4B-Thinking behave)
#
# Qwen3 "thinking" models first write a long hidden reasoning block:
#     <think> ...lots of reasoning... </think> actual answer
# That block EATS output tokens, so with small max_tokens the visible
# answer gets cut off — or comes back completely EMPTY. We therefore:
#   1. use generous max_tokens (the thinking needs headroom), and
#   2. strip the <think>...</think> part before showing the answer,
#   3. retry once with double tokens if the answer came back empty.
# ------------------------------------------------------------------
_THINK_RE = re.compile(r"<think>.*?</think>", re.S)


def _strip_thinking(text: str) -> str:
    """Remove <think>...</think> reasoning blocks from the model output.

    In Qwen3 output the reasoning block always comes FIRST, so we only
    treat a leading <think> as the hidden block — a plain mention of the
    word later in the answer must never truncate the reply.
    """
    if not text:
        return ""
    text = text.strip()
    if text.startswith("<think>"):
        end = text.find("</think>")
        text = text[end + len("</think>"):] if end != -1 else ""
    # safety net: remove any further complete think blocks
    text = _THINK_RE.sub("", text)
    return text.strip()


def _chat(system: str, user: str, max_tokens: int = 2000) -> str:
    model = active_model()
    if not model:
        raise LLMError(
            "LLM server not found. Start llamafile first "
            f"(run start_llm.bat). URL tried: {config.LLM_BASE_URL}"
        )

    last_err = "unknown error"
    for attempt in range(2):  # one retry — thinking models sometimes need it
        try:
            resp = get_client().chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                temperature=0.6,          # Qwen-recommended for thinking models
                top_p=0.95,
                max_tokens=max_tokens if attempt == 0 else max_tokens * 2,
            )
            answer = _strip_thinking(resp.choices[0].message.content or "")
            if answer:
                return answer
            last_err = ("the model spent all its tokens thinking and returned "
                        "an empty answer (retried with more tokens)")
        except Exception as e:
            last_err = str(e)
    raise LLMError(f"LLM error: {last_err}")


def test_connection() -> dict:
    """Quick diagnostic used by the Settings page 'Test AI' button."""
    model = active_model()
    if not model:
        raise LLMError(
            f"No model detected at {config.LLM_BASE_URL} — is llamafile running?"
        )
    started = time.time()
    answer = _chat(
        "You are a health-check inside a reading app. "
        "Reply with exactly one short friendly sentence.",
        "Say that BookSmart AI is ready.",
        max_tokens=2500,
    )
    return {
        "model": model,
        "reply": answer,
        "seconds": round(time.time() - started, 1),
    }


# ---------------------------------------------------------------
# AI Features  (app is English-only → all prompts & answers English)
# ---------------------------------------------------------------
def explain_word(word: str, context: str, lang: str = "en") -> str:
    system = (
        "You are a smart vocabulary assistant inside a book-reading app. "
        "Explain ONE word only, in simple student-friendly English. "
        "Format your answer EXACTLY as three short lines:\n"
        "MEANING: <one simple sentence, max 15 words>\n"
        "SYNONYMS: <2-3 similar words, comma separated>\n"
        "IN CONTEXT: <what the word means in the sentence it was clicked in>"
    )
    user = f"Word: {word}\n\nFrom the book:\n\"{context[:800]}\""
    return _chat(system, user, max_tokens=1500)


def summarize(text: str, lang: str = "en", kind: str = "paragraph") -> str:
    what = {
        "paragraph": "the selected passage",
        "page": "this page",
        "chapter": "this chapter",
    }.get(kind, "this passage")
    system = (
        f"Summarize {what} in 4-6 bullet points. Every bullet must start with '• '. "
        "Keep it crisp and useful for revision. Reply in clear, simple English."
    )
    return _chat(system, f"Text:\n{text[:4000]}", max_tokens=2500)


def make_notes(text: str, lang: str = "en") -> str:
    system = (
        "You are a study-notes expert. From the given book text, create clean "
        "revision notes in English with these exact sections:\n"
        "📌 KEY POINTS — 4-6 main ideas as bullets\n"
        "💡 IMPORTANT LINES — 2-3 quotes worth remembering\n"
        "🧠 SUMMARY — 3-4 line overall summary\n"
        "❓ SELF-TEST — 2 questions to check understanding"
    )
    return _chat(system, f"Book text:\n{text[:5000]}", max_tokens=3500)


def answer_question(question: str, context: str, lang: str = "en") -> str:
    system = (
        "You are a book mentor inside a reading app. Answer the user's question "
        "in clear English and ONLY from the book context given. If the answer is "
        "not in the context, say exactly: 'The answer is not in this part of the book.'\n"
        "End your answer with a short '📖 Book reference' line quoting the exact "
        "sentence that supports your answer."
    )
    user = f"Question: {question}\n\nBook context:\n{context[:8000]}"
    return _chat(system, user, max_tokens=3500)


def chapter_title(text: str, lang: str = "en") -> str:
    """Short auto-title for a book section (used by future features)."""
    system = (
        "Give a short, catchy title (max 6 words) for this book section. "
        "Return ONLY the title, nothing else."
    )
    return _chat(system, f"Section text:\n{text[:1500]}", max_tokens=1000)


def hard_words(text: str, lang: str = "en") -> str:
    """Pick the hardest / most important words from a passage, with meanings."""
    system = (
        "You are a vocabulary tutor. From the given text, pick the 5 hardest / most "
        "important words for an English learner. For EACH word output EXACTLY:\n"
        "WORD: <word>\n"
        "MEANING: <simple easy meaning in one line>\n"
        "EXAMPLE: <one short sentence using the word>\n"
        "Separate each word with a blank line. No intro, nothing else."
    )
    return _chat(system, f"Text:\n{text[:4000]}", max_tokens=2500)
