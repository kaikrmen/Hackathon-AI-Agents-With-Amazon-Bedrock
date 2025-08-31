from __future__ import annotations
import json
from layers.app_common.python.agents.dream_interpret import interpret_dream
from layers.app_common.python.agents.design_generate import generate_assets
from layers.app_common.python.agents.listing_publish import create_product_and_listing

def _ok(b, c=200):
    return {"statusCode": c, "headers": {"Content-Type": "application/json"},
            "body": json.dumps(b, ensure_ascii=False)}

def handler(event, _ctx):
    body = event.get("body") or "{}"
    try:
        payload = json.loads(body)
    except:
        payload = {}

    q = payload.get("q") or ""
    user_id = payload.get("user_id") or "user_dev_001"
    price_cents = payload.get("price_cents") or 1500

    if not q:
        return _ok({"error": "missing q"}, 400)

    brief = interpret_dream(q)

    design = generate_assets(brief.get("design_prompt", q), brief, user_id)

    ids = create_product_and_listing(
        user_id=user_id,
        package=design["package"],
        media_keys=design.get("media_keys", []),
        price_cents=price_cents,
    )

    return _ok({
        "brief": brief,
        "design": design,
        "ids": ids,
        "price_cents": price_cents,
        "currency": "USD"
    })
