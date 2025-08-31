from __future__ import annotations
import json
from agents.listing_publish import create_product_and_listing

def handler(event, context):
    body = json.loads(event.get("body", "{}")) if isinstance(event.get("body"), str) else (event.get("body") or {})
    user_id = body.get("user_id", "user_unknown")
    package = body.get("package", {})
    image_key = body.get("image_key", None)
    price_cents = int(body.get("price_cents", 1500))
    result = create_product_and_listing(user_id, package, image_key, price_cents=price_cents)
    return {"statusCode": 200, "body": json.dumps(result)}
