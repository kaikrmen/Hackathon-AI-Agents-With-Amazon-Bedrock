from __future__ import annotations
import json, uuid
from agents.dream_interpret import interpret_dream
from agents.design_generate import generate_assets
from agents.listing_publish import create_product_and_listing
from shared.dynamo import ensure_conversation, put_message
from shared.config import settings

def _ok(b, c=200):
    return {
        "statusCode": c,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(b, ensure_ascii=False),
    }

def handler(event, _ctx):
    body = event.get("body") or "{}"
    try:
        payload = json.loads(body)
    except Exception:
        payload = {}

    q = payload.get("q") or ""
    raw_user_id = payload.get("user_id")
    user_id = raw_user_id or "user_dev_001"
    user_id_defaulted = raw_user_id in (None, "",)

    price_cents = int(payload.get("price_cents") or 1500)

    if not q:
        return _ok({"error": "missing q"}, 400)

    conversation_id = f"conv_{uuid.uuid4().hex[:12]}"
    ensure_conversation(
        conversation_id=conversation_id,
        user_id=user_id,
        model_id=settings.bedrock_text_model_id,
        title=q[:64] + ("…" if len(q) > 64 else ""),
    )
    put_message(conversation_id, role="user", content=q)

    brief = interpret_dream(q)
    put_message(conversation_id, role="assistant",
                content=json.dumps({"brief": brief}, ensure_ascii=False))

    design = generate_assets(brief.get("design_prompt", q), brief, user_id)
    all_keys = []
    for k in ["image_key","pdf_key","docx_key","rtf_key","text_key","video_key","model3d_key"]:
        v = design.get(k)
        if v: all_keys.append(v)
    for v in design.get("media_keys", []):
        if v not in all_keys:
            all_keys.append(v)
    put_message(conversation_id, role="assistant",
                content=json.dumps({"design": design}, ensure_ascii=False),
                media_keys=all_keys or None)

    ids = create_product_and_listing(
        user_id=user_id,
        package=design["package"],
        media_keys=all_keys,
        price_cents=price_cents,
    )
    put_message(conversation_id, role="assistant",
                content=json.dumps({"ids": ids}, ensure_ascii=False))

    resp = {
        "conversation_id": conversation_id,
        "brief": brief,
        "design": design,
        "ids": ids,
        "price_cents": price_cents,
        "currency": "USD",
        "user_id": user_id,
        "user_id_defaulted": user_id_defaulted
    }
    if user_id_defaulted:
        resp["message"] = "user_id not provided; using test user 'user_dev_001'."

    return _ok(resp)
