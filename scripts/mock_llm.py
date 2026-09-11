"""
mock_llm.py — a tiny fake LLM server for testing BookSmart WITHOUT a real model.

It mimics llamafile's OpenAI-compatible API on port 8080:
    GET  /v1/models
    POST /v1/chat/completions

It deliberately wraps answers in <think>...</think> blocks, exactly like the
real Qwen3-4B-Thinking model does — so you can verify BookSmart strips them.

Run:
    python scripts/mock_llm.py
Then start BookSmart normally — the sidebar should show "mock-qwen3-4b".
"""
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

PORT = 8080
MODEL_ID = "mock-qwen3-4b"


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path.rstrip("/").endswith("/v1/models"):
            self._send_json({"object": "list", "data": [
                {"id": MODEL_ID, "object": "model", "created": int(time.time()), "owned_by": "mock"}
            ]})
        else:
            self._send_json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path.rstrip("/").endswith("/v1/chat/completions"):
            length = int(self.headers.get("Content-Length", 0))
            try:
                payload = json.loads(self.rfile.read(length) or b"{}")
            except Exception:
                payload = {}
            user_msg = ""
            for m in payload.get("messages", []):
                if m.get("role") == "user":
                    user_msg = m.get("content", "")

            # --- simulate a thinking model: reasoning block first, then the answer ---
            think = (
                "<think>The user is testing BookSmart. I should reason briefly "
                "about the request, then give a clean final answer. This block "
                "imitates Qwen3-4B-Thinking's hidden reasoning.</think>\n\n"
            )
            if "WORD:" in user_msg or "Word:" in user_msg:
                answer = ("MEANING: a sample simple meaning from the mock AI\n"
                          "SYNONYMS: example, sample, demo\n"
                          "IN CONTEXT: here it is used as a test word")
            else:
                answer = ("This is a mock AI answer. Your real Qwen3 model will give "
                          "real answers. If you can read this cleanly WITHOUT any hidden "
                          "reasoning block around it, BookSmart's thinking-model fix "
                          "is working. ✅")
            content = think + answer

            self._send_json({
                "id": "chatcmpl-mock",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": MODEL_ID,
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": "stop",
                }],
                "usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            })
        else:
            self._send_json({"error": "not found"}, 404)

    def log_message(self, fmt, *args):  # quieter console
        pass


if __name__ == "__main__":
    print(f"Mock LLM running on http://127.0.0.1:{PORT}/v1  (model id: {MODEL_ID})")
    print("Press Ctrl+C to stop.")
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
