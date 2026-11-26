"""One bounded HTTP exchange, isolated in a child process."""
import http.client
import json
import sys

from penny.guardian.policy import identity_matches
from . import identity
from .request import MAX_WIRE_BYTES, render_request

MAX_RESPONSE_BYTES = 262144
MODEL = "qwen3:14b"


def exchange(request: object) -> str:
    # Independently check the pin in the child before opening a connection.
    if not identity_matches():
        raise PermissionError("canonical identity mismatch")
    prompt = render_request(request)
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": identity.SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": False, "think": False, "keep_alive": "5m",
        "options": {"num_ctx": 8192, "num_predict": 512},
    }).encode("utf-8")
    # http.client performs no automatic redirects or environment proxy routing.
    conn = http.client.HTTPConnection("127.0.0.1", 11434, timeout=80)
    try:
        conn.request("POST", "/api/chat", body, {"Content-Type": "application/json"})
        response = conn.getresponse()
        if response.status != 200:
            raise ValueError("inference HTTP failure")
        data = response.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES:
            raise ValueError("inference response too large")
        result = json.loads(data)
        if result.get("done") is not True or result.get("done_reason") != "stop":
            raise ValueError("inference did not finish normally")
        message = result["message"]
        if message.get("role") != "assistant" or message.get("tool_calls"):
            raise ValueError("unexpected assistant message")
        text = message.get("content")
        if not isinstance(text, str) or not text.strip() or len(text) > 16000 or "\x00" in text:
            raise ValueError("invalid assistant text")
        return text
    finally:
        conn.close()


def main() -> int:
    try:
        # stdin is populated by the trusted parent; no prompt in argv or logs.
        raw = sys.stdin.buffer.read(MAX_WIRE_BYTES + 1)
        if len(raw) > MAX_WIRE_BYTES:
            raise ValueError("request too large")
        prompt = json.loads(raw)
        print(json.dumps(exchange(prompt), ensure_ascii=True))
        return 0
    except Exception:
        # Never send raw server errors or conversation text to logs.
        print("local inference failed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
