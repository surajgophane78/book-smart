"""
main.py — BookSmart's FastAPI server. Everything runs from here.

To start:
    uvicorn backend.main:app --reload --port 8000
or from the project folder:
    python run.py
"""
import re
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import audio, config, database as db, library, llm, pdf_engine, tts

# ---------------------------------------------------------------
# FastAPI setup
# ---------------------------------------------------------------
app = FastAPI(title="BookSmart", description="Read your books, listen to them, take notes — all local.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local app — allow everything
    allow_methods=["*"],
    allow_headers=["*"],
)

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
app.mount("/media", StaticFiles(directory=config.AUDIO_DIR), name="media")
app.mount("/assets", StaticFiles(directory=FRONTEND_DIR), name="assets")


@app.on_event("startup")
def startup():
    db.init_db()


@app.get("/")
def index():
    return FileResponse(FRONTEND_DIR / "index.html")


# ---------------------------------------------------------------
# Request models
# ---------------------------------------------------------------
class ExplainReq(BaseModel):
    word: str
    context: str = ""
    lang: str = "en"


class TextReq(BaseModel):
    text: str
    lang: str = "en"
    kind: str = "paragraph"   # paragraph | page | chapter


class ChatReq(BaseModel):
    book_id: int
    question: str
    lang: str = "en"


class NoteReq(BaseModel):
    book_id: int
    title: str = "Note"
    content: str
    page: int = 0
    kind: str = "manual"


class TTSPageReq(BaseModel):
    book_id: int
    page: int
    lang: str = "auto"     # auto -> detect (English voice is used today)


class TTSWordReq(BaseModel):
    word: str
    lang: str = "auto"


class DownloadReq(BaseModel):
    gutenberg_id: int


# ---------------------------------------------------------------
# Health
# ---------------------------------------------------------------
@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "llm": llm.is_available(),
        "llm_model": llm.active_model(),
        "llm_url": config.LLM_BASE_URL,
        "presets": config.BRAIN_PRESETS,
    }


# ---------------------------------------------------------------
# Books (upload / list / read)
# ---------------------------------------------------------------
@app.post("/api/books/upload")
async def upload_book(file: UploadFile = File(...)):
    """Upload a PDF / TXT -> added to the library."""
    suffix = Path(file.filename or "book.pdf").suffix.lower()
    if suffix not in (".pdf", ".txt"):
        raise HTTPException(400, "Only .pdf or .txt files are supported")

    dest = config.BOOKS_DIR / f"{uuid.uuid4().hex[:8]}{suffix}"
    with open(dest, "wb") as f:
        shutil.copyfileobj(file.file, f)

    try:
        if suffix == ".pdf":
            extracted = pdf_engine.extract_pdf_pages(dest)
            title, author, pages = extracted["title"], extracted["author"], extracted["pages"]
            lang, page_count = extracted["lang"], extracted["page_count"]
        else:
            text = dest.read_text(encoding="utf-8", errors="replace")
            pages = pdf_engine.txt_to_pages(text)
            title = Path(file.filename).stem
            author, lang, page_count = "Unknown", pdf_engine.detect_language(text[:5000]), len(pages)
    except Exception as e:
        dest.unlink(missing_ok=True)
        raise HTTPException(400, f"Could not read this book: {e}")

    book_id = db.add_book(title, author, str(dest), suffix.lstrip("."), page_count, lang, "upload")
    pdf_engine.cache_pages(book_id, pages)
    return {"id": book_id, "title": title, "page_count": page_count}


@app.get("/api/books")
def list_books():
    books = db.get_books()
    for b in books:
        b["progress"] = db.get_progress(b["id"])
        b["note_count"] = len([n for n in db.get_notes(b["id"])])
    return books


@app.get("/api/books/{book_id}")
def book_info(book_id: int):
    b = db.get_book(book_id)
    if not b:
        raise HTTPException(404, "Book not found")
    b["notes"] = db.get_notes(book_id)
    b["bookmarks"] = db.get_bookmarks(book_id)
    b["progress"] = db.get_progress(book_id)
    return b


