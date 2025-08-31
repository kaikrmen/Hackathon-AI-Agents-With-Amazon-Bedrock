from __future__ import annotations
import json
from layers.app_common.python.agents.dream_interpret import interpret_dream
from layers.app_common.python.agents.design_generate import generate_assets

def _ok(b, c=200):
    return {"statusCode": c, "headers":{"Content-Type":"application/json"},
            "body": json.dumps(b, ensure_ascii=False)}

def handler(event, _ctx):
    body = event.get("body") or "{}"
    try: payload = json.loads(body)
    except: payload = {}
    q = payload.get("q") or ""
    user_id = payload.get("user_id") or "user_dev_001"

    if not q:
        return _ok({"error":"missing q"}, 400)

    brief = interpret_dream(q)
    out = generate_assets(brief.get("design_prompt", q), brief, user_id=user_id)

    return _ok({"brief": brief, "design": out})
