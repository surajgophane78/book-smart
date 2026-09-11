"""
sample_book.py — Testing ke liye ek chhoti sample PDF banata hai.
    python scripts/sample_book.py
Output: storage/books/sample_book.pdf
"""
import sys
from pathlib import Path

try:
    import pymupdf as fitz  # PyMuPDF (naya naam)
except ImportError:
    import fitz

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from backend import config  # noqa: E402

TEXT = """
THE LITTLE READER'S GUIDE
A short sample book for testing BookSmart.

Chapter 1: Why Reading Matters

Reading is a superpower. It allows you to travel to places you have
never visited and to understand thoughts you have never thought.
Books are a bridge between generations, and every page you turn
is a step towards a better, more thoughtful version of yourself.

Great ideas often begin as quiet thoughts in an ordinary moment.
The habit of reading builds concentration and patience, and it
transforms curiosity into understanding. Knowledge compounds:
every book you finish makes the next one easier to appreciate.

Chapter 2: The Joy of Learning

Learning should feel like exploration, not like a burden. When you
study something you love, the effort becomes enjoyable and the
results become natural. Notes, summaries and questions are the
tools that turn reading into real learning.

Always record the ideas that surprise you. The best notes are not
long essays; they are short flags that remind you of what mattered.
Ask questions as you read: Why? How? What would I do differently?
This simple habit transforms a passive reader into a sharp thinker.

Chapter 3: Sounds of the Mind

Some readers like a quiet room. Others enjoy soft music or gentle
frequencies that help the mind settle. Binaural beats, played with
headphones, send different frequencies to each ear and the brain
blends them into a steady, calming rhythm. Try a calm frequency
while you read, and a fresh frequency when you finish, to wash
the day from your mind and greet the next page with new energy.

Remember: a calm mind reads clearly. A fresh mind reads often.
"""


def main():
    doc = fitz.open()
    doc.set_metadata({
        "title": "The Little Reader's Guide",
        "author": "BookSmart Demo",
    })
    # text ko ~ half page chunks me todkar pages banate hain
    paragraphs = [p.strip() for p in TEXT.split("\n\n") if p.strip()]
    chunk = ""
    pages_text = []
    for p in paragraphs:
        if len(chunk) + len(p) > 1200:
            pages_text.append(chunk)
            chunk = p
        else:
            chunk = (chunk + "\n\n" + p).strip()
    if chunk:
        pages_text.append(chunk)

    for i, text in enumerate(pages_text):
        page = doc.new_page(width=595, height=842)  # A4
        page.insert_textbox(
            fitz.Rect(60, 80, 535, 780), text,
            fontsize=13, fontname="helv", lineheight=1.6,
        )

    out = config.BOOKS_DIR / "sample_book.pdf"
    doc.save(out)
    doc.close()
    print(f"✅ Sample book ban gayi: {out}")


if __name__ == "__main__":
    main()
