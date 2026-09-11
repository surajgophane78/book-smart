"""
pdf_engine.py — the PDF / TXT book-reading engine (PyMuPDF).

What it does:
  1. Extracts metadata (title, author) and per-page text from PDFs
  2. Caches every page's text to disk (storage/pages/) for fast re-reading
  3. Splits plain .txt books into page-sized chunks
"""
import re
import unicodedata
from pathlib import Path

try:
    import pymupdf as fitz  # PyMuPDF (new name)
except ImportError:          # older versions
    import fitz

from . import config

CHARS_PER_TXT_PAGE = 3000  # how many characters one "page" of a .txt book holds


# ---------------------------------------------------------------
# PDF
# ---------------------------------------------------------------
def extract_pdf_pages(file_path: Path) -> dict:
    """Open a PDF and return per-page text + metadata."""
    doc = fitz.open(file_path)
    pages = []
    for page in doc:
        text = page.get_text("text")
        text = clean_text(text)
        pages.append(text)
    meta = doc.metadata or {}
    title = (meta.get("title") or "").strip() or doc.name.split("/")[-1]
    author = (meta.get("author") or "").strip() or "Unknown"
    lang = detect_language(" ".join(pages[:5]))
    doc.close()
    return {
        "title": title,
        "author": author,
        "pages": pages,
        "page_count": len(pages),
        "lang": lang,
    }


def cache_pages(book_id: int, pages: list[str]):
    """Save page texts to disk so later page loads are instant."""
    book_dir = config.PAGES_DIR / str(book_id)
    book_dir.mkdir(exist_ok=True)
    for i, text in enumerate(pages, start=1):
        (book_dir / f"page_{i:05d}.txt").write_text(text, encoding="utf-8")


def load_page(book_id: int, page_no: int) -> str | None:
    """Load a cached page's text. Returns None if missing."""
    f = config.PAGES_DIR / str(book_id) / f"page_{page_no:05d}.txt"
    if f.exists():
        return f.read_text(encoding="utf-8")
    return None


def book_text(book_id: int, max_pages: int | None = None) -> str:
    """The whole book's text (used to build AI context)."""
    book_dir = config.PAGES_DIR / str(book_id)
    parts = []
    if book_dir.exists():
        files = sorted(book_dir.glob("page_*.txt"))
        if max_pages:
            files = files[:max_pages]
        for f in files:
            parts.append(f.read_text(encoding="utf-8"))
    return "\n\n".join(parts)


# ---------------------------------------------------------------
# TXT books (Project Gutenberg downloads arrive in this format)
# ---------------------------------------------------------------
def txt_to_pages(text: str) -> list[str]:
    """Split long text into page-sized chunks."""
    text = clean_text(text)
    if not text:
        return []
    paragraphs = re.split(r"\n\s*\n", text)
    pages, current = [], ""
    for para in paragraphs:
        if len(current) + len(para) + 2 > CHARS_PER_TXT_PAGE:
            if current.strip():
                pages.append(current.strip())
            current = para
        else:
            current += ("\n\n" if current else "") + para
    if current.strip():
        pages.append(current.strip())
    return pages or [""]


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------
def clean_text(text: str) -> str:
    """Normalize unicode and strip extra whitespace."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\u00ad", "")            # soft hyphen
    text = re.sub(r"[ \t]+", " ", text)          # extra spaces
    text = re.sub(r"\n{3,}", "\n\n", text)       # extra blank lines
    return text.strip()


def detect_language(text: str) -> str:
    """Kept for book metadata: returns 'hi' if Devanagari is present, else 'en'."""
    devanagari = re.compile(r"[\u0900-\u097F]")
    if devanagari.search(text):
        return "hi"
    return "en"
