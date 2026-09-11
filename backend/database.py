"""
database.py — SQLite database helpers.
Books, notes, bookmarks and reading progress live here.
Uses Python's built-in sqlite3 (nothing extra to install).
"""
import sqlite3
from datetime import datetime

from . import config


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Runs once at startup — creates tables if they don't exist."""
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS books (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            author      TEXT DEFAULT 'Unknown',
            file_path   TEXT NOT NULL,
            file_type   TEXT DEFAULT 'pdf',      -- pdf | txt
            page_count  INTEGER DEFAULT 0,
            lang        TEXT DEFAULT 'en',
            source      TEXT DEFAULT 'upload',   -- upload | gutenberg | manual
            added_at    TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS notes (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id     INTEGER NOT NULL,
            title       TEXT DEFAULT 'Note',
            content     TEXT NOT NULL,
            page        INTEGER DEFAULT 0,
            kind        TEXT DEFAULT 'manual',   -- manual | ai
            created_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS bookmarks (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            book_id     INTEGER NOT NULL,
            page        INTEGER NOT NULL,
            created_at  TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )
    conn.commit()
    conn.close()


# --------------------------- books ---------------------------
def add_book(title, author, file_path, file_type, page_count, lang, source) -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO books (title, author, file_path, file_type, page_count, lang, source) "
        "VALUES (?,?,?,?,?,?,?)",
        (title, author, file_path, file_type, page_count, lang, source),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_books():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM books ORDER BY added_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_book(book_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM books WHERE id=?", (book_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_book(book_id):
    conn = get_conn()
    conn.execute("DELETE FROM notes WHERE book_id=?", (book_id,))
    conn.execute("DELETE FROM bookmarks WHERE book_id=?", (book_id,))
    conn.execute("DELETE FROM books WHERE id=?", (book_id,))
    conn.commit()
    conn.close()


def save_progress(book_id, page):
    conn = get_conn()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (f"progress:{book_id}", str(page)),
    )
    conn.commit()
    conn.close()


def get_progress(book_id) -> int:
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (f"progress:{book_id}",)).fetchone()
    conn.close()
    return int(row["value"]) if row else 0


# --------------------------- notes ---------------------------
def add_note(book_id, title, content, page, kind="manual") -> int:
    conn = get_conn()
    cur = conn.execute(
        "INSERT INTO notes (book_id, title, content, page, kind) VALUES (?,?,?,?,?)",
        (book_id, title, content, page, kind),
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return new_id


def get_notes(book_id=None):
    conn = get_conn()
    if book_id:
        rows = conn.execute(
            "SELECT * FROM notes WHERE book_id=? ORDER BY created_at DESC", (book_id,)
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM notes ORDER BY created_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def delete_note(note_id):
    conn = get_conn()
    conn.execute("DELETE FROM notes WHERE id=?", (note_id,))
    conn.commit()
    conn.close()


# --------------------------- bookmarks ---------------------------
def add_bookmark(book_id, page):
    conn = get_conn()
    conn.execute("INSERT INTO bookmarks (book_id, page) VALUES (?,?)", (book_id, page))
    conn.commit()
    conn.close()


def get_bookmarks(book_id):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM bookmarks WHERE book_id=? ORDER BY page", (book_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def remove_bookmark(book_id, page):
    conn = get_conn()
    conn.execute("DELETE FROM bookmarks WHERE book_id=? AND page=?", (book_id, page))
    conn.commit()
    conn.close()
