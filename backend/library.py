"""
library.py — free & legal book downloads.

Source: Project Gutenberg (via the gutendex.com API) — 70,000+ FREE,
copyright-free public-domain books in 60+ languages. Internet required.
Books download as plain text (.txt) and the app converts them into
page-wise readable form.
"""
import re
import uuid
from pathlib import Path

import requests

from . import config
from . import database as db
from .pdf_engine import txt_to_pages, detect_language, cache_pages

GUTENDEX_API = "https://gutendex.com/books"

# Gutenberg politely asks for a real User-Agent
HEADERS = {"User-Agent": "BookSmart/1.0 (book reader; contact: local-user)"}


def search_gutenberg(query: str, limit: int = 12) -> list[dict]:
    """Search Gutenberg. Returns [{id, title, authors, langs, downloads}]."""
    try:
        resp = requests.get(GUTENDEX_API, params={"search": query}, timeout=40, headers=HEADERS)
        resp.raise_for_status()
    except Exception as e:
        raise RuntimeError(f"Could not reach Gutenberg (internet slow/offline?): {e}")

    results = []
    for item in resp.json().get("results", [])[:limit]:
        results.append({
            "id": item["id"],
            "title": item.get("title", "Unknown"),
            "authors": ", ".join(a.get("name", "") for a in item.get("authors", [])),
            "langs": item.get("languages", []),
            "downloads": item.get("download_count", 0),
        })
    return results


def _plain_text_urls(gutenberg_id: int) -> list[str]:
    """Build a list of candidate plain-text URLs (gutendex 'formats' + standard paths)."""
    urls = []
    try:
        detail = requests.get(f"{GUTENDEX_API}/{gutenberg_id}", timeout=40, headers=HEADERS)
        detail.raise_for_status()
        for key, url in detail.json().get("formats", {}).items():
            if "text/plain" in key:
                urls.append(url)
    except Exception:
        pass
    urls += [
        f"https://www.gutenberg.org/cache/epub/{gutenberg_id}/pg{gutenberg_id}.txt",
        f"https://www.gutenberg.org/ebooks/{gutenberg_id}.txt.utf-8",
        f"https://www.gutenberg.org/files/{gutenberg_id}/{gutenberg_id}-0.txt",
    ]
    # drop duplicates, keep order
    seen, out = set(), []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def download_gutenberg(gutenberg_id: int) -> int:
    """
    Download a book and add it to the library.
    Returns the new book id (in the database).
    """
    resp = None
    for url in _plain_text_urls(gutenberg_id):
        try:
            r = requests.get(url, timeout=120, headers=HEADERS)
            if r.status_code == 200 and len(r.text) > 500:
                resp = r
                break
        except Exception:
            continue
    if resp is None:
        raise RuntimeError(
            f"Could not download Gutenberg book #{gutenberg_id} "
            "(gutenberg.org may be busy or blocked — try again on your normal internet)."
        )

    text = resp.content.decode("utf-8", errors="replace")

    # ---- remove Gutenberg's license header/footer boilerplate ----
    text = strip_gutenberg_boilerplate(text)

    # Title/Author live at the top of the text (Gutenberg format)
    m = re.search(r"Title:\s*(.+?)\s*\n", text[:3000])
    title = m.group(1).strip() if m else f"Gutenberg #{gutenberg_id}"
    m2 = re.search(r"Author:\s*(.+?)\s*\n", text[:3000])
    author = m2.group(1).strip() if m2 else "Project Gutenberg"

    pages = txt_to_pages(text)
    lang = detect_language(text[:5000])

    # Save the file
    safe = re.sub(r"[^\w\- ]+", "", title).strip()[:60] or "book"
    file_path = config.BOOKS_DIR / f"{safe}_{uuid.uuid4().hex[:6]}.txt"
    file_path.write_text(text, encoding="utf-8")

    book_id = db.add_book(title, author, str(file_path), "txt", len(pages), lang, "gutenberg")
    cache_pages(book_id, pages)
    return book_id


def strip_gutenberg_boilerplate(text: str) -> str:
    """Remove Gutenberg's start/end license markers."""
    text = re.sub(
        r"\*\*\* START OF (THE|THIS) PROJECT GUTENBERG.*?\*\*\*", "", text, flags=re.S
    )
    text = re.sub(
        r"\*\*\* END OF (THE|THIS) PROJECT GUTENBERG.*?\*", "", text, flags=re.S
    )
    return text.strip()
