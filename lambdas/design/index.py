from __future__ import annotations
import json
from agents.design_generate import generate_assets

def handler(event, context):
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else (event.get("body") or {})
    prompt = body.get("design_prompt", "")
    brief = body.get("brief", {})
    user_id = body.get("user_id", "user_unknown")
    result = generate_assets(prompt or "Genera un diseño creativo", brief, user_id)
    return {"statusCode": 200, "body": json.dumps(result)}
