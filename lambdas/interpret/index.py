from __future__ import annotations
import json
from agents.dream_interpret import interpret_dream

def handler(event, context):
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else (event.get("body") or {})
    q = body.get("q", "")
    result = interpret_dream(q) if q else {"error": "missing q"}
    return {"statusCode": 200, "body": json.dumps(result)}