@app.get("/api/books/{book_id}/page/{page_no}")
def get_page(book_id: int, page_no: int):
    b = db.get_book(book_id)
    if not b:
        raise HTTPException(404, "Book not found")
    if page_no < 1 or page_no > b["page_count"]:
        raise HTTPException(404, "Page number out of range")
    text = pdf_engine.load_page(book_id, page_no) or ""
    return {"book_id": book_id, "page": page_no, "total": b["page_count"],
            "text": text, "lang": b["lang"]}


@app.post("/api/books/{book_id}/progress/{page_no}")
def save_progress(book_id: int, page_no: int):
    db.save_progress(book_id, page_no)
    return {"ok": True}


@app.delete("/api/books/{book_id}")
def remove_book(book_id: int):
    b = db.get_book(book_id)
    if not b:
        raise HTTPException(404, "Book not found")
    Path(b["file_path"]).unlink(missing_ok=True)
    db.delete_book(book_id)
    return {"ok": True}


# ---------------------------------------------------------------
# Free library (Project Gutenberg)
# ---------------------------------------------------------------
@app.get("/api/library/search")
def library_search(q: str):
    try:
        return {"results": library.search_gutenberg(q)}
    except Exception as e:
        raise HTTPException(502, str(e))


@app.post("/api/library/download")
def library_download(req: DownloadReq):
    try:
        book_id = library.download_gutenberg(req.gutenberg_id)
    except Exception as e:
        raise HTTPException(500, str(e))
    b = db.get_book(book_id)
    return {"id": book_id, "title": b["title"], "page_count": b["page_count"]}


# ---------------------------------------------------------------
# AI features (LLM)
# ---------------------------------------------------------------
@app.get("/api/ai/test")
def ai_test():
    """Diagnostics: ask the LLM a tiny question and measure the response time."""
    try:
        return {"ok": True, **llm.test_connection()}
    except llm.LLMError as e:
        raise HTTPException(503, str(e))


@app.post("/api/ai/explain")
def ai_explain(req: ExplainReq):
    """Explain a hard word (simple English meaning + synonyms)."""
    word = req.word.strip()
    if not word:
        raise HTTPException(400, "Word is empty")
    context = req.context or f"The word '{word}' appears in the book."
    try:
        answer = llm.explain_word(word, context, req.lang)
    except llm.LLMError as e:
        raise HTTPException(503, str(e))
    return {"word": word, "answer": answer}


@app.post("/api/ai/summarize")
def ai_summarize(req: TextReq):
    try:
        return {"summary": llm.summarize(req.text, req.lang, req.kind)}
    except llm.LLMError as e:
        raise HTTPException(503, str(e))


@app.post("/api/ai/notes")
def ai_notes(req: TextReq):
    """Turn a page/selection into revision notes."""
    try:
        return {"notes": llm.make_notes(req.text, req.lang)}
    except llm.LLMError as e:
        raise HTTPException(503, str(e))


@app.post("/api/ai/hardwords")
def ai_hardwords(req: TextReq):
    """Pick the hard words of a passage, with simple meanings."""
    try:
        return {"words": llm.hard_words(req.text, req.lang)}
    except llm.LLMError as e:
        raise HTTPException(503, str(e))


@app.get("/api/ai/lookup")
def ai_lookup(book_id: int, q: str):
    """Find relevant pages in a book (keyword search — fast, no GPU needed)."""
    b = db.get_book(book_id)
    if not b:
        raise HTTPException(404, "Book not found")
    terms = [t.lower() for t in q.split() if len(t) > 2]
    scored = []
    for p in range(1, b["page_count"] + 1):
        text = pdf_engine.load_page(book_id, p) or ""
        if not text:
            continue
        low = text.lower()
        score = sum(low.count(t) for t in terms)
        if score > 0:
            scored.append({"page": p, "score": score, "snippet": make_snippet(text, terms)})
    scored.sort(key=lambda x: -x["score"])
    return {"results": scored[:5]}


