"""
run.py — BookSmart start karne ka simple tarika.
    python run.py
Phir browser me kholo:  http://localhost:8000
"""
import uvicorn

if __name__ == "__main__":
    print("\n📚 BookSmart starting...  ->  http://localhost:8000\n")
    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=True)
