from __future__ import annotations
import json
from agents.dream_interpret import interpret_dream

def _ok(body, code=200):
    return {"statusCode": code, "headers":{"Content-Type":"application/json"},
            "body": json.dumps(body, ensure_ascii=False)}

def handler(event, _ctx):
    body = event.get("body") or "{}"
    try:
        payload = json.loads(body)
    except Exception:
        payload = {}
    q = payload.get("q") or payload.get("text") or ""
    if not q:
        return _ok({"error":"missing q"}, 400)
    brief = interpret_dream(q)
    return _ok({"brief": brief})