def make_snippet(text: str, terms: list[str], width: int = 260) -> str:
    low = text.lower()
    pos = min([low.find(t) for t in terms if t in low], default=0)
    start = max(0, pos - width // 2)
    return text[start:start + width].replace("\n", " ").strip() + "..."


def retrieve_context(book_id: int, question: str, top_pages: int = 4) -> tuple[str, list[int]]:
    """
    RAG (Retrieval-Augmented Generation): find pages related to the question
    and feed their text to the LLM as context.
    Right now this is simple keyword scoring — fast and zero-dependency.
    (Roadmap: upgrade to ChromaDB + embeddings.)
    """
    b = db.get_book(book_id)
    if not b:
        raise HTTPException(404, "Book not found")
    terms = [t.lower() for t in re.findall(r"[a-zA-Z\u0900-\u097F]+", question) if len(t) > 2]
    if not terms:
        return "", []
    scored = []
    for p in range(1, b["page_count"] + 1):
        text = pdf_engine.load_page(book_id, p) or ""
        if not text:
            continue
        low = text.lower()
        score = sum(low.count(t) for t in terms)
        if score > 0:
            scored.append((p, score))
    scored.sort(key=lambda x: -x[1])
    top = [p for p, _ in scored[:top_pages]]
    context = "\n\n".join(
        f"[Page {p}]\n{pdf_engine.load_page(book_id, p)}" for p in top
    )
    return context, top


@app.post("/api/ai/chat")
def ai_chat(req: ChatReq):
    """Ask the book anything — the LLM answers only from the book's context."""
    context, pages = retrieve_context(req.book_id, req.question)
    if not context.strip():
        raise HTTPException(
            404,
            "Couldn't find anything about that in this book. "
            "Try asking with different words, or something more specific to the story/topic.",
        )
    try:
        answer = llm.answer_question(req.question, context, req.lang)
    except llm.LLMError as e:
        raise HTTPException(503, str(e))
    return {"answer": answer, "pages": pages}


# ---------------------------------------------------------------
# Notes
# ---------------------------------------------------------------
@app.get("/api/notes")
def list_notes(book_id: int | None = None):
    return db.get_notes(book_id)


@app.post("/api/notes")
def create_note(req: NoteReq):
    note_id = db.add_note(req.book_id, req.title, req.content, req.page, req.kind)
    return {"id": note_id}


@app.delete("/api/notes/{note_id}")
def drop_note(note_id: int):
    db.delete_note(note_id)
    return {"ok": True}


@app.post("/api/books/{book_id}/bookmark/{page_no}")
def add_mark(book_id: int, page_no: int):
    db.add_bookmark(book_id, page_no)
    return {"ok": True}


@app.delete("/api/books/{book_id}/bookmark/{page_no}")
def drop_mark(book_id: int, page_no: int):
    db.remove_bookmark(book_id, page_no)
    return {"ok": True}


# ---------------------------------------------------------------
# Audio: TTS (listen to a book) + word pronunciation
# ---------------------------------------------------------------
@app.post("/api/tts/page")
def tts_page(req: TTSPageReq):
    b = db.get_book(req.book_id)
    if not b:
        raise HTTPException(404, "Book not found")
    text = pdf_engine.load_page(req.book_id, req.page) or ""
    if len(text.strip()) < 5:
        raise HTTPException(400, "This page doesn't have enough text to read aloud")
    try:
        path = tts.generate_speech(text, lang=req.lang, tag="page")
    except Exception as e:
        raise HTTPException(502, f"Could not create audio (TTS needs internet): {e}")
    return {"audio_url": f"/media/{path.name}"}


@app.post("/api/tts/word")
def tts_word(req: TTSWordReq):
    try:
        path = tts.generate_speech(req.word, lang=req.lang, tag="word")
    except Exception as e:
        raise HTTPException(502, f"Could not create audio: {e}")
    return {"audio_url": f"/media/{path.name}"}


# ---------------------------------------------------------------
# Audio: Brain frequencies (binaural beats)
# ---------------------------------------------------------------
@app.get("/api/audio/brain/{preset}")
def brain_audio(preset: str, minutes: float = 10.0):
    minutes = max(1.0, min(minutes, 60.0))
    try:
        path = audio.generate_brain_wave(preset, minutes)
    except ValueError as e:
        raise HTTPException(404, str(e))
    return FileResponse(path, media_type="audio/wav",
                        headers={"Content-Disposition": f'inline; filename="{path.name}"'})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
